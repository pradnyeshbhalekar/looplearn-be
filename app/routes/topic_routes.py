from flask import Blueprint, jsonify, request
from app.services.pick_topic import pick_topic
from app.config.db import get_connection, close_connection
from app.models.published_articles import get_todays_published_article
from app.utils.auth_decorators import require_auth

topic_bp = Blueprint("topic_bp", __name__)


@topic_bp.route('/today-topic', methods=['GET'])
def today_topic():
    topic = pick_topic()
    if not topic:
        return jsonify({"error": "no topic found"}), 404
    return jsonify(topic)


def check_active_subscription(user_id, domain_names):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT s.id 
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.user_id = %s 
              AND s.status = 'active'
              AND p.domain IN (%s, 'all')
              AND s.ends_at > NOW() 
            LIMIT 1;
        """, (user_id, domain_names))
    
        return cursor.fetchone() is not None
    finally:
        close_connection(conn)



@topic_bp.route('/today-topics', methods=['GET'])
@require_auth
def today_topics_premium(user): 
    domain = request.args.get("domain")
    
    if not domain:
        return jsonify({"error": "Domain query parameter is required"}), 400

    article = get_todays_published_article(domain)
    
    if not article:
        return jsonify({"error": f"No article published today for {domain}"}), 404

    has_access = check_active_subscription(user["user_id"], domain)
    article["is_premium"] = has_access

    if not has_access:
        teaser_text = article["content"][:150].rsplit(' ', 1)[0] 
        article["content"] = f"{teaser_text}...\n\n**[🔒 SUBSCRIBE TO UNLOCK FULL CASE STUDY AND DIAGRAMS]**"
        article["diagram"] = "[PREMIUM DIAGRAM BLURRED]"

    return jsonify(article)