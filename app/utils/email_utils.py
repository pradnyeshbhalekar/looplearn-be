from app.config.db import get_connection,close_connection

def get_admin_emails():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT u.email FROM users u JOIN user_roles ur ON u.id = ur.user_id WHERE ur.role = 'admin'
                   """)
    rows = cursor.fetchall()
    return [r[0] for r in rows]