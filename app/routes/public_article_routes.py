from flask import Blueprint, jsonify, request
from app.models.published_articles import (
    get_published_by_slug,
    get_todays_published_article,
    get_todays_free_article,
)
from app.utils.jwt_utils import decode_jwt
from app.models.user import get_user_by_id, get_user_active_subscription


public_article_routes = Blueprint(
    "public_articles",
    __name__
)


@public_article_routes.get("/today")
def today_article():
    """
    Subscribed users → today's article for their subscribed domain.
    Free / unauthenticated users → today's article from a random domain.
    """
    # Optional auth: try to identify the user
    user = None
    header = request.headers.get("Authorization")
    if header and header.startswith("Bearer "):
        token = header.split(" ")[1]
        try:
            payload = decode_jwt(token)
            user_id = payload.get("user_id")
            if user_id:
                user = get_user_by_id(user_id)
        except Exception:
            pass

    if user:
        subscription = get_user_active_subscription(user["id"])
        if subscription:
            article = get_todays_published_article(subscription["domain"])
            if article:
                article["subscription"] = {
                    "plan": subscription["plan_name"],
                    "domain": subscription["domain"],
                }
                return jsonify(article)
            return jsonify({"error": f"No article published today for {subscription['domain']}"}), 404

    # Free / unauthenticated user → random domain
    article = get_todays_free_article()
    if not article:
        return jsonify({"error": "No article published today"}), 404

    return jsonify(article)


@public_article_routes.get("/<slug>")
def get_article(slug):
    article = get_published_by_slug(slug)
    if not article:
        return jsonify({"error": "Not found"}), 404

    title, article_md, diagram, published_at = article

    return jsonify({
        "title": title,
        "content": article_md,
        "diagram": diagram,
        "published_at": published_at
    })
