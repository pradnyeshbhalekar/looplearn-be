import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return ValueError("DATABASE_URL not found in .env")
    return psycopg2.connect(db_url)


def close_connection(conn):
    if conn:
        conn.close()

        