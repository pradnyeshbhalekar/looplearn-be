from app.models.graph import insert_node,insert_or_increment_edge
from app.config.db import get_connection, close_connection

def add_child_topics(parent_topic_id:str, child_concepts:list[str], domain_name:str=None):
    inserted = []

    domain_id = None
    if domain_name:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM concept_nodes WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s)) AND node_type = 'domain';", (domain_name,))
            row = cursor.fetchone()
            if row:
                domain_id = row[0]
        finally:
            close_connection(conn)

    for topic_name in child_concepts:
        node = insert_node(topic_name,"concept")
        child_node_id = node[0]

        insert_or_increment_edge(parent_topic_id,child_node_id)
        
        if domain_id:
            insert_or_increment_edge(domain_id, child_node_id)

        inserted.append({
            "child_topic":topic_name,
            "child_node_id":child_node_id
        })
    print(inserted)
    return inserted