from flask import Blueprint, jsonify
from app.services.pipeline_job_service import start_pipeline_job
from app.models.pipeline_jobs import get_job

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/api/pipeline")

@pipeline_bp.post("/run")
def run_pipeline_route():
    job_id = start_pipeline_job()
    return jsonify({
        "job_id": job_id,
        "status": "started"
    }), 202


import uuid
from flask import jsonify

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