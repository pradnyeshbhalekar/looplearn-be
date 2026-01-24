from app.config.db import get_connection,close_connection
from app.services.scraper import scrape_article

def scrape_and_store(source_id:str,url:str):
    result = scrape_article(url)

    status = "failed"
    content_text = None
    title = None

    if result.get("ok"):
        status = "success"
        content_text = result.get("text")
        title = result.get("title")

    else:
        status = result.get('reason','failed')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE sources SET title = COALESCE(%s,title), content_text = %s, scrape_status = %s,
                   scraped_at = NOW() WHERE id = %s;
                   """,(title,content_text,status,source_id))
    conn.commit()
    close_connection(conn)

    return({
        "source_id":source_id,
        "url":url,
        "status":status,
        "title":title
    })