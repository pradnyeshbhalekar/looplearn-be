from flask import Blueprint, jsonify, request
import uuid
from flask import jsonify
from app.services.pipeline_service import start_premium_pipeline_job, start_all_domains_pipeline_job
from app.services.pipeline_job_service import start_pipeline_job
from app.models.pipeline_jobs import get_job
import os
from app.utils.auth_decorators import require_pipeline_secret

CRON_SECRET = os.getenv("CRON_SECRET")


pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/api/pipeline")

@pipeline_bp.post("/run")
@require_pipeline_secret
def run_pipeline_route():
    job_id = start_pipeline_job()
    return jsonify({
        "job_id": job_id,
        "status": "started"
    }), 202


@pipeline_bp.get("/status/<job_id>")
def get_pipeline_status(job_id):
    try:
        job_uuid = str(uuid.UUID(job_id))  
    except ValueError:
        return jsonify({"error": "Invalid job_id"}), 400

    job = get_job(job_uuid)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)

@pipeline_bp.post("/start-premium")
def trigger_premium():
    data = request.get_json(silent=True) or {}
    domain = (data.get("domain") or "").strip()

    if not domain:
        job_id = start_all_domains_pipeline_job()
        return jsonify({
            "message": "Premium pipeline started for all domains. It will auto-publish for tomorrow.",
            "job_id": job_id
        }), 202
    else:
        job_id = start_premium_pipeline_job(domain)
        return jsonify({
            "message": f"Premium pipeline started for {domain}. It will auto-publish for tomorrow.",
            "job_id": job_id
        }), 202

@pipeline_bp.post("/start-all")
@require_pipeline_secret
def trigger_all_domains():
    job_id = start_all_domains_pipeline_job()
    return jsonify({
        "message": "All-domains pipeline started. A summary report will be emailed to admins.",
        "job_id": job_id
    }), 202
