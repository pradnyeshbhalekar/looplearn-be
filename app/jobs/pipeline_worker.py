import threading
import uuid
from app.jobs.job_store import jobs,JobStatus
from app.services.pipeline_service import run_pipeline

def start_pipeline_job():
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "result":None,
        "error":None
    }

    t = threading.Thread(target=_run,args=(job_id))
    t.daemon = True
    t.start()

    return job_id




def _run(job_id:str):
    jobs[job_id]['status'] = JobStatus.RUNNING
    try:
        result = run_pipeline()
        jobs[job_id]['status'] = JobStatus.COMPLETED
        jobs[job_id]['result'] = result
    except Exception as e:
        jobs[job_id]['status'] = JobStatus.FAILED
        jobs[job_id]['error'] = str(e)