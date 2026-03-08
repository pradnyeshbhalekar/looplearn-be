import os
import psycopg2
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from psycopg2 import OperationalError
import urllib.parse

load_dotenv()

def _with_sslmode(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if "sslmode" not in q:
        q["sslmode"] = ["require"]
    query = urllib.parse.urlencode({k: v[0] for k, v in q.items()})
    return urllib.parse.urlunparse(parsed._replace(query=query))

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True, retry=retry_if_exception_type(OperationalError))
def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in .env")
    db_url = _with_sslmode(db_url)
    return psycopg2.connect(
        db_url,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )


def close_connection(conn):
    if conn:
        conn.close()

        
