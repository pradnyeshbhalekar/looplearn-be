from app.config.db import close_connection, get_connection
import json
from typing import Optional, Any


def create_loop_in_jobs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loop_in_jobs (
            job_id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic TEXT NOT NULL,
            intent TEXT NOT NULL,
            status TEXT NOT NULL,
            result JSONB,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    close_connection(conn)


def create_job(job_id: str, user_id: str, topic: str, intent: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO loop_in_jobs (job_id, user_id, topic, intent, status)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (job_id) DO NOTHING
    """, (job_id, user_id, topic, intent, "pending"))
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
        UPDATE loop_in_jobs
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
        SELECT job_id, user_id, topic, intent, status, result, error, created_at, updated_at
        FROM loop_in_jobs
        WHERE job_id = %s
    """, (job_id,))
    row = cursor.fetchone()
    close_connection(conn)

    if not row:
        return None

    return {
        "job_id": row[0],
        "user_id": row[1],
        "topic": row[2],
        "intent": row[3],
        "status": row[4],
        "result": row[5],
        "error": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }
