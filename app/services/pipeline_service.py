from app.services.pick_topic import pick_topic
from app.services.fetcher import fetch_candidate_source
from app.services.source_service import store_sources_bulk
from app.config.db import get_connection, close_connection
from app.services.source_scrape_service import scrape_and_store
from app.services.topic_compiler import compile_topic
from app.services.compiled_topic_service import save_compiled_topic
from app.services.child_topic_service import add_child_topics
from app.models.article_candidate import create_candidate
from slugify import slugify   # python-slugify
import json

def render_article_md(compiled: dict) -> str:
    parts = []

    # Title
    parts.append(f"# {compiled.get('topic')}\n")

    # THEORY
    theory = compiled.get("theory", {})
    if theory:
        parts.append("## Theory\n")
        if theory.get("overview"):
            parts.append(theory["overview"] + "\n")

        if theory.get("key_principles"):
            parts.append("### Key Principles\n")
            for p in theory["key_principles"]:
                parts.append(f"- {p}")
            parts.append("")

        if theory.get("tradeoffs"):
            parts.append("### Trade-offs\n")
            for t in theory["tradeoffs"]:
                parts.append(f"- {t}")
            parts.append("")

    # TOPIC SCHEMA
    schema = compiled.get("topic_schema", {})
    if schema:
        parts.append("## Conceptual Breakdown\n")
        for name, desc in schema.items():
            parts.append(f"### {name}\n{desc}\n")

    # CASE STUDY
    case = compiled.get("case_study", {})
    if case:
        parts.append("## Case Study\n")
        if case.get("system"):
            parts.append(f"**System:** {case['system']}\n")
        if case.get("description"):
            parts.append(case["description"] + "\n")

        if case.get("key_takeaways"):
            parts.append("### Key Takeaways\n")
            for k in case["key_takeaways"]:
                parts.append(f"- {k}")
            parts.append("")

    # INTERVIEW NOTES
    notes = compiled.get("interview_notes", {})
    if notes:
        parts.append("## Interview Notes\n")

        if notes.get("common_questions"):
            parts.append("### Common Questions\n")
            for q in notes["common_questions"]:
                parts.append(f"- {q}")
            parts.append("")

        if notes.get("common_mistakes"):
            parts.append("### Common Mistakes\n")
            for m in notes["common_mistakes"]:
                parts.append(f"- {m}")
            parts.append("")

        if notes.get("what_interviewers_look_for"):
            parts.append("### What Interviewers Look For\n")
            for w in notes["what_interviewers_look_for"]:
                parts.append(f"- {w}")
            parts.append("")

    return "\n".join(parts).strip()

def run_pipeline():
    topic = pick_topic()
    if not topic:
        raise RuntimeError("No topic could be picked")

    topic_id = topic["topic_node_id"]
    topic_name = topic["topic_name"]

    # 1️⃣ Fetch & store sources
    fetched_sources = fetch_candidate_source(topic_name)
    store_sources_bulk(fetched_sources)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url
        FROM sources
        WHERE scrape_status = 'pending'
        LIMIT 10;
    """)
    rows = cursor.fetchall()
    close_connection(conn)

    scraped_result = []
    for source_id, url in rows:
        scraped_result.append(scrape_and_store(source_id, url))

    # 2️⃣ Compile topic
    compiled = compile_topic(topic_name, [topic_name])

    # 3️⃣ Persist compiled structure
    compiled_id = save_compiled_topic(topic_id, compiled)

    # 4️⃣ Derive ARTICLE FIELDS (THIS WAS MISSING)
    title = f"{topic_name} – Complete Guide"
    slug = slugify(title)
    article_md = render_article_md(compiled)

    diagram = None
    if "mermaid" in compiled:
        diagram = compiled["mermaid"].get("code")

    # 5️⃣ Create candidate article
    candidate_id = create_candidate(
        compiled_topic_id=compiled_id,
        topic_node_id=topic_id,
        title=title,
        slug=slug,
        article_md=article_md,
        diagram=diagram
    )

    print("✅ CANDIDATE CREATED:", candidate_id)

    # 6️⃣ Child topics
    child_topics = compiled.get("child_topics", [])
    child_inserted = add_child_topics(topic_id, child_topics)

    return {
        "candidate_id": candidate_id,
        "topic_id": topic_id,
        "topic_name": topic_name,
        "source_fetched": len(fetched_sources),
        "source_scraped": len(scraped_result),
        "child_topic_added": child_inserted
    }