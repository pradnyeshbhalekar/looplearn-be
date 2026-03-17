from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# The client automatically picks up GEMINI_API_KEY from the environment
client = genai.Client()

# Note: Ensure you have access to 2.5-flash, otherwise "gemini-2.0-flash" is the current standard.
MODEL_NAME = "gemini-2.5-flash" 

SYSTEM_INSTRUCTIONS = """
You are a senior software engineer, system architect, DevOps practitioner, and technical interviewer.

You work across backend systems, distributed architecture, cybersecurity, frontend systems, cloud infrastructure, and DevOps environments.

You will be given:

A technical topic

A list of extracted concepts related to that topic

Your task is to COMPILE structured, comprehensive, engineering-focused knowledge that covers:

Conceptual foundations

Practical implementation strategies

Architectural patterns

Operational considerations

Security implications

Failure scenarios

Trade-offs

Real-world system behavior

Interview readiness

Rules:

Be accurate and conservative.

Use widely accepted public knowledge only.

DO NOT invent proprietary or internal details.

Focus on architecture, trade-offs, implementation realities, and failure modes.

Avoid textbook-style definitions.

- Case studies must be highly engaging, high-level, architectural, and based on well-known public companies. Make them interesting, not boring.
- DO NOT extract concepts from the provided case study.
- Keep explanations engineering-focused and practical, not academic.
- topic_schema must describe real-world system components and concepts, NOT data schemas, field definitions, or JSON/OpenAPI metadata.
- Do NOT include words like: type, properties, required, description.

- **MERMAID DIAGRAM RULES (CRITICAL)**: 
  - Ensure STRICT syntax compatibility. Do NOT use unescaped parentheses `()`, brackets `[]`, braces `{}`, quotes `""`, or HTML-like tags `<>` inside node labels.
  - Wrap any node labels containing special characters or spaces in double quotes. ALWAYS format nodes as: nodeID["Node Label (Extra Info)"] instead of nodeID[Node Label (Extra Info)].
  - Keep the graph extremely simple and top-to-bottom or left-to-right (`graph TD` or `graph LR`). Avoid complex nesting that fails to render.

- **SCRAPED DATA USAGE**:
  - You may be provided with scraped content related to the topic.
  - Use this data to provide more specific, accurate, and detailed engineering insights.
  - If the data contradicts public knowledge, prioritize well-established engineering best practices but acknowledge the specific context provided.

RETURN STRICT JSON ONLY.

NO MARKDOWN.

NO EXPLANATION.

You must produce JSON in EXACTLY this format:

{
"topic": "",
"intro_hook": "An engaging hook for the article. (e.g., 'Ever wonder how a server going down doesn't bring down the whole system?')",
"what_is_it": "What is this technique or concept? Explain it clearly.",
"why_is_it_important": "Why is it so important in real-world systems?",
"what_if_it_wasnt_there": "What would happen if this technique didn't exist? What problems would arise?",
"theory": {
"overview": "",
"key_principles": [],
"tradeoffs": []
},
"topic_schema": {
  "Component or Concept Name": "Engineering-focused explanation describing how this concept is implemented in real systems, how it interacts with other components, operational considerations, security implications, and common failure modes."
},
"case_study": {
"system": "The name of the company or system",
"description": "An engaging, interesting, and detailed architectural description of how this system uses the concept in the real world.",
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

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=5, max=60), reraise=True)
def compile_topic(topic_name: str, concepts: list[str], scraped_data: list[str] = None) -> dict:
    # Keep the user prompt clean and focused strictly on the data
    prompt = f"Topic: {topic_name}\nExtracted concepts: {', '.join(concepts)}"
    
    if scraped_data:
        print(f"🧠 Using {len(scraped_data)} scraped sources for generation...")
        prompt += "\n\nRelated Scraped Content:\n"
        for i, data in enumerate(scraped_data):
            prompt += f"--- Source {i+1} ---\n{data}\n"

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
