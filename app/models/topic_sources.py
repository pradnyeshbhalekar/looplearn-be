from app.config.db import close_connection, get_connection

def create_topic_sources_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_sources (
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   topic_node_id UUID NOT NULL REFERENCES concept_nodes(id) ON DELETE CASCADE,
                   source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                   created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                   UNIQUE(topic_node_id,source_id));
                   """)
    
    cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_topic_sources_topic
        ON topic_sources(topic_node_id);
            """)
    
    conn.commit()
    close_connection(conn)

    print("topic sources table created")