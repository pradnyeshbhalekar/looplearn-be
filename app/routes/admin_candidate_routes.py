from flask import Blueprint, jsonify, request
from app.models.article_candidate import list_candidates, get_candidate
from app.services.publish_service import approve_candidate, reject_candidate
# temp
import os

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

admin_candidate_routes = Blueprint(
    "admin_candidates",
    __name__,
)

@admin_candidate_routes.route("/", methods=["GET"])
def pending_candidates():
    rows = list_candidates("pending")
    return jsonify(rows)


@admin_candidate_routes.post("/approve/<candidate_id>")
def approve(candidate_id):
    # admin_user_id = request.headers.get("X-Admin-User")
    admin_user_id = ADMIN_USER_ID
    approve_candidate(candidate_id, admin_user_id)
    return jsonify({"status": "approved"})


@admin_candidate_routes.post("/reject/<candidate_id>")
def reject(candidate_id):
    reason = request.json.get("reason")
    admin_user_id = ADMIN_USER_ID
    reject_candidate(candidate_id, reason,admin_user_id)
    return jsonify({"status": "rejected"})