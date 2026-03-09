from flask import Blueprint, jsonify, request
from app.models.published_articles import (
    get_published_by_slug,
    get_todays_published_article,
    get_todays_article,
)
from app.utils.jwt_utils import decode_jwt
from app.models.user import get_user_by_id, get_user_active_subscription


public_article_routes = Blueprint(
    "public_articles",
    __name__
)


@public_article_routes.get("/today")
def today_article():
    article = get_todays_article()
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
