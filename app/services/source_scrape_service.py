from app.config.db import get_connection, close_connection
from app.services.scraper import scrape_article
from app.services.text_cleaner import clean_text


def scrape_and_store(source_id: str, url: str):
    result = scrape_article(url)

    status = "failed"
    content_text = None
    title = None

    if result.get("ok"):
        raw_text = result.get("text")
        title = result.get("title")

        if raw_text and len(raw_text) > 300:
            content_text = clean_text(raw_text)
            status = "success"
        else:
            status = "failed"
    else:
        status = result.get("reason", "failed")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sources
        SET title = COALESCE(%s, title),
            content_text = COALESCE(%s, content_text),
            scrape_status = %s,
            scraped_at = NOW()
        WHERE id = %s;
    """, (title, content_text, status, source_id))

    cursor.execute("""
        SELECT topic_node_id
        FROM topic_sources
        WHERE source_id = %s;
    """, (source_id,))

    topic_node_ids = [row[0] for row in cursor.fetchall()]

    conn.commit()
    close_connection(conn)

    return {
        "source_id": source_id,
        "topic_node_ids": topic_node_ids,
        "url": url,
        "status": status,
        "title": title
    }