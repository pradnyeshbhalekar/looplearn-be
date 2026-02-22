from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv

load_dotenv()

# The client automatically picks up GEMINI_API_KEY from the environment
client = genai.Client()

# Note: Ensure you have access to 2.5-flash, otherwise "gemini-2.0-flash" is the current standard.
MODEL_NAME = "gemini-2.5-flash" 

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
    # Keep the user prompt clean and focused strictly on the data
    prompt = f"Topic: {topic_name}\nExtracted concepts: {', '.join(concepts)}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        # Use types.GenerateContentConfig for type safety and clarity
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTIONS,
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        # It is helpful to print the raw text in the error to debug why it failed
        raise ValueError(f"Gemini returned invalid JSON: {response.text}") from e