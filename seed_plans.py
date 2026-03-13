import json
from app.config.db import get_connection, close_connection

def seed_real_plans():
    common = ["Commuter Mode (Audio Briefings)", "Weekly Architecture Reviews"]
    
    def get_features(domain_specific):
        return json.dumps(domain_specific + common)

    plans = [
        ("cybersecurity", "Cybersecurity", 99, get_features([
            "Real-world exploit analysis",
            "Threat modeling exercises",
            "Vulnerability research updates"
        ])),
        ("system_design", "System Design", 99, get_features([
            "Scalability & Availability patterns",
            "Real-world architecture case studies",
            "Load balancing strategies"
        ])),
        ("operating_systems", "Operating Systems", 99, get_features([
            "Kernel internals & Scheduling",
            "Memory management deep-dives",
            "Performance tuning at OS level"
        ])),
        ("backend_engineering", "Backend Engineering", 99, get_features([
            "High-performance API design",
            "Caching & Message queue patterns",
            "SQL vs NoSQL trade-offs"
        ])),
        ("apis", "APIs", 99, get_features([
            "REST, GraphQL & gRPC deep-dives",
            "API Gateway implementation",
            "Versioning & Webhook strategies"
        ])),
        ("distributed_systems", "Distributed Systems", 99, get_features([
            "Consensus algorithms (Raft/Paxos)",
            "Eventual consistency patterns",
            "Distributed transaction management"
        ])),
        ("frontend_engineering", "Frontend Engineering", 99, get_features([
            "Modern rendering (SSR/RSC)",
            "State management architecture",
            "Web performance optimization"
        ])),
        ("databases", "Databases", 99, get_features([
            "Query & Index optimization",
            "Isolation levels & Concurrency",
            "LSM-Trees vs B-Trees"
        ])),
        ("cloud_computing", "Cloud Computing", 99, get_features([
            "Infrastructure as Code (IaC)",
            "Serverless & Edge computing",
            "Cloud-native security patterns"
        ]))
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
        print(f"✅ Successfully added {len(plans)} plans with professional features at ₹99/month!")
    except Exception as e:
        print(f"❌ Error inserting plans: {e}")
        conn.rollback()
    finally:
        close_connection(conn)

if __name__ == "__main__":
    seed_real_plans()