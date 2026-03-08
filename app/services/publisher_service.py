from app.config.db import close_connection,get_connection
from datetime import datetime
from app.models.published_articles import set_article_audience

def publish_approved_article():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT 
                ac.id, 
                ac.topic_node_id,
                ac.title,
                ac.slug, 
                ac.article_md,
                ac.diagram,
                ac.reviewed_by,
                ac.scheduled_for
                    FROM article_candidate ac
                    LEFT JOIN published_articles pa
            ON pa.candidate_id = ac.id
                   WHERE 
                   ac.status='approved' AND
                   ac.scheduled_for <=NOW()
                   AND pa.id is NULL
                   """)
    
    rows = cursor.fetchall()
    published_ids=[]


    for row in rows:
        (
            candidate_id,
            topic_node_id,
            title,
            slug,
            article_md,
            diagram,
            admin_user_id,
            publish_date,
        ) = row

        cursor.execute("""
                INSERT INTO published_articles (
                       candidate_id,
                       topic_node_id,
                       title,
                       slug,
                       article_md,
                       diagram,
                       published_by,
                       published_at,
                       scheduled_for
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,(candidate_id,topic_node_id,title,slug,article_md,diagram,admin_user_id,datetime.utcnow(),publish_date))
        article_id = cursor.fetchone()[0]
        set_article_audience(article_id, "public")
        
        published_ids.append(candidate_id)
        conn.commit()

    close_connection(conn)

    return published_ids
