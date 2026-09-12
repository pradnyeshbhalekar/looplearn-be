from flask import Blueprint, jsonify, request
import uuid
from app.services.loop_in_job_service import start_loop_in_job
from app.models.loop_in_jobs import get_job
from app.utils.auth_middleware import require_auth
from app.services.gap_analyzer import MAX_TOPIC_LENGTH, MAX_INTENT_LENGTH

loop_in_bp = Blueprint("loop_in", __name__, url_prefix="/api/loop-in")


@loop_in_bp.post("/run")
@require_auth
def run_loop_in_route(user):
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    intent = (data.get("intent") or "").strip()

    if not topic:
        return jsonify({"error": "topic is required"}), 400
    if not intent:
        return jsonify({"error": "intent is required"}), 400
    if len(topic) > MAX_TOPIC_LENGTH:
        return jsonify({"error": f"topic must be {MAX_TOPIC_LENGTH} characters or fewer"}), 400
    if len(intent) > MAX_INTENT_LENGTH:
        return jsonify({"error": f"intent must be {MAX_INTENT_LENGTH} characters or fewer"}), 400

    job_id = start_loop_in_job(user["user_id"], topic, intent)
    return jsonify({
        "job_id": job_id,
        "status": "started"
    }), 202


@loop_in_bp.get("/status/<job_id>")
@require_auth
def get_loop_in_status(user, job_id):
    try:
        job_uuid = str(uuid.UUID(job_id))
    except ValueError:
        return jsonify({"error": "Invalid job_id"}), 400

    job = get_job(job_uuid)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Ownership check — this is the gap flagged against pipeline_jobs (no
    # user_id at all): here every job has an owner, and only that owner
    # (or an admin) can read it back.
    if str(job["user_id"]) != str(user["user_id"]) and user.get("role") != "admin":
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)
