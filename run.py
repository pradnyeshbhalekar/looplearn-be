from flask import Flask, jsonify
from flask_cors import CORS

from app.models.schema import init_db
from app.models.graph import insert_node, get_all_nodes, insert_or_increment_edge
from app.routes.pipeline_routes import pipeline_bp
from app.routes.topic_routes import topic_bp
from app.routes.source_routes import source_bp
from app.routes.admin_candidate_routes import admin_candidate_routes
from app.routes.public_article_routes import public_article_routes
from app.routes.auth_routes import auth_routes
from app.routes.subscription_routes import subscription_routes

app = Flask(__name__)


CORS(app, origins=['http://localhost:5173','https://looplearn-nine.vercel.app'], supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

@app.after_request
def add_headers(response):
    # Allow Google OAuth to work by not restricting opener policy
    response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response


@app.route("/")
def home():
    return "Flask is running"


@app.route("/api/test")
def test():
    return jsonify({"message": "API working "})


@app.route("/api/init-db", methods=["POST"])
def init_database():
    init_db()
    return jsonify({"message": "✅ Database initialized"})


app.register_blueprint(topic_bp, url_prefix="/api/topics")
app.register_blueprint(source_bp,url_prefix='/api/sources')
app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")
app.register_blueprint(admin_candidate_routes,url_prefix="/api/admin/candidates")
app.register_blueprint(public_article_routes,url_prefix='/api/articles')
app.register_blueprint(auth_routes,url_prefix="/api/auth")
app.register_blueprint(subscription_routes,url_prefix='/api/subscriptions')





if __name__ == "__main__":
    app.run(debug=True)
