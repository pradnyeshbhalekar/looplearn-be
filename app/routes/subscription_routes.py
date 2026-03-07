from flask import Flask,Blueprint,jsonify,request
from app.config.db import get_connection,close_connection
from app.utils.auth_decorators import require_auth
from app.models.user import get_user_active_subscription
from app.models.published_articles import get_todays_published_article

subscription_routes = Blueprint('subscription',__name__)

@subscription_routes.get("/plans")
def get_plans():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, name, domain, billing_cycle,monthly_price,features FROM plans
                       """)
        columns = [col[0] for col in cursor.description]
        plans = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(plans)
    finally:
        close_connection(conn)
@subscription_routes.post("/subscribe")
@require_auth  
def mock_subscribe(user): 
    data = request.get_json()
    plan_id = data.get('plan_id')
    

    user_id = user["user_id"] 

    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
        
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM plans WHERE id = %s', (plan_id,))
        if not cursor.fetchone():
            return jsonify({"error": "plan not found"}), 404
        
        cursor.execute("""
            INSERT INTO subscriptions (user_id, plan_id, status, started_at, ends_at) 
            VALUES (%s, %s, 'active', NOW(), NOW() + INTERVAL '30 days')
            RETURNING id, ends_at
        """, (user_id, plan_id))
        
        result = cursor.fetchone()
        conn.commit()

        return jsonify({
            "message": "successfully subscribed",
            "subscription_id": result[0],
            "ends_at": result[1]
        })
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        close_connection(conn)

@subscription_routes.get("/me/today")
@require_auth
def my_today_article(user):
    subscription = get_user_active_subscription(user["user_id"])
    if not subscription:
        return jsonify({"error": "active subscription required"}), 403
    article = get_todays_published_article(subscription["domain"])
    if not article:
        return jsonify({"error": f"No article published today for {subscription['domain']}"}), 404
    article["subscription"] = {
        "plan": subscription["plan_name"],
        "domain": subscription["domain"],
    }
    return jsonify(article)
