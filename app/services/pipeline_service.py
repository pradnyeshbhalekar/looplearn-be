from app.services.pick_topic import pick_topic
from app.services.fetcher import fetch_candidate_source
from app.services.source_service import store_sources_bulk
from app.config.db import get_connection,close_connection
from app.services.source_scrape_service import scrape_and_store
from app.services.topic_compiler import compile_topic
from app.services.compiled_topic_service import save_compiled_topic
from app.services.child_topic_service import add_child_topics

def run_pipeline():
    topic = pick_topic()
    if not topic:
        raise RuntimeError("No topic could be picked")

    topic_id = topic["topic_node_id"]
    topic_name = topic["topic_name"]

    fetched_sources = fetch_candidate_source(topic_name)
    store_sources_bulk(fetched_sources)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url
        FROM sources
        WHERE scrape_status = 'pending'
        LIMIT 10;
    """)
    rows = cursor.fetchall()
    close_connection(conn)

    if not rows:
        return {
            "topic": topic_id,
            "source_fetched": len(fetched_sources),
            "source_scraped": 0,
            "child_topic_added": 0
        }

    scraped_result = []
    for row in rows:
        if len(row) < 2:
            raise ValueError(f"Expected at least 2 columns in sources query result, got {len(row)}: {row}")
        source_id, url = row[0], row[1]
        scraped_result.append(scrape_and_store(source_id, url))

    concepts = [topic_name]  

    compiled = compile_topic(topic_name, concepts)

    save_compiled_topic(topic_id, compiled)

    child_topics = compiled.get("child_topics", [])
    child_inserted = add_child_topics(topic_id, child_topics)

    return {
        "topic_id": topic_id,
        "result": compiled,
        "topic_name":topic_name,
        "source_fetched": len(fetched_sources),
        "source_scraped": len(scraped_result),
        "child_topic_added": child_inserted
    }

