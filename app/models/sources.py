from app.config.db import get_connection,close_connection

def create_sources_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources(
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   url TEXT UNIQUE NOT NULL,
                   domain TEXT,
                   title TEXT,
                   summary TEXT,
                   published_at TIMESTAMP NOT NULL,
                   fetched_at TIMESTAMP NOT NULL DEFAULT NOW()
                   );
""")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_domain ON sources(domain)")

    conn.commit()
    close_connection(conn)

    