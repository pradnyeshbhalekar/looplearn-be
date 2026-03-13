from app.config.db import get_connection, close_connection

DOMAINS = [
    "Databases",
    "Cybersecurity",
    "System Design",
    "Operating Systems",
    "Backend Engineering",
    "APIs",
    "Distributed Systems",
    "Frontend Engineering",
    "Cloud Computing",
]


def create_graph_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Enable UUID generator
    cursor.execute("""CREATE EXTENSION IF NOT EXISTS "pgcrypto";""")

    # Nodes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_nodes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT UNIQUE NOT NULL,
            node_type TEXT NOT NULL CHECK (node_type IN ('domain', 'concept', 'feature')),
            last_used_at TIMESTAMP NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)

    # Edges table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_edges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            from_node_id UUID NOT NULL REFERENCES concept_nodes(id) ON DELETE CASCADE,
            to_node_id UUID NOT NULL REFERENCES concept_nodes(id) ON DELETE CASCADE,
            strength REAL NOT NULL DEFAULT 1.0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(from_node_id, to_node_id)
        );
    """)

    # Indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_concept_nodes_type
        ON concept_nodes(node_type);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_edges_from
        ON concept_edges(from_node_id);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_edges_to
        ON concept_edges(to_node_id);
    """)

    conn.commit()
    close_connection(conn)
    print(" Graph tables created (concept_nodes, concept_edges)")


def seed_domains():
    conn = get_connection()
    cursor = conn.cursor()

    for d in DOMAINS:
        # Standardize matching insert_node logic
        raw_name = d.strip()
        if raw_name.upper() == 'APIS':
            processed_name = 'APIs'
        else:
            processed_name = raw_name.title()
        
        cursor.execute("""
            INSERT INTO concept_nodes (name, node_type)
            VALUES (%s, 'domain')
            ON CONFLICT (name) 
            DO UPDATE SET node_type = 'domain'
            RETURNING id;
        """, (processed_name,))

    conn.commit()
    close_connection(conn)
    print(" Domains seeded")


def get_all_domain_names():
    """Returns a list of all domain names from concept_nodes."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM concept_nodes
            WHERE node_type = 'domain'
            ORDER BY name;
        """)
        rows = cursor.fetchall()
        return [r[0] for r in rows]
    finally:
        close_connection(conn)


def insert_node(name, node_type):
    conn = get_connection()
    cursor = conn.cursor()

    # Standardize domain names to prevent case duplicates
    processed_name = name.strip()
    if node_type == 'domain':
        if processed_name.upper() == 'APIS':
            processed_name = 'APIs'
        else:
            processed_name = processed_name.title()

    cursor.execute("""
        INSERT INTO concept_nodes (name, node_type)
        VALUES (%s, %s)
        ON CONFLICT (name)
        DO UPDATE SET 
            node_type = CASE 
                WHEN concept_nodes.node_type = 'domain' AND EXCLUDED.node_type = 'concept' THEN 'domain'
                ELSE EXCLUDED.node_type 
            END
        RETURNING id, name, node_type;
    """, (processed_name, node_type))

    node = cursor.fetchone()

    conn.commit()
    close_connection(conn)

    return node


def get_all_nodes():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, node_type
        FROM concept_nodes
        ORDER BY created_at DESC;
    """)

    rows = cursor.fetchall()
    close_connection(conn)
    return rows


def insert_or_increment_edge(from_node_id, to_node_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO concept_edges (from_node_id, to_node_id, strength)
        VALUES (%s, %s, 1.0)
        ON CONFLICT (from_node_id, to_node_id)
        DO UPDATE SET strength = concept_edges.strength + 1.0
        RETURNING id, from_node_id, to_node_id, strength;
    """, (from_node_id, to_node_id))

    edge = cursor.fetchone()

    conn.commit()
    close_connection(conn)

    return edge
