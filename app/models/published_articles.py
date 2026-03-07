from app.config.db import close_connection,get_connection

def create_published_article():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS published_articles(
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   candidate_id UUID
                        REFERENCES article_candidate(id),
                   topic_node_id UUID NOT NULL
                        REFERENCES concept_nodes(id),
                   title TEXT NOT NULL,
                   slug TEXT NOT NULL,
                   article_md TEXT NOT NULL,
                   diagram TEXT,
                   published_at TIMESTAMP DEFAULT NOW(),
                   published_by UUID,
                   scheduled_for DATE NOT NULL
                   )
                   """)
    conn.commit()
    close_connection(conn)
    print("published_articles created")

def publish_article(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id,publish_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
          INSERT INTO published_articles(
                   candidate_id,
                   topic_node_id,
                   title,
                   slug,
                   article_md,
                   diagram,published_by,scheduled_for
                   ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
                   """,(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id,publish_date))
    article_id = cursor.fetchone()[0]
    conn.commit()
    close_connection(conn)
    return article_id


def get_published_by_slug(slug):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, article_md, diagram, published_at
        FROM published_articles
        WHERE slug = %s
        LIMIT 1
    """, (slug,))

    article = cursor.fetchone()
    close_connection(conn)
    return article

def get_published_by_id(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
          SELECT * FROM published_articles WHERE id=%s
     """,(id,))
    row = cursor.fetchone()
    close_connection(conn)
    return row

def get_todays_published_article(domain_name: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pa.id,
                pa.title,
                pa.slug,
                pa.article_md,
                pa.diagram,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name
            FROM published_articles pa
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
              AND LOWER(domain.name) = LOWER(%s)
            ORDER BY pa.published_at DESC
            LIMIT 1;
        """, (domain_name,))

        row = cursor.fetchone()
        
        if not row:
            return None

        return {
            "id": row[0],
            "title": row[1],
            "slug": row[2],
            "content": row[3],
            "diagram": row[4],
            "published_at": row[5],
            "topic": row[6],
            "domain": row[7],
        }
    finally:
        close_connection(conn)


def get_todays_free_article():
    """Returns today's article from any random domain (for free users)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pa.id,
                pa.title,
                pa.slug,
                pa.article_md,
                pa.diagram,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name
            FROM published_articles pa
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
            ORDER BY RANDOM()
            LIMIT 1;
        """)

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "title": row[1],
            "slug": row[2],
            "content": row[3],
            "diagram": row[4],
            "published_at": row[5],
            "topic": row[6],
            "domain": row[7],
        }
    finally:
        close_connection(conn)


def insert_published_article(title, slug, article_md, diagram, topic_node_id, scheduled_date):
    """Directly pushes an article to the published table, bypassing the candidate queue."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO published_articles 
            (title, slug, article_md, diagram, published_at, scheduled_for, topic_node_id)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s)
            RETURNING id
        """, (title, slug, article_md, diagram, scheduled_date, topic_node_id))
        
        article_id = cursor.fetchone()[0]
        conn.commit()
        return article_id
    finally:
        close_connection(conn)