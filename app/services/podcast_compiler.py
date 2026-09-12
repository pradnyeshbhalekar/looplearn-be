import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.groq_client import get_groq_client

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"

# Groq's free/on-demand tier caps requests at 8,000 tokens/min. The podcast
# prompt is the heaviest of the three Loop in calls (sources + blog summary
# both feed it), so both are hard-truncated here — full text isn't needed,
# just enough to ground the conversation and know what angles to avoid.
MAX_SOURCE_CHARS = 400
MAX_SOURCES_TOTAL = 4
MAX_SECTION_SUMMARY_CHARS = 150

HOST_A_NAME = "Maya"
HOST_B_NAME = "Leo"

SYSTEM_INSTRUCTIONS = f"""
You are writing a two-host podcast script for a learner who gave you a TOPIC
and their INTENT. You've already been given a gap analysis (subtopics they
asked for vs. subtopics they're missing), scraped source material, and the
BLOG ARTICLE already written from the same research.

### THE TWO HOSTS
- HOST_A, whose name is {HOST_A_NAME}: the more curious one on average, but
  NOT purely an interviewer — has their own half-formed opinions, makes
  guesses (some wrong), occasionally explains something themselves, and
  sometimes asks HOST_B a question back.
- HOST_B, whose name is {HOST_B_NAME}: the more knowledgeable one on
  average, but NOT infallible or a lecture machine — sometimes unsure,
  sometimes asks HOST_A what they think first, sometimes gets corrected or
  contradicted by HOST_A, and occasionally goes on a short tangent before
  circling back.

Both hosts explain things and both hosts ask things. Neither host has a
fixed role in every exchange. Refer to each other by name occasionally
("Yeah, {HOST_B_NAME}, but..." / "Wait, {HOST_A_NAME}, hang on—") like real
co-hosts do, not just "you."

### OPENING — DO NOT SKIP THIS
The first 3-5 lines are a real podcast cold-open, not a jump straight into
content:
1. {HOST_A_NAME} welcomes listeners back and names today's topic in one
   casual line (not a formal announcement).
2. {HOST_A_NAME} introduces {HOST_B_NAME} — with a little personality or a
   light joke/tease, like real co-hosts who know each other, not a formal
   "and here's my co-host."
3. {HOST_B_NAME} responds in kind (a joke back, a quip, or just an
   easygoing "hey everyone") before the conversation eases into the topic.
Do NOT start the transcript on the first line of actual technical content.

### KEEP IT LIGHT IN PLACES
Sprinkle 2-4 small moments of humor or banter across the whole
conversation (not just the opening) — a wisecrack about the topic, gentle
ribbing between the hosts, a self-deprecating aside about getting
something wrong before. It should feel like two people who like each
other, not two people reciting a syllabus at each other.

### AVOID THE INTERVIEW PATTERN — THIS IS THE MOST IMPORTANT RULE
The single most common failure mode for this format is turning into a
question-then-answer-then-question-then-answer pattern, like one host is
interviewing or quizzing the other. THAT IS NOT A CONVERSATION.

Hard numeric constraints (check these before returning your answer):
- At most 40% of all lines may end in a question mark. If you notice most
  HOST_A lines end in "?", you have failed this constraint — go back and
  turn several of those into statements, reactions, or half-finished
  thoughts instead.
- No more than 2 consecutive lines from the same host may end in a
  question mark.
- At least 3 lines total must be under 6 words (a short reaction, not an
  explanation).

Here is a short EXAMPLE of the target style, on a totally unrelated topic
(why standup meetings run long) — copy the STYLE, not the content:

  HOST_A: Okay so today I want to talk about why standup always runs over.
  HOST_B: Oh my god, don't get me started, we did forty minutes yesterday.
  HOST_A: Forty? See, that's the thing, it's supposed to be a status check,
    not a design review.
  HOST_B: Right, but then someone hits a blocker and suddenly it's a whole
    debugging session in front of six people.
  HOST_A: Which, honestly, half the room doesn't even need to be there for.
  HOST_B: Yeah — actually this happened to me at my last job, we ended up
    splitting standup into two rooms just to fix it.
  HOST_A: Wait, did that actually work?
  HOST_B: Kind of. People just started blocker-hopping between both rooms.
  HOST_A: Of course they did.

Notice: most lines are statements or reactions, not questions. Turn lengths
vary a lot. HOST_B volunteers an anecdote unprompted. HOST_A reacts with a
short line ("Of course they did.") instead of asking something new. Only
one line in the whole example is a genuine question. Your dialogue on the
real topic must read like this, not like an interview.

### STRUCTURE
- Cover every subtopic in "recommended_scope", but reach each one through
  natural conversational flow — do not announce subtopics like a checklist
  ("Next, let's talk about X"). A subtopic can come up because someone
  asks about it, because it naturally follows from the previous point,
  because someone brings it up mid-tangent, or because someone states an
  assumption about it that turns out to be wrong.
- Include at least one moment of genuine disagreement, correction, or
  tangent between the hosts — this is a real conversation, not two people
  taking turns reciting facts.
- After the dialogue, list every subtopic from "recommended_scope" that
  the conversation actually touched on, in "subtopics_covered" — every
  entry from "recommended_scope" must appear here exactly once.

### DEPTH — THE LISTENER SHOULD ACTUALLY LEARN SOMETHING
This is not a highlight reel. For each subtopic, actually explain the
mechanism or the "why", with a concrete detail or example — not just a
one-line definition before moving on. It's fine, even good, to spend
several exchanges lingering on a subtopic that deserves it (a tricky
mechanism, something counterintuitive, something the learner's intent
specifically cares about) rather than rushing through every subtopic at
the same shallow depth just to cover them all quickly. Depth on the
subtopics that matter beats even, shallow coverage of all of them.

### TONE
Informal, spoken language — contractions, interruptions, "yeah" / "right" /
"okay so" type filler where natural. Not a script that reads like an essay
read aloud. Turn count isn't fixed — let the depth and the opening/banter
requirements above determine the real length; a well-explained episode
will likely run longer than 30 turns, and that's fine. Turn lengths should
stay genuinely uneven (some 3 words, some 3+ sentences) throughout, not
just in the opening.

RETURN STRICT JSON ONLY, matching this exact shape:

{{
  "title": "",
  "dialogue": [
    {{"host": "HOST_A", "text": ""}},
    {{"host": "HOST_B", "text": ""}}
  ],
  "subtopics_covered": ["subtopic", "..."]
}}

"host" must always be exactly "HOST_A" or "HOST_B" (not the character's
name — the name is only spoken in "text", the "host" field stays as the
role id so the audio pipeline can map it to a voice).
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

    response = get_groq_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=4096
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

    # Enforced backstop for the "interview pattern" — the prompt asks for
    # this, but LLMs default back to Q&A easily, so check it in code and
    # force a retry (new sample at temperature=0.7) rather than trust it.
    question_lines = sum(1 for line in dialogue if line.get("text", "").rstrip().endswith("?"))
    question_ratio = question_lines / len(dialogue)
    if question_ratio > 0.5:
        raise ValueError(
            f"Podcast script reads like an interview: {question_ratio:.0%} "
            f"of lines end in a question mark: {raw}"
        )

    return result
