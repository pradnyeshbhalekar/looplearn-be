from flask import Flask, jsonify
from flask_cors import CORS

from app.models.schema import init_db
from app.models.graph import insert_node, get_all_nodes, insert_or_increment_edge
from app.routes.pipeline_routes import pipeline_bp
from app.routes.topic_routes import topic_bp
from app.routes.source_routes import source_bp

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return "Flask is running ✅"


@app.route("/api/test")
def test():
    return jsonify({"message": "API working ✅"})


@app.route("/api/init-db", methods=["POST"])
def init_database():
    init_db()
    return jsonify({"message": "✅ Database initialized"})


app.register_blueprint(topic_bp, url_prefix="/api/topics")
app.register_blueprint(source_bp,url_prefix='/api/sources')
app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")





if __name__ == "__main__":
    app.run(debug=True)
