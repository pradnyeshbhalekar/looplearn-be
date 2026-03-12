from operator import index
from app.services.pick_topic import pick_topic,pick_topic_domain
from app.services.fetcher import fetch_candidate_source
from app.services.source_service import store_sources_bulk
from app.config.db import get_connection, close_connection
from app.services.source_scrape_service import scrape_and_store
from app.services.topic_compiler import compile_topic
from app.services.compiled_topic_service import save_compiled_topic
from app.services.child_topic_service import add_child_topics
from app.models.article_candidate import create_candidate, update_candidate_status
from slugify import slugify   # python-slugify
from app.models.published_articles import publish_article, set_article_audience
from datetime import date, timedelta
import threading
import uuid
from app.models.pipeline_jobs import create_job, update_job
from app.models.graph import insert_node, insert_or_increment_edge

def render_article_md(compiled: dict) -> str:
    parts = []

    # Title
    parts.append(f"# {compiled.get('topic')}\n")
    
    # Hook & Introduction
    if compiled.get("intro_hook"):
        parts.append(f"*{compiled.get('intro_hook')}*\n")
        
    if compiled.get("what_is_it"):
        parts.append("## What Is It?\n")
        parts.append(str(compiled.get("what_is_it")) + "\n")
        
    if compiled.get("why_is_it_important"):
        parts.append("## Why Is It Important?\n")
        parts.append(str(compiled.get("why_is_it_important")) + "\n")
        
    if compiled.get("what_if_it_wasnt_there"):
        parts.append("## What If It Wasn't There?\n")
        parts.append(str(compiled.get("what_if_it_wasnt_there")) + "\n")

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


    compiled = compile_topic(topic_name, [topic_name])


    compiled_id = save_compiled_topic(topic_id, compiled)


    title = f"{topic_name}"
    slug = slugify(title)
    article_md = render_article_md(compiled)

    diagram = None
    if "mermaid" in compiled:
        diagram = compiled["mermaid"].get("code")

    domain_name = topic.get("domain", "")

    # Generate Audio
    from app.services.audio_service import create_commuter_audio
    print(f"🎙️ Generating commuter audio for topic: {topic_name}...")
    audio_url, timestamps = create_commuter_audio(article_md, slug, domain_name, title)

    # 5️⃣ Create candidate article
    candidate_id = create_candidate(
        compiled_topic_id=compiled_id,
        topic_node_id=topic_id,
        title=title,
        slug=slug,
        article_md=article_md,
        diagram=diagram,
        audio_url=audio_url
    )

    print("✅ CANDIDATE CREATED:", candidate_id)

    # 6️⃣ Child topics
    child_topics = compiled.get("child_topics", [])
    child_inserted = add_child_topics(topic_id, child_topics, domain_name)

    return {
        "candidate_id": candidate_id,
        "topic_id": topic_id,
        "topic_name": topic_name,
        "source_fetched": len(fetched_sources),
        "source_scraped": len(scraped_result),
        "child_topic_added": child_inserted
    }


import re
def slugify(text):
    text = text.lower()
    return re.sub(r'[\W_]+', '-', text).strip('-')



def start_premium_pipeline_job(domain: str):
    job_id = str(uuid.uuid4())
    create_job(job_id)

    t = threading.Thread(
        target=_run_premium_pipeline_job,
        args=(job_id, domain),
        daemon=True
    )
    t.start()

    return job_id



def _run_premium_pipeline_job(job_id: str, domain: str):
    """Runs the pipeline and updates the job status upon success or failure."""
    update_job(job_id, "running")

    try:
        result = run_premium_pipeline(domain)
        update_job(job_id, "completed", result=result)

        topic_name = result.get("topic_name")
        if topic_name:
            try:
                from app.services.email_service import send_admin_notification
                from app.utils.email_utils import get_admin_emails
                emails = get_admin_emails()
                if emails:
                    send_admin_notification(emails, topic_name)
            except Exception as mail_err:
                print(f"⚠️ Email notification failed: {mail_err}")
    except Exception as e:
        update_job(job_id, "failed", error=str(e))
        print(f"Pipeline failed for {domain}: {e}")


def run_premium_pipeline(domain: str):
    """Fetches, scrapes, compiles, and AUTO-PUBLISHES for tomorrow."""
    

    topic = pick_topic_domain(domain)
    if not topic:

        topic = pick_topic()
        if not topic:
            raise RuntimeError(f"No pending topics found for domain: {domain}")

    topic_id = topic["topic_node_id"]
    topic_name = topic["topic_name"]
    actual_domain = topic.get("domain", domain or "System Design")
    print(f"Starting generation for: {topic_name} (Requested: {domain or 'auto'}, Actual: {actual_domain})")


    fetched_sources = fetch_candidate_source(topic_name)
    store_sources_bulk(fetched_sources)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, url
            FROM sources
            WHERE scrape_status = 'pending'
            LIMIT 10;
        """)
        rows = cursor.fetchall()
    finally:
        close_connection(conn)


    scraped_result = []
    for source_id, url in rows:
        scraped_result.append(scrape_and_store(source_id, url))


    compiled = compile_topic(topic_name, [topic_name])


    compiled_id = save_compiled_topic(topic_id, compiled)

    # 6️⃣ Derive ARTICLE FIELDS
    title = f"{topic_name} – Complete Guide"
    slug = slugify(title)
    article_md = render_article_md(compiled)

    diagram = None
    if "mermaid" in compiled:
        diagram = compiled["mermaid"].get("code")

    domain_name = actual_domain

    # Generate Audio
    from app.services.audio_service import create_commuter_audio
    print(f"🎙️ Generating commuter audio for topic: {topic_name}...")
    audio_url, timestamps = create_commuter_audio(article_md, slug, domain_name, title)

    # 7️⃣ Create candidate and AUTO-PUBLISH
    tomorrow = date.today() + timedelta(days=1)
    candidate_id = create_candidate(
        compiled_topic_id=compiled_id,
        topic_node_id=topic_id,
        title=title,
        slug=slug,
        article_md=article_md,
        diagram=diagram,
        audio_url=audio_url
    )
    article_id = publish_article(
        candidate_id=candidate_id,
        topic_node_id=topic_id,
        title=title,
        slug=slug,
        article_md=article_md,
        diagram=diagram,
        admin_user_id=None,
        publish_date=tomorrow,
        audio_url=audio_url
    )
    set_article_audience(article_id, "subscriber")
    try:
        domain_node = insert_node(domain, "domain")
        insert_or_increment_edge(domain_node[0], topic_id)
    except Exception as _:
        pass
    # Mark candidate as approved so it doesn't appear in admin pending list
    update_candidate_status(
        candidate_id=candidate_id,
        status="approved",
        reason=None,
        reviewed_by=None,
        scheduled_for=tomorrow
    )

    print(f"🚀 AUTO-PUBLISHED '{title}' directly to DB (Scheduled for {tomorrow})")

    # 8️⃣ Child topics
    child_topics = compiled.get("child_topics", [])
    child_inserted = add_child_topics(topic_id, child_topics, domain_name)

    result = {
        "article_id": article_id,
        "candidate_id": candidate_id,
        "topic_id": topic_id,
        "topic_name": topic_name,
        "domain": domain or "auto",
        "scheduled_for": str(tomorrow),
        "source_fetched": len(fetched_sources),
        "source_scraped": len(scraped_result),
        "child_topic_added": child_inserted
    }
    return result


# ==========================================
# 4. ALL-DOMAINS PIPELINE
# ==========================================
def start_all_domains_pipeline_job():
    """Kicks off a single background job that runs the pipeline for every domain."""
    job_id = str(uuid.uuid4())
    create_job(job_id)

    t = threading.Thread(
        target=_run_all_domains_pipeline_job,
        args=(job_id,),
        daemon=True
    )
    t.start()

    return job_id


def _run_all_domains_pipeline_job(job_id: str):
    update_job(job_id, "running")

    try:
        result = run_all_domains_pipeline()
        update_job(job_id, "completed", result=result)

        # Send summary email to admins
        try:
            from app.services.email_service import send_all_domains_report
            from app.utils.email_utils import get_admin_emails
            emails = get_admin_emails()
            if emails:
                send_all_domains_report(emails, result)
        except Exception as mail_err:
            print(f"⚠️ Email notification failed: {mail_err}")
    except Exception as e:
        update_job(job_id, "failed", error=str(e))
        print(f"All-domains pipeline failed: {e}")  


def run_all_domains_pipeline():
    """Runs the premium pipeline for every domain. Returns a summary of results."""
    from app.models.graph import get_all_domain_names
    from app.utils.email_utils import get_admin_emails
    from app.services.email_service import send_admin_notification
    import time

    domains = get_all_domain_names()
    if not domains:
        raise RuntimeError("No domains found in the database")

    successes = []
    failures = []

    for domain in domains:
        try:
            print(f" Running pipeline for domain: {domain}")
            result = run_premium_pipeline(domain)
            successes.append(result)
            print(f"Completed: {domain} → {result['topic_name']}")
            time.sleep(5)
            try:
                emails = get_admin_emails()
                if emails and result.get("topic_name"):
                    send_admin_notification(emails, result["topic_name"])
            except Exception as mail_err:
                print(f"⚠️ Email notification failed for {domain}: {mail_err}")
        except Exception as e:
            failures.append({"domain": domain, "error": str(e)})
            print(f"Failed: {domain} → {e}")

    return {
        "total_domains": len(domains),
        "succeeded": len(successes),
        "failed": len(failures),
        "results": successes,
        "errors": failures,
    }
