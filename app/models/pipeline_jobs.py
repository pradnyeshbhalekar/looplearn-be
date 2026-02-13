from app.config.db import close_connection, get_connection
import json
from typing import Optional, Any

def create_pipeline_jobs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            job_id UUID PRIMARY KEY,
            status TEXT NOT NULL,
            result JSONB,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    close_connection(conn)


def create_job(job_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pipeline_jobs (job_id, status)
        VALUES (%s, %s)
        ON CONFLICT (job_id) DO NOTHING
    """, (job_id, "pending"))
    conn.commit()
    close_connection(conn)


def update_job(
    job_id: str,
    status: str,
    result: Optional[Any] = None,
    error: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pipeline_jobs
        SET status = %s,
            result = %s,
            error = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE job_id = %s
    """, (
        status,
        json.dumps(result) if result is not None else None,
        error,
        job_id
    ))
    conn.commit()
    close_connection(conn)


def get_job(job_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, status, result, error, created_at, updated_at
        FROM pipeline_jobs
        WHERE job_id = %s
    """, (job_id,))
    row = cursor.fetchone()
    close_connection(conn)

    if not row:
        return None

    return {
        "job_id": row[0],
        "status": row[1],
        "result": row[2],
        "error": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }