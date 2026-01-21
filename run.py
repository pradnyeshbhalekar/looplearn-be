from flask import Flask, jsonify
from flask_cors import CORS

from app.models.schema import init_db
from app.models.graph import insert_node, get_all_nodes, insert_or_increment_edge

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


@app.route("/api/demo", methods=["POST"])
def demo_insert():
    mvcc = insert_node("MVCC", "concept")
    nodes = get_all_nodes()

    edge = None
    if nodes:
        databases_id = nodes[0][0]
        mvcc_id = mvcc[0]
        edge = insert_or_increment_edge(databases_id, mvcc_id)

    return jsonify({
        "inserted_node": mvcc,
        "total_nodes": len(nodes),
        "inserted_edge": edge
    })


if __name__ == "__main__":
    app.run(debug=True)
