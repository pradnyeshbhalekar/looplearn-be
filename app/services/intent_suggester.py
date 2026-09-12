from groq import Groq
import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.gap_analyzer import MAX_TOPIC_LENGTH, GapAnalysisInputError

load_dotenv()

client = Groq()

MODEL_NAME = "openai/gpt-oss-120b"

SYSTEM_INSTRUCTIONS = """
You help a learner who has typed in a TOPIC but is stuck on stating their
INTENT — what they specifically want out of it, their current level, and
their goal. That intent is used downstream to scope a personalized
research pipeline, so each suggestion must read like something the learner
themselves would type: first person, concrete, one or two sentences.

Propose 4 distinct intents for the given topic, each covering a different
angle a learner might actually have, for example (adapt to the topic,
don't force these labels):
- a complete beginner wanting a plain-language overview
- someone wanting a practical, hands-on/how-to understanding
- someone wanting a deep technical/advanced understanding
- someone wanting to compare it against alternatives or evaluate a decision

RETURN STRICT JSON ONLY, matching this exact shape:

{
  "suggestions": [
    {"label": "short label, a few words", "intent": "first-person intent sentence(s)"},
    "... exactly 4 items"
  ]
}
"""


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=5, max=60), reraise=True)
def suggest_intents(topic: str) -> dict:
    topic = (topic or "").strip()

    if not topic:
        raise GapAnalysisInputError("topic is required")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise GapAnalysisInputError(f"topic must be {MAX_TOPIC_LENGTH} characters or fewer")

    prompt = f"Topic: {topic}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Groq returned invalid JSON: {raw}") from e

    if "suggestions" not in result or not isinstance(result["suggestions"], list):
        raise ValueError(f"Groq response missing/invalid 'suggestions': {raw}")

    for item in result["suggestions"]:
        if not isinstance(item, dict) or "label" not in item or "intent" not in item:
            raise ValueError(f"Groq response has malformed suggestion item: {raw}")

    return result
