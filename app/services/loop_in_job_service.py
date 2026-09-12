import uuid
import threading
from app.models.loop_in_jobs import create_job, update_job
from app.services.loop_in_service import run_loop_in


def start_loop_in_job(user_id: str, topic: str, intent: str) -> str:
    job_id = str(uuid.uuid4())
    create_job(job_id, user_id, topic, intent)

    t = threading.Thread(
        target=_run_loop_in_job,
        args=(job_id, topic, intent),
        daemon=True
    )
    t.start()

    return job_id


def _run_loop_in_job(job_id: str, topic: str, intent: str):
    update_job(job_id, "running")

    try:
        result = run_loop_in(topic, intent, audio_slug=job_id)
        update_job(job_id, "completed", result=result)
    except Exception as e:
        print(f"❌ Loop in job {job_id} failed: {e}")
        update_job(job_id, "failed", error=str(e))
