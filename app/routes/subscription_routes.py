from flask import Flask,Blueprint,jsonify,request
from app.config.db import get_connection,close_connection
from app.utils.auth_decorators import require_auth
from app.models.user import get_user_active_subscription
from app.models.published_articles import (
    get_todays_published_article,
    get_latest_published_article,
    get_todays_published_article_pref_subscriber,
    get_todays_subscriber_article
)
from app.services.razorpay_service import razorpay_client
import os
import hmac
import hashlib

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
        cursor.execute('SELECT id, name, domain, billing_cycle, monthly_price FROM plans WHERE id = %s', (plan_id,))
        plan_row = cursor.fetchone()
        if not plan_row:
            return jsonify({"error": "plan not found"}), 404
        plan_id_db, plan_name, plan_domain, billing_cycle, monthly_price = plan_row
        cycle_raw = (billing_cycle or "monthly").strip().lower()
        if cycle_raw in ("monthly", "month", "m"):
            period = "monthly"
            total_count = 12
            interval_days = "30 days"
        elif cycle_raw in ("yearly", "annual", "year", "y"):
            period = "yearly"
            total_count = 1
            interval_days = "365 days"
        elif cycle_raw in ("weekly", "week", "w"):
            period = "weekly"
            total_count = 4
            interval_days = "28 days"
        elif cycle_raw in ("daily", "day", "d"):
            period = "daily"
            total_count = 30
            interval_days = "30 days"
        else:
            period = "monthly"
            total_count = 12
            interval_days = "30 days"
        interval = 1
        amount_paise = int(monthly_price) * 100
        rp_plan = razorpay_client.plan.create({
            "period": period,
            "interval": interval,
            "item": {
                "name": f"LoopLearn {plan_name}",
                "amount": amount_paise,
                "currency": "INR",
                "description": f"{plan_domain} subscription"
            }
        })
        redirect_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/") + "/subscription/success"
        rp_subscription = razorpay_client.subscription.create({
            "plan_id": rp_plan["id"],
            "total_count": total_count,
            "customer_notify": 1,
            "notes": {
                "user_id": str(user_id),
                "plan_id": str(plan_id_db),
                "domain": plan_domain
            }
        })
        
        cursor.execute(f"""
            INSERT INTO subscriptions (user_id, plan_id, status, started_at, ends_at) 
            VALUES (%s, %s, 'pending', NOW(), NULL)
            RETURNING id, ends_at
        """, (user_id, plan_id))
        
        result = cursor.fetchone()
        cursor.execute("""
            UPDATE subscriptions
            SET razorpay_subscription_id = %s,
                razorpay_plan_id = %s
            WHERE id = %s
        """, (rp_subscription.get("id"), rp_plan.get("id"), result[0]))
        conn.commit()

        return jsonify({
            "message": "subscription created, pending payment",
            "subscription_id": result[0],
            "ends_at": result[1],
            "razorpay": {
                "subscription_id": rp_subscription.get("id"),
                "status": rp_subscription.get("status"),
                "short_url": rp_subscription.get("short_url"),
                "redirect_url": redirect_url
            }
        })
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        close_connection(conn)

@subscription_routes.post("/webhook")
def razorpay_webhook():
    body = request.data
    signature = request.headers.get("X-Razorpay-Signature", "")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if secret:
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if digest != signature:
            return jsonify({"error": "invalid signature"}), 400
    data = request.get_json(silent=True) or {}
    event = data.get("event")
    entity = (data.get("payload", {}).get("subscription", {}) or {}).get("entity", {}) or {}
    status = entity.get("status")
    rzp_sub_id = entity.get("id")
    notes = entity.get("notes", {}) or {}
    user_id = notes.get("user_id")
    plan_id = notes.get("plan_id")
    if not user_id or not plan_id:
        if not rzp_sub_id:
            return jsonify({"ok": True})
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT billing_cycle FROM plans WHERE id = %s", (plan_id,))
        row = cursor.fetchone()
        cycle_raw = (row[0] if row else "monthly") or "monthly"
        cycle_raw = cycle_raw.strip().lower()
        if cycle_raw in ("monthly", "month", "m"):
            interval_days = "30 days"
        elif cycle_raw in ("yearly", "annual", "year", "y"):
            interval_days = "365 days"
        elif cycle_raw in ("weekly", "week", "w"):
            interval_days = "7 days"
        elif cycle_raw in ("daily", "day", "d"):
            interval_days = "1 day"
        else:
            interval_days = "30 days"
        if event in ("subscription.activated", "subscription.completed") or status in ("active", "authenticated"):
            if rzp_sub_id:
                cursor.execute(f"""
                    UPDATE subscriptions
                    SET status = 'active',
                        started_at = NOW(),
                        ends_at = NOW() + INTERVAL '{interval_days}'
                    WHERE razorpay_subscription_id = %s;
                """, (rzp_sub_id,))
            else:
                cursor.execute(f"""
                    UPDATE subscriptions
                    SET status = 'active',
                        started_at = NOW(),
                        ends_at = NOW() + INTERVAL '{interval_days}'
                    WHERE user_id = %s AND plan_id = %s AND status = 'pending';
                """, (user_id, plan_id))
            conn.commit()
        elif event in ("subscription.halted", "subscription.paused", "subscription.cancelled") or status in ("halted", "paused", "cancelled"):
            if rzp_sub_id:
                cursor.execute("""
                    UPDATE subscriptions
                    SET status = %s
                    WHERE razorpay_subscription_id = %s;
                """, (status, rzp_sub_id))
            else:
                cursor.execute("""
                    UPDATE subscriptions
                    SET status = %s
                    WHERE user_id = %s AND plan_id = %s;
                """, (status, user_id, plan_id))
            conn.commit()
        return jsonify({"ok": True})
    finally:
        close_connection(conn)

@subscription_routes.get("/me")
@require_auth
def my_subscription(user):
    sub = get_user_active_subscription(user["user_id"])
    if not sub:
        return jsonify({"status": "none"})
    return jsonify({
        "status": "active",
        "subscription": sub
    })


@subscription_routes.get("/me/today")
@require_auth
def my_today_article(user):
    subscription = get_user_active_subscription(user["user_id"])
    if not subscription:
        return jsonify({"error": "active subscription required"}), 403
    article = get_todays_subscriber_article(subscription["domain"])
    if not article:
        article = get_todays_published_article(subscription["domain"])
        if not article:
            article = get_latest_published_article(subscription["domain"])
        if not article:
            return jsonify({"error": f"No article available for {subscription['domain']}"}), 404
    article["subscription"] = {
        "plan": subscription["plan_name"],
        "domain": subscription["domain"],
    }
    return jsonify(article)
