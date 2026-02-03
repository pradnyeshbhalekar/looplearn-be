from app.config.db import close_connection,get_connection
import json

def save_compiled_topic(topic_node_id:str,compiled:dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO compiled_topics(
                   topic_node_id,
                   theory,
                   topic_schema,
                   case_study,
                   interview_notes,
                   mermaid,   
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT(topic_node_id) DO NOTHING;
    """,(
        topic_node_id,
        json.dumps(compiled["theory"]),
        json.dumps(compiled["topic_schema"]),
        json.dumps(compiled["case_study"]),
        json.dumps(compiled["interview_notes"]),
        json.dumps(compiled["mermaid"]),
    ))

    conn.commit()
    close_connection(conn)