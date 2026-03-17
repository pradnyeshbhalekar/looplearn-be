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
                   scheduled_for DATE NOT NULL,
                   audio_url TEXT,
                   content_json JSONB
                   )
                   """)
    conn.commit()
    close_connection(conn)
    print("published_articles created")
    
def create_article_visibility_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS article_visibility(
        published_article_id UUID PRIMARY KEY REFERENCES published_articles(id) ON DELETE CASCADE,
        audience TEXT NOT NULL CHECK (audience IN ('public','subscriber'))
    );
    """)
    conn.commit()
    close_connection(conn)

def publish_article(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id,publish_date, audio_url=None, content_json=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            INSERT INTO published_articles(
                   candidate_id,
                   topic_node_id,
                   title,
                   slug,
                   article_md,
                   diagram,published_by,scheduled_for,
                   audio_url,
                   content_json
                   ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
                   """,(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id,publish_date, audio_url, content_json))
    article_id = cursor.fetchone()[0]
    conn.commit()
    close_connection(conn)
    set_article_audience(article_id, "public")
    return article_id
def set_article_audience(article_id: str, audience: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO article_visibility (published_article_id, audience)
        VALUES (%s, %s)
        ON CONFLICT (published_article_id)
        DO UPDATE SET audience = EXCLUDED.audience;
    """, (article_id, audience))
    conn.commit()
    close_connection(conn)


def get_published_by_slug(slug):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, article_md, diagram, audio_url, published_at
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
              AND LOWER(domain.name) = LOWER(%s)
              AND (av.audience IS NULL OR av.audience IN ('public','subscriber'))
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
        }
    finally:
        close_connection(conn)

def get_latest_published_article(domain_name: str):
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE LOWER(domain.name) = LOWER(%s)
              AND (av.audience IS NULL OR av.audience IN ('public','subscriber'))
            ORDER BY pa.scheduled_for DESC NULLS LAST, pa.published_at DESC NULLS LAST
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
        }
    finally:
        close_connection(conn)

def get_article_by_slug_with_domain(slug: str):
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name,
                COALESCE(av.audience, 'public') AS audience
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.slug = %s
            LIMIT 1;
        """, (slug,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "slug": row[2],
            "content": row[3],
            "diagram": row[4],
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
            "audience": row[9],
        }
    finally:
        close_connection(conn)
def get_todays_published_article_pref_subscriber(domain_name: str):
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name,
                COALESCE(av.audience, 'public') AS audience
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
              AND LOWER(domain.name) = LOWER(%s)
            ORDER BY 
              CASE 
                WHEN av.audience = 'subscriber' THEN 0
                WHEN av.audience = 'public' THEN 1
                ELSE 2
              END,
              pa.published_at DESC
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
            "audience": row[9],
        }
    finally:
        close_connection(conn)

def get_todays_subscriber_article(domain_name: str):
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name
            FROM published_articles pa
            JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
              AND LOWER(domain.name) = LOWER(%s)
              AND av.audience = 'subscriber'
            ORDER BY pa.published_at DESC NULLS LAST
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
            "audience": "subscriber",
        }
    finally:
        close_connection(conn)

def get_latest_published_article_pref_subscriber(domain_name: str):
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name,
                COALESCE(av.audience, 'public') AS audience
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE LOWER(domain.name) = LOWER(%s)
            ORDER BY 
              CASE 
                WHEN av.audience = 'subscriber' THEN 0
                WHEN av.audience = 'public' THEN 1
                ELSE 2
              END,
              pa.scheduled_for DESC NULLS LAST,
              pa.published_at DESC NULLS LAST
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
            "audience": row[9],
        }
    finally:
        close_connection(conn)
def get_todays_article():
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name,
                COALESCE(av.audience, 'public') AS audience
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
            ORDER BY pa.published_at DESC
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
            "audience": row[9],
        }
    finally:
        close_connection(conn)

def get_todays_published_article_pref_subscriber(domain_name: str):
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
                pa.audio_url,
                pa.published_at,
                topic.name  AS topic_name,
                domain.name AS domain_name,
                COALESCE(av.audience, 'public') AS audience
            FROM published_articles pa
            LEFT JOIN article_visibility av
                ON av.published_article_id = pa.id
            JOIN concept_nodes topic
                ON pa.topic_node_id = topic.id
            JOIN concept_edges ce
                ON ce.to_node_id = topic.id
            JOIN concept_nodes domain
                ON ce.from_node_id = domain.id
               AND domain.node_type = 'domain'
            WHERE pa.scheduled_for::date = CURRENT_DATE
              AND LOWER(domain.name) = LOWER(%s)
            ORDER BY 
              CASE WHEN av.audience = 'subscriber' THEN 1 ELSE 0 END DESC,
              pa.published_at DESC NULLS LAST
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
            "audio_url": row[5],

            "published_at": row[6],
            "topic": row[7],
            "domain": row[8],
            "audience": row[9],
        }
    finally:
        close_connection(conn)

def insert_published_article(title, slug, article_md, diagram, topic_node_id, scheduled_date, audio_url=None):
    """Directly pushes an article to the published table, bypassing the candidate queue."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO published_articles 
            (title, slug, article_md, diagram, audio_url, published_at, scheduled_for, topic_node_id)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
            RETURNING id
        """, (title, slug, article_md, diagram, audio_url, scheduled_date, topic_node_id))
        
        article_id = cursor.fetchone()[0]
        conn.commit()
        set_article_audience(article_id, "public")
        return article_id
    finally:
        close_connection(conn)
