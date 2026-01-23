from urllib.parse import urlparse
from app.config.db import get_connection, close_connection


def store_sources_bulk(items):
    conn = get_connection()
    cursor = conn.cursor()

    stored = []

    for item in items:
        url = item["url"]
        title = item.get("title")
        summary = item.get("summary")
        domain = urlparse(url).netloc

        cursor.execute("""
            INSERT INTO sources (url, domain, title, summary,published_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (url) DO NOTHING
            RETURNING id, url;
        """, (url, domain, title, summary))

        row = cursor.fetchone()  

        if row:
            stored.append({"source_id": str(row[0]), "url": row[1]})
        else:
            stored.append({"source_id": None, "url": url})

    conn.commit()
    close_connection(conn)

    return stored