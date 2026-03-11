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