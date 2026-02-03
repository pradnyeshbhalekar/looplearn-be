from app.config.db import get_connection,close_connection

def create_compiled_topics_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS compiled_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_node_id UUID NOT NULL REFERENCES concept_nodes(id) ON DELETE CASCADE,

    theory JSONB NOT NULL,
    topic_schema JSONB NOT NULL,
    case_study JSONB NOT NULL,
    mermaid JSONB NOT NULL,
    interview_notes JSONB NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (topic_node_id)
);
                   """)
    
    conn.commit()
    close_connection(conn)
    print("compiled_topics table created")