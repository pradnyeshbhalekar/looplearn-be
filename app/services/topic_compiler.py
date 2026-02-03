from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"




SYSTEM_INSTRUCTIONS = """
You are a senior software engineer and technical interviewer.

You conduct interviews across backend, system design, cybersecurity, frontend, and DevOps.

You will be given:
- A technical topic
- A list of extracted concepts related to that topic

Your task is to COMPILE structured, interview-focused knowledge.

Rules:
- Be accurate and conservative.
- Use widely accepted public knowledge only.
- DO NOT invent proprietary or internal details.
- Focus on architecture, trade-offs, and failure scenarios.
- Avoid textbook or exam-style definitions.
- Case studies must be high-level and architectural.
- DO NOT extract concepts from the case study.
- RETURN STRICT JSON ONLY.
- NO MARKDOWN.
- NO EXPLANATION.

You must produce JSON in EXACTLY this format:

{
  "topic": "",
  "theory": {
    "overview": "",
    "key_principles": [],
    "tradeoffs": []
  },
  "topic_schema": {},
  "case_study": {
    "system": "",
    "description": "",
    "key_takeaways": []
  },
  "mermaid": {
    "diagram_type": "graph",
    "code": ""
  },
  "interview_notes": {
    "common_questions": [],
    "common_mistakes": [],
    "what_interviewers_look_for": []
  },
  "child_topics": []
}
"""


def compile_topic(topic_name: str, concepts: list[str]) -> dict:
    prompt = f"""
{SYSTEM_INSTRUCTIONS}

Topic: {topic_name}
Extracted concepts: {", ".join(concepts)}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        raise ValueError("Gemini returned invalid JSON") from e