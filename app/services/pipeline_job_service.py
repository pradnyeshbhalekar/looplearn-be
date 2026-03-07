import uuid
import threading
from app.models.pipeline_jobs import (
    create_job,
    update_job
)
from app.services.pipeline_service import run_pipeline
from app.services.email_service import send_admin_notification
from app.utils.email_utils import get_admin_emails

def start_pipeline_job():
    job_id = str(uuid.uuid4())
    create_job(job_id)

    t = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id,), 
        daemon=True
    )
    t.start()

    return job_id


def _run_pipeline_job(job_id: str):
    update_job(job_id, "running")

    try:
        result = run_pipeline()
        update_job(job_id, "completed", result=result)

        topic_name = result.get("topic_name")
        if topic_name:
            try:
                emails = get_admin_emails()
                if emails:
                    send_admin_notification(emails, topic_name)
            except Exception as mail_err:
                print(f"⚠️ Email notification failed: {mail_err}")
    except Exception as e:
        update_job(job_id, "failed", error=str(e))
