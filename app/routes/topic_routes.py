from flask import Blueprint,jsonify
from app.services.pick_topic import pick_topic

topic_bp = Blueprint("topic_bp",__name__)

@topic_bp.route('/today-topic',methods=['GET'])
def today_topic():
    topic = pick_topic()
    if not topic:
        return jsonify({"error":"no topic found"}),404
    return jsonify(topic)


