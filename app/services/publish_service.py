from app.models.published_articles import publish_article
from app.models.article_candidate import update_candidate_status
from app.config.db import get_connection, close_connection
from datetime import datetime, timedelta



def approve_candidate(candidate_id, admin_user_id, publish_date=None):
    if not publish_date:
        publish_date = datetime.utcnow() + timedelta(days=1)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT topic_node_id, title, slug, article_md, diagram, audio_url
        FROM article_candidate
        WHERE id = %s AND status = 'pending';
    """, (candidate_id,))

    row = cursor.fetchone()
    if not row:
        close_connection(conn)
        raise ValueError("Invalid candidate")

    topic_node_id, title, slug, article_md, diagram, audio_url = row


    publish_article(
        candidate_id=candidate_id,
        topic_node_id=topic_node_id,
        title=title,
        slug=slug,
        article_md=article_md,
        diagram=diagram,
        admin_user_id=admin_user_id,
        publish_date=publish_date,
        audio_url=audio_url
    )

    cursor.execute("""
        UPDATE article_candidate
        SET
            status = 'approved',
            scheduled_for = %s,
            reviewed_by = %s,
            reviewed_at = NOW()
        WHERE id = %s;
    """, (publish_date, admin_user_id, candidate_id))

    conn.commit()
    close_connection(conn)

def reject_candidate(candidate_id, reason, admin_user_id):
    update_candidate_status(
        candidate_id=candidate_id,
        status="rejected",
        reason=reason,
        reviewed_by=admin_user_id
    )