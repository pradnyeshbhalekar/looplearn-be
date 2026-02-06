from flask import Blueprint,jsonify
from app.services.pipeline_service import run_pipeline

pipeline_bp = Blueprint("pipeline_bp",__name__)

@pipeline_bp.route("/run",methods = ["POST"])
def run():
    try:
        result = run_pipeline()
        return jsonify({
            "status":"success",
            "result": result
        })
    except Exception as e:
        return jsonify({
            "status":"error",
            "error":str(e)
        }),500
    

    