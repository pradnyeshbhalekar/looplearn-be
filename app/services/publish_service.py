from app.models.published_articles import publish_article
from app.models.article_candidate import update_candidate_status
from app.config.db import get_connection, close_connection


def approve_candidate(candidate_id, admin_user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_node_id, title, slug, article_md, diagram
        FROM article_candidate
        WHERE id = %s AND status = 'pending';
    """, (candidate_id,))
    row = cursor.fetchone()
    close_connection(conn)

    if not row:
        raise ValueError("Invalid candidate")

    topic_node_id, title, slug, article_md, diagram = row

    publish_article(
        candidate_id,
        topic_node_id,
        title,
        slug,
        article_md,
        diagram,
        admin_user_id
    )

    update_candidate_status(
        candidate_id=candidate_id,
        status="approved"
    )


def reject_candidate(candidate_id, reason, admin_user_id):
    update_candidate_status(
        candidate_id=candidate_id,
        status="rejected",
        reason=reason,
        rejected_by=admin_user_id
    )