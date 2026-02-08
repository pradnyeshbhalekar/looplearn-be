from flask import Blueprint,jsonify
from app.jobs.pipeline_worker import start_pipeline_job
from app.jobs.job_store import jobs

pipeline_bp = Blueprint("pipeline_bp",__name__)

@pipeline_bp.route("/run",methods = ["POST"])
def run():
    job_id = start_pipeline_job()
    return jsonify({
        "job_id":job_id,
        "status":"started"
    }),202


@pipeline_bp.get('/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error":"Job not found"}),404
    
    return jsonify(job)