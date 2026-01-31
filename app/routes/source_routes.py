from flask import Blueprint,jsonify
from app.services.pick_topic import pick_topic
from app.services.fetcher import fetch_candidate_source
from app.config.db import get_connection, close_connection
from app.services.source_service import store_sources_bulk
from app.services.source_scrape_service import scrape_and_store
from app.services.topic_source_service import link_sources_to_topic
from app.services.topic_source_service import get_best_topic_sources
from app.services.text_structurer import split_into_sections



source_bp = Blueprint("source_bp",__name__)

@source_bp.route('/fetch',methods=['POST'])
def fetch_sources():
    topic = pick_topic()
    if not topic:
        return jsonify({"error":"no topic found"})
    items = fetch_candidate_source(topic["topic_name"],max_results=20)
    stored = store_sources_bulk(items)
    
    linked_count = link_sources_to_topic(topic["topic_node_id"],stored)

    return jsonify({
        "topic":topic,
        "fetched_count":len(items),
        "stored_count":len(stored),
        "linked_count":linked_count,
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


@source_bp.route("/topic/<topic_node_id>", methods=["GET"])
def get_sources_for_topic(topic_node_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.url, s.scrape_status, LENGTH(s.content_text) AS content_len
        FROM topic_sources ts
        JOIN sources s ON s.id = ts.source_id
        WHERE ts.topic_node_id = %s
        ORDER BY ts.created_at DESC;
    """, (topic_node_id,))

    rows = cursor.fetchall()
    close_connection(conn)

    return jsonify([
        {
            "source_id": str(r[0]),
            "url": r[1],
            "scrape_status": r[2],
            "content_len": r[3]
        }
        for r in rows
    ])


@source_bp.route("/topic/<topic_node_id>/scrape", methods=["POST"])
def scrape_sources_for_topic(topic_node_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.url
        FROM topic_sources ts
        JOIN sources s ON s.id = ts.source_id
        WHERE ts.topic_node_id = %s
          AND (s.scrape_status = 'pending' OR s.scrape_status IS NULL)
        ORDER BY ts.created_at DESC
        LIMIT 20;
    """, (topic_node_id,))

    rows = cursor.fetchall()
    close_connection(conn)

    results = []
    for source_id, url in rows:
        results.append(scrape_and_store(str(source_id), url))

    success = len([x for x in results if x["status"] == "success"])

    return jsonify({
        "topic_node_id": topic_node_id,
        "attempted": len(results),
        "success": success,
        "results": results
    })

@source_bp.route("/topic/<topic_node_id>/best", methods=["GET"])
def get_best_sources_for_topic(topic_node_id):
    best = get_best_topic_sources(topic_node_id, limit=5)

    return jsonify({
        "topic_node_id": topic_node_id,
        "count": len(best),
        "best_sources": best
    })


@source_bp.route('/topic/<topic_node_id>/preview',methods=['GET'])
def preview_topic_source(topic_node_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT s.url, LENGTH(s.content_text), SUBSTRING(s.content_text, 1, 500)
        FROM topic_sources ts
        JOIN sources s ON s.id = ts.source_id
        WHERE ts.topic_node_id = %s
          AND s.scrape_status = 'success'
        ORDER BY LENGTH(s.content_text) DESC
        LIMIT 3;
    """, (topic_node_id,))

    rows = cursor.fetchall()
    close_connection(conn)

    return jsonify([
        {
        "url":r[0],
        "content_len":r[1],
        "preview":r[2]
        }
        for r in rows
    ])


@source_bp.route("/topic/<topic_node_id>/sections", methods=["GET"])
def preview_structured_sections(topic_node_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.url, s.content_text
        FROM topic_sources ts
        JOIN sources s ON s.id = ts.source_id
        WHERE ts.topic_node_id = %s
          AND s.scrape_status = 'success'
        ORDER BY LENGTH(s.content_text) DESC
        LIMIT 1;
    """, (topic_node_id,))

    row = cursor.fetchone()
    close_connection(conn)

    if not row:
        return jsonify({"error": "No source found"}), 404

    url, content_text = row
    sections = split_into_sections(content_text)

    return jsonify({
        "url": url,
        "section_count": len(sections),
        "sections": [
            {
                "heading": s["heading"],
                "preview": s["content"][:300]
            }
            for s in sections
        ]
    })