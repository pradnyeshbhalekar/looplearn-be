from app.config.db import get_connection, close_connection
from app.services.scraper import scrape_article
from app.services.text_cleaner import clean_text


MIN_RAW_LEN = 300
MIN_CLEAN_LEN = 200


def scrape_and_store(source_id: str, url: str):
    result = scrape_article(url)

    status = "failed"
    content_text = None
    title = None

    raw_text = None
    clean_len = 0
    raw_len = 0

    if result.get("ok"):
        raw_text = result.get("text")
        title = result.get("title")

        raw_len = len(raw_text) if raw_text else 0

        if raw_text and raw_len >= MIN_RAW_LEN:
            cleaned = clean_text(raw_text)
            clean_len = len(cleaned) if cleaned else 0

            if cleaned and clean_len >= MIN_CLEAN_LEN:
                content_text = cleaned
                status = "success"
            else:
                status = "failed"
        else:
            status = "failed"
    else:
        status = result.get("reason", "failed")

    # 🔍 DEBUG LOG (keep this until stable)
    print({
        "source_id": source_id,
        "url": url,
        "raw_len": raw_len,
        "clean_len": clean_len,
        "status": status
    })

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sources
        SET title = COALESCE(%s, title),
            content_text = %s,
            scrape_status = %s,
            scraped_at = NOW()
        WHERE id = %s;
    """, (
        title,
        content_text,   # ← overwrite so failures are visible
        status,
        source_id
    ))

    # fetch related topic nodes (optional, but fine)
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
        "url": url,
        "status": status,
        "raw_length": raw_len,
        "clean_length": clean_len,
        "title": title,
        "content_text": content_text,
        "topic_node_ids": topic_node_ids
    }