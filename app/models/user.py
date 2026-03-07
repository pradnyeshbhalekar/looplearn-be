from app.config.db import get_connection, close_connection

def create_user_table():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (
                    role IN ('admin', 'editor', 'viewer')
                ),
                PRIMARY KEY (user_id)
            );
        """)
        
        conn.commit()
        cursor.close()
        print("Created users and user_roles tables successfully")
    finally:
        close_connection(conn)

def create_plans_table():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                domain TEXT,
                billing_cycle TEXT,
                name TEXT,
                monthly_price INTEGER,
                features JSONB
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Fixed missing comma & added default
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                plan_id UUID REFERENCES plans(id) ON DELETE CASCADE,
                status TEXT CHECK (
                    status IN ('active', 'paused', 'cancelled')
                ),
                started_at TIMESTAMP DEFAULT NOW(),
                ends_at TIMESTAMP
            );
        """)
        
        conn.commit()
        cursor.close()
        print("Created plans and subscriptions successfully")
    finally:
        close_connection(conn)

def get_or_create_user(email: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM users WHERE email = %s
        """, (email,))
        
        row = cursor.fetchone()

        if row:
            return row[0]
        

        cursor.execute("""
            INSERT INTO users (email) VALUES (%s) RETURNING id
        """, (email,))
        user_id = cursor.fetchone()[0]


        cursor.execute("""
            INSERT INTO user_roles (user_id, role) VALUES (%s, 'viewer')
        """, (user_id,))

        conn.commit()
        return user_id
    finally:
        close_connection(conn)

def get_user_active_subscription(user_id):
    """Returns the user's active subscription with its domain, or None if free user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.plan_id, s.status, s.ends_at, p.domain, p.name AS plan_name
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            WHERE s.user_id = %s
              AND s.status = 'active'
              AND (s.ends_at IS NULL OR s.ends_at > NOW())
            LIMIT 1;
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "subscription_id": row[0],
            "plan_id": row[1],
            "status": row[2],
            "ends_at": row[3],
            "domain": row[4],
            "plan_name": row[5],
        }
    finally:
        close_connection(conn)

def get_user_by_id(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Changed to LEFT JOIN just in case a user somehow doesn't have a role, 
        # it won't break the entire login flow.
        cursor.execute("""
            SELECT
                u.id,
                u.email,
                COALESCE(r.role, 'viewer') as role
            FROM users u
            LEFT JOIN user_roles r ON r.user_id = u.id
            WHERE u.id = %s AND u.is_active = TRUE
            LIMIT 1;
        """, (user_id,))

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "email": row[1],
            "role": row[2],
        }
    finally:

        close_connection(conn)