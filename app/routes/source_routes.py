from flask import Blueprint,jsonify
from app.services.pick_topic import pick_topic
from app.services.fetcher import fetch_candidate_source
from app.services.source_service import store_sources_bulk

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