import threading
import uuid
from app.jobs.job_store import jobs,JobStatus
from app.services.pipeline_service import run_pipeline
from app.services.email_service import send_admin_notification
from app.utils.email_utils import get_admin_emails

def start_pipeline_job():
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "result":None,
        "error":None
    }

    t = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id,),   # ← THIS COMMA MATTERS
        daemon=True
    )
    t.daemon = True
    t.start()

    return job_id

def _run_pipeline_job(job_id: str):
    jobs[job_id]['status'] = JobStatus.RUNNING

    try:
        result = run_pipeline()

        jobs[job_id]['status'] = JobStatus.COMPLETED
        jobs[job_id]['result'] = result

        topics = result.get("topics", [])

        if topics:
            emails = get_admin_emails()
            send_admin_notification(emails, topics)

    except Exception as e:
        jobs[job_id]['status'] = JobStatus.FAILED
        jobs[job_id]['error'] = str(e)