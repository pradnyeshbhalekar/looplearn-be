import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.topic_compiler import compile_topic
from unittest.mock import MagicMock, patch

def test_compilation_with_scraped_data():
    topic_name = "Consistent Hashing"
    concepts = ["Hash Ring", "Virtual Nodes", "Data Distribution"]
    scraped_data = [
        "Consistent hashing is a technique used in distributed systems to distribute data across multiple nodes.",
        "It minimizes the number of keys that need to be remapped when nodes are added or removed.",
        "A hash ring is used to represent the set of nodes and data."
    ]

    print(f"Testing compilation for topic: {topic_name} with scraped data...")
    
    # We won't actually call Gemini to avoid costs/API dependency in unit test, 
    # but we can verify the function signature and prompt construction if we were to mock it properly.
    # However, for a real verification, I'll do a dry run of the prompt construction logic.
    
    with patch('app.services.topic_compiler.client') as mock_client:
        mock_instance = mock_client
        mock_instance.models.generate_content.return_value = MagicMock(text=json.dumps({
            "topic": topic_name,
            "intro_hook": "Ever wonder how databases scale?",
            "what_is_it": "A distributed hashing scheme.",
            "why_is_it_important": "Scaling.",
            "what_if_it_wasnt_there": "Chaos.",
            "theory": {"overview": "Ring", "key_principles": [], "tradeoffs": []},
            "topic_schema": {},
            "case_study": {"system": "Dynamo", "description": "Used it.", "key_takeaways": []},
            "mermaid": {"diagram_type": "graph", "code": "graph TD; A-->B;"},
            "interview_notes": {"common_questions": [], "common_mistakes": [], "what_interviewers_look_for": []},
            "child_topics": []
        }))

        result = compile_topic(topic_name, concepts, scraped_data=scraped_data)
        
        print("✅ Compilation call successful!")
        print("Result keys:", result.keys())
        
        # Verify prompt construction (internal check)
        call_args = mock_instance.models.generate_content.call_args
        # generate_content is called with config=... and contents=...
        # contents is a keyword argument or positional argument?
        # In topic_compiler.py: response = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=...)
        prompt = call_args[1]['contents']
        
        assert "Related Scraped Content:" in prompt
        assert "--- Source 1 ---" in prompt
        assert scraped_data[0] in prompt
        print("✅ Prompt construction verified!")

if __name__ == "__main__":
    try:
        test_compilation_with_scraped_data()
        print("\nVerification Passed!")
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        sys.exit(1)
