from app.config.db import get_connection, close_connection


def create_workspace_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspaces(
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            owner_id UUID REFERENCES users(id),
            seat_limit INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspace_members(
            workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id),
            role VARCHAR(20) CHECK (role IN ('admin','member')) DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(workspace_id, user_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_workspace_members_user
        ON workspace_members(user_id);
    """)

    conn.commit()
    close_connection(conn)


def is_workspace_admin(workspace_id, user_id):
    """Checks if a user has the 'admin' role in a workspace."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s;
        """, (workspace_id, user_id))
        row = cursor.fetchone()
        return row is not None and row[0] == 'admin'
    finally:
        close_connection(conn)


def get_active_team_subscription(workspace_id):
    """Returns the active team subscription for a workspace, if any."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Find the owner of the workspace and then their active team subscription
        cursor.execute("""
            SELECT s.id, s.plan_id, s.status, s.ends_at, p.domain, p.name AS plan_name
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            JOIN workspaces w ON w.owner_id = s.user_id
            WHERE w.id = %s
              AND s.status = 'active'
              AND s.is_team = TRUE
              AND (s.ends_at IS NULL OR s.ends_at > NOW())
            ORDER BY s.ends_at DESC NULLS LAST, s.id DESC
            LIMIT 1;
        """, (workspace_id,))
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