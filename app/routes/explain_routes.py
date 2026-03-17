from flask import Blueprint,request,jsonify
from app.services.explain_service import fetch_explanation
from app.utils.rate_limiter import llm_limiter


explain_bp  = Blueprint('explain',__name__)

@explain_bp.route("/",methods=['POST'])
def get_explaination():
    data = request.get_json()
    highlighted_text = data.get("highlightedText")
    surrounding_context = data.get('surroundingContext')

    if not highlighted_text or not surrounding_context:
        return jsonify({"Error":"Missing required fields"}),400
    
    normalized_term = highlighted_text.lower().strip()

    try:
        generated_explanation = llm_limiter.execute(fetch_explanation, normalized_term, surrounding_context)
    except Exception as e:
        print(f"Error fetching explanation: {e}")
        return jsonify({"error": "The tutor is currently overwhelmed. Try again in a moment."}), 503


    return jsonify({"explanation": generated_explanation}), 200