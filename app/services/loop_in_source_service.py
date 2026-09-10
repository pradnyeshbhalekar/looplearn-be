from app.services.fetcher import fetch_candidate_source
from app.services.scraper import scrape_article

MAX_SOURCES = 6
CANDIDATES_PER_SUBTOPIC = 5
MAX_SCRAPE_ATTEMPTS = 20


def gather_sources(recommended_scope: list[str]) -> list[dict]:

    if not recommended_scope:
        return []

    candidate_queues = {
        subtopic: fetch_candidate_source(subtopic, max_results=CANDIDATES_PER_SUBTOPIC)
        for subtopic in recommended_scope
    }

    sources = []
    seen_urls = set()
    attempts = 0
    round_idx = 0

    while len(sources) < MAX_SOURCES and attempts < MAX_SCRAPE_ATTEMPTS:
        made_progress_this_round = False

        for subtopic in recommended_scope:
            if len(sources) >= MAX_SOURCES or attempts >= MAX_SCRAPE_ATTEMPTS:
                break

            queue = candidate_queues.get(subtopic, [])
            if round_idx >= len(queue):
                continue

            made_progress_this_round = True
            candidate = queue[round_idx]
            url = candidate.get("url")

            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            attempts += 1
            result = scrape_article(url)

            if result.get("ok") and result.get("text"):
                sources.append({
                    "subtopic": subtopic,
                    "url": url,
                    "title": candidate.get("title"),
                    "text": result["text"]
                })

        if not made_progress_this_round:
            break
        round_idx += 1

    return sources
