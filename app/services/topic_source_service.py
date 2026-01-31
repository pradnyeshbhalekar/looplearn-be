from app.config.db import get_connection,close_connection

def link_sources_to_topic(topic_node_id:str,stored_sources:list):
    conn = get_connection()
    cursor = conn.cursor()

    linked = 0

    for s in stored_sources:
        source_id = s.get("source_id")
        if not source_id:
            continue

        cursor.execute("""
                       INSERT INTO topic_sources(topic_node_id, source_id)
                       VALUES (%s,%s)
                       ON CONFLICT (topic_node_id,source_id) DO NOTHING;
                       """,(topic_node_id,source_id))
        linked += 1

    conn.commit()
    close_connection(conn)
    
    return linked


def get_best_topic_sources(topic_node_id: str, limit: int = 5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.url, LENGTH(s.content_text) AS content_len
        FROM topic_sources ts
        JOIN sources s ON s.id = ts.source_id
        WHERE ts.topic_node_id = %s
          AND s.scrape_status = 'success'
          AND s.content_text IS NOT NULL
        ORDER BY LENGTH(s.content_text) DESC
        LIMIT %s;
    """, (topic_node_id, limit))

    rows = cursor.fetchall()
    close_connection(conn)

    return [
        {
            "source_id": str(r[0]),
            "url": r[1],
            "content_len": r[2]
        }
        for r in rows
    ]