from flask import Blueprint, jsonify
from app.models.published_articles import get_published_by_slug

public_article_routes = Blueprint(
    "public_articles",
    __name__
)

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