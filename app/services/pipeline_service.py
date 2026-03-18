from operator import index
import json
import os
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
    segments = []
    
    # Intro
    segments.append(f"{compiled.get('intro_hook', '')}\n\n{compiled.get('what_is_it', '')}")
    
    # Why Important
    segments.append(f"## Why is it important?\n{compiled.get('why_is_it_important', '')}")
    
    # Theory
    theory = compiled.get("theory", {})
    if theory:
        t_md = f"## Core Principles\n{theory.get('overview', '')}\n\n"
        for p in theory.get("key_principles", []):
            t_md += f"- **{p}**\n"
        
        t_md += "\n### Trade-offs\n"
        for tr in theory.get("tradeoffs", []):
            if isinstance(tr, dict):
                strategy = tr.get("strategy", "Strategy")
                t_md += f"- **{strategy}**:\n"
                for p in tr.get("pros", []):
                    t_md += f"  - Pro: {p}\n"
                for c in tr.get("cons", []):
                    t_md += f"  - Con: {c}\n"
            else:
                t_md += f"- {tr}\n"
        segments.append(t_md)

    # Observability
    metrics = compiled.get("observability_metrics", [])
    if metrics:
        m_md = "## Operational Essentials\n"
        for m in metrics:
            m_md += f"- **{m.get('metric')}**: {m.get('importance')}\n"
        segments.append(m_md)

    # Anti-patterns
    antis = compiled.get("anti_patterns", [])
    if antis:
        a_md = "## Common Pitfalls\n"
        for a in antis:
            a_md += f"- **{a.get('pattern')}**: {a.get('consequence')}\n"
        segments.append(a_md)

    # Case Study
    cs = compiled.get("case_study", {})
    if cs:
        cs_md = f"## Architecture in Action: {cs.get('system', '')}\n{cs.get('description', '')}\n"
        segments.append(cs_md)

    return "\n\n".join(segments)

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


    scraped_data = [res["content_text"] for res in scraped_result if res.get("status") == "success" and res.get("content_text")]
    compiled = compile_topic(topic_name, [topic_name], scraped_data=scraped_data)


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
        audio_url=audio_url,
        content_json=json.dumps(compiled)
    )

    print(f"✅ Created candidate: {candidate_id}")

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
        raise RuntimeError(f"No pending topics found for domain: {domain}")

    topic_id = topic["topic_node_id"]
    topic_name = topic["topic_name"]
    # Standardize requested domain name (Title Case, except APIs)
    if domain and domain.strip().upper() == 'APIS':
        std_domain = 'APIs'
    else:
        std_domain = domain.strip().title() if domain else "General"
    
    actual_domain = topic.get("domain", std_domain)
    # Fix actual_domain casing if it came from DB as 'Apis'
    if actual_domain.upper() == 'APIS':
        actual_domain = 'APIs'
    
    print(f"Starting generation for: {topic_name} (Requested: {std_domain}, Actual: {actual_domain})")


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


    scraped_data = [res["content_text"] for res in scraped_result if res.get("status") == "success" and res.get("content_text")]
    compiled = compile_topic(topic_name, [topic_name], scraped_data=scraped_data)


    compiled_id = save_compiled_topic(topic_id, compiled)

    # 6️⃣ Derive ARTICLE FIELDS
    title = f"{topic_name} "
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
        audio_url=audio_url,
        content_json=json.dumps(compiled)
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
        audio_url=audio_url,
        content_json=json.dumps(compiled)
    )
    set_article_audience(article_id, "subscriber")
    
    # 8️⃣ Link to domain ONLY if it's the correct match or an orphaned topic
    # This prevents contaminating unrelated domains on fallback.
    try:
        # Use actual_domain for the edge, but ensure requested domain exists too
        requested_node = insert_node(std_domain, "domain")
        
        # If the topic was picked specifically for this domain OR was orphaned/global fallback,
        # we check if we should actually link it. 
        # Crucial fix: Only link if we are sure it belongs here.
        if actual_domain.lower() == std_domain.lower():
            insert_or_increment_edge(requested_node[0], topic_id)
            print(f"🔗 Linked '{topic_name}' to domain '{std_domain}'")
        else:
            # Topic belongs to different domain (fallback), link it to ITS domain instead
            actual_node = insert_node(actual_domain, "domain")
            insert_or_increment_edge(actual_node[0], topic_id)
            print(f"🔗 Linked '{topic_name}' to its OWN domain '{actual_domain}' (Fallback occurred from '{std_domain}')")
    except Exception as e:
        print(f"⚠️ Graph linking failed: {e}")
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
