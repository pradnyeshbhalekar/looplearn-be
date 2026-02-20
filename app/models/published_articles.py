from app.config.db import close_connection,get_connection

def create_published_article():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS published_articles(
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   candidate_id UUID NOT NULL
                        REFERENCES article_candidate(id),
                   topic_node_id UUID NOT NULL
                        REFERENCES concept_nodes(id),
                   title TEXT NOT NULL,
                   slug TEXT NOT NULL,
                   article_md TEXT NOT NULL,
                   diagram TEXT NOT NULL,
                   published_at TIMESTAMP DEFAULT NOW(),
                   published_by UUID
                   )
                   """)
    conn.commit()
    close_connection(conn)
    print("published_articles created")

def publish_article(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
          INSERT INTO published_articles(
                   candidate_id,
                   topic_node_id,
                   title,
                   slug,
                   article_md,
                   diagram,published_by
                   ) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id;
                   """,(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id))
    article_id = cursor.fetchone()[0]
    conn.commit()
    close_connection(conn)
    return article_id

def get_published_by_slug(slug):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
          SELECT * FROM published_articles WHERE slug =%s
                   """,(slug,))    
    row = cursor.fetchone()
    close_connection(conn)
    return row


def get_published_by_id(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
          SELECT * FROM published_articles WHERE id=%s
     """,(id,))
    row = cursor.fetchone()
    close_connection(conn)
    return row