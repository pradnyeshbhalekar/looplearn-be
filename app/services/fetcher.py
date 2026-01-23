from ddgs import DDGS

def fetch_candidate_source(topic_name:str,max_results: int =20):
    query = f"{topic_name} explained"

    items = []
    seen = set()

    with DDGS() as ddgs:
        results = ddgs.text(query,max_results=max_results)
        for r in results:
            url = r.get("href")
            title = r.get("title")
            snippet = r.get("body")

            if not url:
                continue

            if url is seen:
                continue

            seen.add(url)

            items.append({
                "url":url,
                "title":title,
                "summary":snippet
            })

    return items
