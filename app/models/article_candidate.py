from app.config.db import get_connection,close_connection

def create_article_candidate():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_candidate(
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            compiled_topic_id UUID NOT NULL
                REFERENCES compiled_topics(id) ON DELETE CASCADE,

            topic_node_id UUID NOT NULL
                REFERENCES concept_nodes(id) ON DELETE CASCADE,

            title TEXT NOT NULL,
            slug TEXT NOT NULL,
            article_md TEXT NOT NULL,
            diagram TEXT,

            status TEXT NOT NULL CHECK (
                status IN ('pending', 'approved', 'rejected')
            ) DEFAULT 'pending',

            scheduled_for DATE,
            rejection_reason TEXT,

            reviewed_by UUID REFERENCES users(id),
            reviewed_at TIMESTAMP,
            audio_url TEXT,

            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    close_connection(conn)

def create_candidate(
        compiled_topic_id,topic_node_id,title,slug,article_md,diagram=None, audio_url=None
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            INSERT INTO article_candidate (
                   compiled_topic_id,
                   topic_node_id,
                   title,
                   slug,
                   article_md,
                   diagram,
                   audio_url
                   )
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id;
                   """,(
                       compiled_topic_id
                       ,topic_node_id
                       ,title
                       ,slug
                       ,article_md
                       ,diagram
                       ,audio_url
                   ))
    
    candidate_id = cursor.fetchone()[0]
    conn.commit()
    close_connection(conn)
    return candidate_id

def get_candidate(candidate_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM article_candidate WHERE id=%s;
""", (candidate_id,))   
    row = cursor.fetchone()
    close_connection(conn)
    return row


def list_candidates(status="pending"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM article_candidate WHERE status=%s ORDER BY created_at DESC;
                   """,(status,))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    result = [dict(zip(columns, row)) for row in rows]

    close_connection(conn)
    return result

def update_candidate_status(
    candidate_id,
    status,
    reason=None,
    reviewed_by=None,
    scheduled_for=None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE article_candidate
        SET status = %s,
            scheduled_for = %s,
            rejection_reason = %s,
            reviewed_by = %s,
            reviewed_at = NOW()
        WHERE id = %s;
    """, (
        status,
        scheduled_for,
        reason,
        reviewed_by,
        candidate_id
    ))

    conn.commit()
    close_connection(conn)