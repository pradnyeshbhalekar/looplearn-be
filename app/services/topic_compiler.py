from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()


client = genai.Client()


MODEL_NAME = "gemini-2.5-flash" 

SYSTEM_INSTRUCTIONS = """
You are a senior software engineer, system architect, and technical educator.
Your task is to COMPILE structured, engineering-focused knowledge for a given topic.

### SCHEMA REQUIREMENTS:

1. **Practical Implementation (The "Show Me" Artifact)**:
   - Provide a concrete, real-world artifact (Code snippet, Config YAML, CLI commands, or SQL query).
   - Engineers trust what they can see. Avoid generic "Hello World".
   - Include a `line_by_line_breakdown` explaining the technical rationale for specific lines.

2. **Flashcards (Interview Readiness)**:
   - Format: `{"question": "...", "answer": "..."}`.
   - Design for active recall. Direct, punchy Question/Answer pairs.

3. **Observability & Anti-Patterns**:
   - `observability_metrics`: Key indicators (Latencies, Error rates, Throughput) to monitor this topic in production.
   - `anti_patterns`: Common mistakes engineers make and their consequences.

4. **Mermaid Diagrams**:
   - Use `graph TD` for flowcharts or `sequenceDiagram` for interactions.
   - Labels: **ABSOLUTELY NO** `(`, `)`, `[`, `]`, `{`, `}`, `\"`, or `'` inside a label.
   - **BAD**: `A[\"Load (Slow)\"]` or `B[\"User's Action\"]`.
   - **GOOD**: `A[\"Load Slow\"]` or `B[\"User Action\"]`.
   - Formatting: **ALWAYS** wrap labels in double quotes. Example: `nodeID[\"Label Text\"]`.
   - Node IDs: Use simple alphanumeric IDs (e.g., `A`, `B`, Node1).
   - Connections: Use `-->` for flow and `-- \"text\" -->` for labeled arrows.
   - NO markdown code blocks (e.g., ```mermaid) inside the \"code\" string. Just the raw Mermaid syntax.
   - Ensure all nodes used in connections are defined earlier in the diagram.

### RULES:
- **Case Studies**: Must be highly engaging, high-level, and based on well-known public companies (Netflix, Uber, Discord, etc.).
- **Scraped Data**: Use provided scraped content to enrich the artifact with real-world implementation nuances.
- **Tone**: Professional, engineering-focused, and practical.

RETURN STRICT JSON ONLY.

{
"topic": "",
"intro_hook": "",
"what_is_it": "",
"why_is_it_important": "",
"practical_implementation": {
  "artifact_type": "Code | Config | CLI | SQL",
  "language": "e.g. typescript, yaml, bash",
  "code": "",
  "line_by_line_breakdown": [
    {"line": "", "explanation": ""}
  ]
},
"theory": {
  "overview": "",
  "key_principles": [],
  "tradeoffs": [
    {
      "strategy": "e.g. Client-side Load Balancing",
      "pros": ["pro 1", "pro 2"],
      "cons": ["con 1", "con 2"]
    }
  ]
},
"observability_metrics": [
  {"metric": "", "importance": ""}
],
"anti_patterns": [
  {"pattern": "", "why_it_happens": "", "consequence": ""}
],
"case_study": {
  "system": "",
  "description": "",
  "key_takeaways": []
},
"flashcards": [
  {"question": "", "answer": ""}
],
"mermaid": {
  "diagram_type": "graph",
  "code": "graph TD\n  A[\"Load Balancer\"] --> B[\"API Cluster\"]\n  B -- \"Read Query\" --> C[\"Database Read Replica\"]"
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
