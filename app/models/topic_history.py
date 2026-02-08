from app.config.db import close_connection, get_connection

def create_topic_history_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""CREATE EXTENSION IF NOT EXISTS "pgcrypto";""")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_history(
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            topic_node_id UUID NOT NULL REFERENCES concept_nodes(id) ON DELETE CASCADE,
            used_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_topic_history_node_time
        ON topic_history(topic_node_id, used_at DESC);
    """)

    conn.commit()
    close_connection(conn)
    print("✅ topic_history table created") 