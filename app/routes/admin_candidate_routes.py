from flask import Blueprint, jsonify, request
from app.models.article_candidate import list_candidates
from app.services.publish_service import approve_candidate, reject_candidate
from app.utils.auth_decorators import require_admin
from datetime import datetime,timedelta

admin_candidate_routes = Blueprint("admin_candidates", __name__)

@admin_candidate_routes.get("/")
@require_admin
def pending_candidates(user):
    rows = list_candidates("pending")
    return jsonify(rows)

@admin_candidate_routes.get("/queue")
@require_admin
def queued_candidates(user):
    # This returns all approved candidates (queued for future deployment)
    rows = list_candidates("approved")
    return jsonify(rows)


@admin_candidate_routes.post("/approve/<candidate_id>")
@require_admin
def approve(user, candidate_id):
    data = request.get_json(silent=True) or {}

    publish_date_raw = data.get("publish_date")

    if publish_date_raw:
        publish_date = datetime.fromisoformat(
            publish_date_raw.replace("Z", "+00:00")
        )
    else:
        publish_date = datetime.utcnow() + timedelta(days=1)

    approve_candidate(
        candidate_id=candidate_id,
        admin_user_id=user["user_id"],
        publish_date=publish_date
    )

    return {"status": "approved", "publish_date": publish_date.isoformat()}

@admin_candidate_routes.post("/reject/<candidate_id>")
@require_admin
def reject(user, candidate_id):
    reason = request.json.get("reason")
    reject_candidate(candidate_id, reason, user["user_id"])
    return {"status": "rejected"}