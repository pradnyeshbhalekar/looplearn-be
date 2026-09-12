import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.groq_client import get_groq_client

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"

MAX_TOPIC_LENGTH = 200
MAX_INTENT_LENGTH = 1000

SYSTEM_INSTRUCTIONS = """
You are a curriculum designer performing a gap analysis for a learner.

The learner gives you a TOPIC and their INTENT (what they specifically want
out of it, their current level, and their goal). Your job is to figure out:

1. What subtopics their intent ALREADY implies they want covered
   ("requested").
2. What subtopics are MISSING that a genuinely working understanding of the
   topic requires, given their stated level and goal, that they did not
   mention ("gaps"). Do not pad this list — only include a gap if skipping it
   would leave a real hole in their understanding for their stated goal.
3. The full ORDERED list of subtopics to actually research and write about,
   combining "requested" and "gaps" into a single sensible learning order
   ("recommended_scope"). Every entry in "requested" and "gaps" must appear
   in "recommended_scope" exactly once, and "recommended_scope" must not
   contain anything that isn't in one of those two lists.

Keep each subtopic short (a few words, like a section heading), not a full
sentence. Aim for 3-8 total subtopics in "recommended_scope" — enough to be
useful, not so many that the output turns into an exhaustive syllabus.

RETURN STRICT JSON ONLY, matching this exact shape:

{
  "requested": ["subtopic", "..."],
  "gaps": ["subtopic", "..."],
  "recommended_scope": ["subtopic", "..."]
}
"""


class GapAnalysisInputError(ValueError):
    pass


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=5, max=60), reraise=True)
def analyze_gaps(topic: str, intent: str) -> dict:
    topic = (topic or "").strip()
    intent = (intent or "").strip()

    if not topic:
        raise GapAnalysisInputError("topic is required")
    if not intent:
        raise GapAnalysisInputError("intent is required")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise GapAnalysisInputError(f"topic must be {MAX_TOPIC_LENGTH} characters or fewer")
    if len(intent) > MAX_INTENT_LENGTH:
        raise GapAnalysisInputError(f"intent must be {MAX_INTENT_LENGTH} characters or fewer")

    prompt = f"Topic: {topic}\nLearner intent: {intent}"

    response = get_groq_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Groq returned invalid JSON: {raw}") from e

    for key in ("requested", "gaps", "recommended_scope"):
        if key not in result or not isinstance(result[key], list):
            raise ValueError(f"Groq response missing/invalid '{key}': {raw}")

    return result
