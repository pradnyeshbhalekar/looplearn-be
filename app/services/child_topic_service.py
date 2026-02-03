from app.models.graph import insert_node,insert_or_increment_edge

def add_child_topics(parent_topic_id:str,child_concepts:list[str]):
    inserted = []

    for topic_name in child_concepts:
        node = insert_node(topic_name,"concept")
        child_node_id = node[0]

        insert_or_increment_edge(parent_topic_id,child_node_id)

        inserted.append({
            "child_topic":topic_name,
            "child_node_id":child_node_id
        })
    print(inserted)
    return inserted