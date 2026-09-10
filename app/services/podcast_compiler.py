from groq import Groq
import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

client = Groq()

MODEL_NAME = "openai/gpt-oss-120b"

# Groq's free/on-demand tier caps requests at 8,000 tokens/min. The podcast
# prompt is the heaviest of the three Loop in calls (sources + blog summary
# both feed it), so both are hard-truncated here — full text isn't needed,
# just enough to ground the conversation and know what angles to avoid.
MAX_SOURCE_CHARS = 400
MAX_SOURCES_TOTAL = 4
MAX_SECTION_SUMMARY_CHARS = 150

SYSTEM_INSTRUCTIONS = """
You are writing a two-host podcast script for a learner who gave you a TOPIC
and their INTENT. You've already been given a gap analysis (subtopics they
asked for vs. subtopics they're missing), scraped source material, and the
BLOG ARTICLE already written from the same research.

### THE TWO HOSTS
- HOST_A: curious, asks questions, occasionally pushes back or admits
  confusion. Represents the learner's perspective.
- HOST_B: explains things informally, like a knowledgeable friend, not a
  lecturer. Not infallible — can be corrected or contradicted by HOST_A.

### DO NOT NARRATE THE BLOG
You're given a short summary of each blog section (not the full article) so
you can AVOID repeating its angle, not so you can expand on it. Use
different analogies, different examples, and a different path through the
material than the blog took.

### STRUCTURE
- Cover every subtopic in "recommended_scope", but reach each one through
  natural conversational flow — do not announce subtopics like a checklist
  ("Next, let's talk about X"). A subtopic can come up because HOST_A asks
  about it, because it naturally follows from the previous point, or
  because HOST_B brings it up while explaining something else.
- Include at least one moment of genuine disagreement, correction, or
  tangent between the hosts — this is a real conversation, not two people
  taking turns reciting facts.
- After the dialogue, list every subtopic from "recommended_scope" that
  the conversation actually touched on, in "subtopics_covered" — every
  entry from "recommended_scope" must appear here exactly once.

### TONE
Informal, spoken language — contractions, interruptions, "yeah" / "right" /
"okay so" type filler where natural. Not a script that reads like an essay
read aloud. Aim for roughly 20-30 dialogue turns total, each turn 1-3
sentences — a tight conversation, not a marathon transcript.

RETURN STRICT JSON ONLY, matching this exact shape:

{
  "title": "",
  "dialogue": [
    {"host": "HOST_A", "text": ""},
    {"host": "HOST_B", "text": ""}
  ],
  "subtopics_covered": ["subtopic", "..."]
}

"host" must always be exactly "HOST_A" or "HOST_B".
"""


def _format_blog_summary(blog: dict) -> str:
    lines = [f"Blog title: {blog.get('title', '')}"]
    for section in blog.get("sections", []):
        summary = (section.get("content") or "")[:MAX_SECTION_SUMMARY_CHARS]
        lines.append(f"- {section.get('subtopic')}: {summary}...")
    return "\n".join(lines)


def _format_sources_block(sources: list[dict]) -> str:
    if not sources:
        return "(no scraped sources)"
    return "\n\n".join(
        f"--- {source.get('subtopic')} ({source.get('url')}) ---\n{(source.get('text') or '')[:MAX_SOURCE_CHARS]}"
        for source in sources[:MAX_SOURCES_TOTAL]
    )


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=5, max=60), reraise=True)
def compile_podcast(topic: str, intent: str, gap_analysis: dict, sources: list[dict], blog: dict) -> dict:
    recommended_scope = gap_analysis["recommended_scope"]

    prompt = (
        f"Topic: {topic}\n"
        f"Learner intent: {intent}\n\n"
        f"Recommended scope (must all be covered, any order): "
        f"{', '.join(recommended_scope)}\n\n"
        f"Scraped source material:\n\n{_format_sources_block(sources)}\n\n"
        f"Blog article already written from this research (avoid repeating "
        f"its structure/analogies/examples):\n\n{_format_blog_summary(blog)}"
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Groq returned invalid JSON: {raw}") from e

    dialogue = result.get("dialogue")
    if not isinstance(dialogue, list) or not dialogue:
        raise ValueError(f"Podcast script has no dialogue: {raw}")

    for line in dialogue:
        if line.get("host") not in ("HOST_A", "HOST_B"):
            raise ValueError(f"Invalid host in dialogue line: {line}")

    covered = set(result.get("subtopics_covered") or [])
    missing = set(recommended_scope) - covered
    if missing:
        raise ValueError(f"Podcast script missing subtopics {missing}: {raw}")

    return result
