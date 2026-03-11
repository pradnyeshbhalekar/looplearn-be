from app.config.db import get_connection, close_connection


def create_workspace(name,owner_id,seat_limit = 5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO workspaces(name,owner_id,seat_limit) VALUES
                   (%s,%s,%s)
                   RETURNING id;
                   """,(name,owner_id,seat_limit))
    

    workspace_id = cursor.fetchone()[0]
    
    cursor.execute("""
            INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'admin');
                   """,(workspace_id,owner_id))
    
    conn.commit()
    close_connection(conn)

    return workspace_id


def add_workspace_member(workspace_id,user_id,role='member'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            INSERT INTO workspace_members(workspace_id,user_id,role)
                   VALUES (%s,%s,%s)
                   ON CONFLICT DO NOTHING;
                   """,(workspace_id,user_id,role))
    
    conn.commit()
    close_connection(conn)


def remove_workspace_member(workspace_id,user_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM workspace_members
                   WHERE workspace_id=%s AND user_id=%s
                   """,(workspace_id,user_id))
    
    conn.commit()
    close_connection(conn)


def get_user_workspaces(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT w.id, w.name, w.owner_id, w.seat_limit, w.created_at
                   FROM workspace_members wm
                   JOIN workspaces w ON wm.workspace_id = w.id
                   WHERE wm.user_id=%s
                   """,(user_id,))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    result = [dict(zip(columns,row)) for row in rows]

    close_connection(conn)
    return result

def get_workspace_members(workspace_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.id, users.email, wm.role, wm.joined_at
                   FROM workspace_members wm
                   JOIN users ON users.id = wm.user_id
                   WHERE wm.workspace_id = %s;
                   """,(workspace_id,))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    result = [dict(zip(columns,row)) for row in rows]

    close_connection(conn)
    return result
    
def delete_workspace(workspace_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM workspaces
        WHERE id=%s;
    """, (workspace_id,))

    conn.commit()
    close_connection(conn)