from app.config.db import get_connection, close_connection

ANTI_REPEAT_DAYS = 30
MAX_TRIES = 10


def pick_topic():
    conn = get_connection()
    cursor = conn.cursor()

    picked_id = None
    picked_name = None

    for _ in range(MAX_TRIES):

        # 1) pick random domain
        cursor.execute("""
            SELECT id, name
            FROM concept_nodes
            WHERE node_type = 'domain'
            ORDER BY RANDOM()
            LIMIT 1;
        """)
        domain = cursor.fetchone()

        if not domain:
            close_connection(conn)
            return None

        domain_id, domain_name = domain

        # 2) pick a connected concept (if exists) that is not already published
        cursor.execute("""
            SELECT cn.id, cn.name
            FROM concept_edges ce
            JOIN concept_nodes cn ON cn.id = ce.to_node_id
            WHERE ce.from_node_id = %s
              AND cn.id NOT IN (
                  SELECT topic_node_id 
                  FROM published_articles 
                  WHERE topic_node_id IS NOT NULL
              )
            ORDER BY (RANDOM() * ce.strength) DESC
            LIMIT 1;
        """, (domain_id,))
        candidate = cursor.fetchone()

        # if no edges yet, fallback to domain itself
        picked_id, picked_name = candidate if candidate else (domain_id, domain_name)

        # 3) anti-repeat check (last 30 days)
        cursor.execute(f"""
            SELECT 1
            FROM topic_history
            WHERE topic_node_id = %s
              AND used_at >= NOW() - INTERVAL '{ANTI_REPEAT_DAYS} days'
            LIMIT 1;
        """, (picked_id,))
        repeated = cursor.fetchone()

        # 3B) check if already officially published
        cursor.execute("""
            SELECT 1 
            FROM published_articles 
            WHERE topic_node_id = %s
            LIMIT 1;
        """, (picked_id,))
        published = cursor.fetchone()

        # ✅ if not repeated or published, accept topic
        if not repeated and not published:
            break

    # 4) save usage (history + last_used_at)
    cursor.execute("""
        UPDATE concept_nodes
        SET last_used_at = NOW()
        WHERE id = %s;
    """, (picked_id,))

    cursor.execute("""
        INSERT INTO topic_history (topic_node_id)
        VALUES (%s);
    """, (picked_id,))

    conn.commit()
    close_connection(conn)

    return {"topic_node_id": str(picked_id), "topic_name": picked_name, "domain": domain_name}


from app.config.db import get_connection, close_connection

def pick_topic_domain(domain_name=None):
    """
    Finds an unwritten topic. 
    If a domain_name is provided, it filters by that domain.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        if domain_name:
            print(f"🔍 Searching for a topic in domain: {domain_name}")
            
            # First attempt: Try to find a topic EXACTLY in this domain
            cursor.execute("""
                SELECT t.id, t.name, d.name
                FROM concept_nodes t
                INNER JOIN concept_edges e ON t.id = e.to_node_id
                INNER JOIN concept_nodes d ON e.from_node_id = d.id
                WHERE LOWER(d.name) = LOWER(%s) 
                  AND d.node_type = 'domain' 
                  AND t.node_type = 'concept'
                  AND t.id NOT IN (
                      SELECT topic_node_id 
                      FROM published_articles 
                      WHERE topic_node_id IS NOT NULL
                  )
                ORDER BY RANDOM()
                LIMIT 1;
            """, (domain_name,))
            row = cursor.fetchone()
            
            # Second attempt: If the specific domain is exhausted, fallback to ANY unused concept globally
            if not row:
                print(f"⚠️ Domain '{domain_name}' exhausted. Falling back to any available topic...")
                cursor.execute("""
                    SELECT t.id, t.name, d.name
                    FROM concept_nodes t
                    LEFT JOIN concept_edges e ON t.id = e.to_node_id
                    LEFT JOIN concept_nodes d ON e.from_node_id = d.id AND d.node_type = 'domain'
                    WHERE t.node_type = 'concept'
                      AND t.id NOT IN (
                          SELECT topic_node_id 
                          FROM published_articles 
                          WHERE topic_node_id IS NOT NULL
                      )
                    ORDER BY RANDOM()
                    LIMIT 1;
                """)
                row = cursor.fetchone()
                
        else:
            # Query randomly and also fetch its linked domain
            cursor.execute("""
                SELECT t.id, t.name, d.name
                FROM concept_nodes t
                LEFT JOIN concept_edges e ON t.id = e.to_node_id
                LEFT JOIN concept_nodes d ON e.from_node_id = d.id AND d.node_type = 'domain'
                WHERE t.node_type = 'concept'
                  AND t.id NOT IN (
                      SELECT topic_node_id 
                      FROM published_articles 
                      WHERE topic_node_id IS NOT NULL
                  )
                ORDER BY RANDOM()
                LIMIT 1;
            """)
            row = cursor.fetchone()
        
        if row:
            print(f"✅ Found topic: {row[1]} (ID: {row[0]})")
            actual_domain = domain_name if domain_name else (row[2] if len(row) > 2 else "System Design")
            return {
                "topic_node_id": row[0], 
                "topic_name": row[1],
                "domain": actual_domain
            }
        
        print(f"❌ No unused topics found for domain: {domain_name}")
        return None
        
    except Exception as e:
        print(f"⚠️ Database error in pick_topic: {e}")
        return None
    finally:
        close_connection(conn)
