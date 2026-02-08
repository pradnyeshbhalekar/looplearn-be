from app.config.db import close_connection,get_connection

def create_daily_post_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            CREATE EXTENSION IF NOT EXISTS "pgcrypto";

            CREATE TABLE IF NOT EXISTS daily_posts(
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   post_date DATE UNIQUE NOT NULL,
                   topic_node_id UUID NOT NULL REFERENCES concept_nodes(id),
                   title TEXT NOT NULL,
                   slug TEXT UNIQUE NOT NULL,
                   article_md TEXT NOT NULL,
                   diagram TEXT NOT NULL,
                   created_at TIMESTAMP NOT NULL DEFAULT NOW()
                   );
                   """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_posts_date ON daily_posts(post_date);")
    conn.commit()
    close_connection(conn)
    print("daily_posts table created")


def create_daily_post_sources_table():
    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute("""CREATE EXTENSION IF NOT EXISTS "pgcrypto";""")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_post_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            daily_post_id UUID NOT NULL REFERENCES daily_posts(id) ON DELETE CASCADE,
            source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            rank_score REAL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(daily_post_id, source_id)
        );
    """)

    conn.commit()
    close_connection(conn)

    print("daily_post_sources table created")

