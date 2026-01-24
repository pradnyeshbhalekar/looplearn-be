from flask import Blueprint,jsonify
from app.services.pick_topic import pick_topic
from app.services.fetcher import fetch_candidate_source
from app.config.db import get_connection, close_connection
from app.services.source_service import store_sources_bulk
from app.services.source_scrape_service import scrape_and_store

source_bp = Blueprint("source_bp",__name__)

@source_bp.route('/fetch',methods=['POST'])
def fetch_sources():
    topic = pick_topic()
    if not topic:
        return jsonify({"error":"no topic found"})
    items = fetch_candidate_source(topic["topic_name"],max_results=20)
    stored = store_sources_bulk(items)

    return jsonify({
        "topic":topic,
        "fetched_count":len(items),
        "stored_count":len(stored),
        "stored_sources":stored
    })

@source_bp.route('/scrape_latest',methods=['POST'])
def scrape_latest():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id,url FROM sources ORDER BY fetched_at DESC LIMIT 20;")

    rows = cursor.fetchall()
    close_connection(conn)

    results = []
    for r in rows:
        source_id,url = r
        results.append(scrape_and_store(str(source_id),url))
    
    success = len([x for x in results if x["status"] == "success"])

    return jsonify({
        "attempted":len(results),
        "success":success,
        "results":results
    })