import json
from app.config.db import get_connection, close_connection

def seed_real_plans():
    # Empty JSON array for the features column
    empty_features = json.dumps([])
    
    plans = [
        ("cybersecurity", "Cybersecurity", 99, empty_features),
        ("system_design", "System Design", 99, empty_features),
        ("operating_systems", "Operating Systems", 99, empty_features),
        ("backend_engineering", "Backend Engineering", 99, empty_features),
        ("apis", "APIs", 99, empty_features),
        ("distributed_systems", "Distributed Systems", 99, empty_features),
        ("frontend_engineering", "Frontend Engineering", 99, empty_features)
    ]

    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Clear out any old plans
        cursor.execute("DELETE FROM plans;")
        
        # Insert the new plans
        cursor.executemany("""
            INSERT INTO plans (domain, name, monthly_price, features)
            VALUES (%s, %s, %s, %s::jsonb)
        """, plans)
        
        conn.commit()
        print(f"✅ Successfully added {len(plans)} plans with empty features at ₹99/month!")
    except Exception as e:
        print(f"❌ Error inserting plans: {e}")
        conn.rollback()
    finally:
        close_connection(conn)

if __name__ == "__main__":
    seed_real_plans()