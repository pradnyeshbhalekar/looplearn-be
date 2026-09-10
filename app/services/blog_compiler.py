from groq import Groq
import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

client = Groq()

MODEL_NAME = "openai/gpt-oss-120b"

# Groq's free/on-demand tier caps requests at 8,000 tokens/min — scraped
# sources are the biggest variable in the prompt, so they're hard-truncated
# to stay well under that regardless of how long the original article was.
MAX_SOURCE_CHARS = 600
MAX_SOURCES_PER_SUBTOPIC = 2

SYSTEM_INSTRUCTIONS = """
You are a technical writer compiling a deep-dive blog article for a learner
who gave you a TOPIC and their INTENT. You have already been given a gap
analysis (subtopics they asked for vs. subtopics they're missing) and
scraped source material for each subtopic.

### STRUCTURE REQUIREMENTS

- Write exactly ONE section per subtopic in "recommended_scope", in the
  exact same order. Do not add, drop, merge, or reorder subtopics.
- For each section, set "is_gap" to true if that subtopic came from the
  gap analysis's "gaps" list rather than "requested" — and when it is a
  gap, the section's content should explicitly call that out (e.g. "This
  wasn't part of what you asked for, but you'll need it because...")
  rather than silently folding it in as if the learner already expected it.
- Ground each section in the provided scraped sources where available for
  that subtopic. If no sources were found for a subtopic, write from
  general knowledge but keep it accurate and say less rather than
  fabricate specifics.

### MERMAID DIAGRAMS

- Only include a diagram on a section where it genuinely clarifies a flow,
  architecture, or relationship — most sections should have "mermaid": null.
- Use `graph TD` for flowcharts or `sequenceDiagram` for interactions.
- Labels: ABSOLUTELY NO `(`, `)`, `[`, `]`, `{`, `}`, `"`, or `'` inside a
  label. BAD: `A["Load (Slow)"]`. GOOD: `A["Load Slow"]`.
- Always wrap labels in double quotes: `nodeID["Label Text"]`.
- Node IDs: simple alphanumeric (A, B, Node1).
- NO markdown code fences (no ```mermaid) inside the "code" string — raw
  Mermaid syntax only.
- Every node used in a connection must be defined earlier in the diagram.

### TONE
Clear, direct, written to the learner's stated level — not marketing copy,
not an exhaustive reference manual. Keep each section's "content" to
roughly 150-250 words — concise sections, not an exhaustive reference.

RETURN STRICT JSON ONLY, matching this exact shape:

{
  "title": "",
  "intro": "",
  "sections": [
    {
      "subtopic": "",
      "is_gap": false,
      "content": "",
      "mermaid": null
    }
  ]
}

When a section does include a diagram, "mermaid" must be
{"diagram_type": "graph", "code": "graph TD\\n  A[\\"Step One\\"] --> B[\\"Step Two\\"]"}
instead of null.
"""


def _format_sources_block(recommended_scope: list[str], sources: list[dict]) -> str:
    by_subtopic = {subtopic: [] for subtopic in recommended_scope}
    for source in sources:
        subtopic = source.get("subtopic")
        if subtopic in by_subtopic:
            by_subtopic[subtopic].append(source)

    lines = []
    for subtopic in recommended_scope:
        subtopic_sources = by_subtopic[subtopic]
        if not subtopic_sources:
            lines.append(f"### {subtopic}\n(no scraped sources found for this subtopic)")
            continue

        lines.append(f"### {subtopic}")
        for i, source in enumerate(subtopic_sources[:MAX_SOURCES_PER_SUBTOPIC]):
            text = (source.get("text") or "")[:MAX_SOURCE_CHARS]
            lines.append(f"--- Source {i+1} ({source.get('url')}) ---\n{text}")

    return "\n\n".join(lines)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=5, max=60), reraise=True)
def compile_blog(topic: str, intent: str, gap_analysis: dict, sources: list[dict]) -> dict:
    recommended_scope = gap_analysis["recommended_scope"]
    gaps = set(gap_analysis.get("gaps", []))

    prompt = (
        f"Topic: {topic}\n"
        f"Learner intent: {intent}\n\n"
        f"Requested subtopics: {', '.join(gap_analysis.get('requested', []))}\n"
        f"Gap subtopics: {', '.join(gap_analysis.get('gaps', []))}\n"
        f"Recommended scope (write sections in this exact order): "
        f"{', '.join(recommended_scope)}\n\n"
        f"Scraped source material:\n\n{_format_sources_block(recommended_scope, sources)}"
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.4
    )

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Groq returned invalid JSON: {raw}") from e

    sections = result.get("sections")
    if not isinstance(sections, list) or len(sections) != len(recommended_scope):
        raise ValueError(
            f"Expected {len(recommended_scope)} sections, got "
            f"{len(sections) if isinstance(sections, list) else 'invalid'}: {raw}"
        )

    for expected_subtopic, section in zip(recommended_scope, sections):
        if section.get("subtopic") != expected_subtopic:
            raise ValueError(
                f"Section order/naming mismatch: expected '{expected_subtopic}', "
                f"got '{section.get('subtopic')}': {raw}"
            )
        section["is_gap"] = expected_subtopic in gaps

    return result
