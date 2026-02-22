from app.config.db import get_connection, close_connection
import json

def save_compiled_topic(topic_node_id: str, compiled: dict) -> str:
    conn = get_connection()
    cursor = conn.cursor()

    def _dump_if_present(key):
        val = compiled.get(key)
        return json.dumps(val) if val is not None else None

    cursor.execute("""
        INSERT INTO compiled_topics(
            topic_node_id,
            theory,
            topic_schema,
            case_study,
            interview_notes,
            mermaid
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(topic_node_id) DO UPDATE
        SET theory = EXCLUDED.theory,
            topic_schema = EXCLUDED.topic_schema,
            case_study = EXCLUDED.case_study,
            interview_notes = EXCLUDED.interview_notes,
            mermaid = EXCLUDED.mermaid
        RETURNING id;
    """, (
        topic_node_id,
        _dump_if_present("theory"),
        _dump_if_present("topic_schema"),
        _dump_if_present("case_study"),
        _dump_if_present("interview_notes"),
        _dump_if_present("mermaid"),
    ))

    compiled_id = cursor.fetchone()[0]

    conn.commit()
    close_connection(conn)

    return compiled_id