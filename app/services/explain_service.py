import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def fetch_explanation(highlighted_text,context):
    system_prompt = """
        You are an expert technical tutor. Explain the highlighted text strictly based on the sorrounding paragraph involved.
        Limit your response to a maximum of 3 sentences.
        Use plain, accessible language.
        Do not provide a generic dictionary definiation.
        Output a raw text only.
        No markdown,bolding or bullet points.    
        """
    
    user_prompt = f"Context Paragraph: {context}\n\n Highlighted Term to Explain:`{highlighted_text}`"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type":"application/json"
    }

    payload = {
        "model":"gpt-4o-mini",
        "messages":[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}
        ],
        "temperature":0.2
    }

    try:
        response = requests.post(
            "https://models.inference.ai.azure.com/chat/completions", 
            json=payload, 
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
        
    except requests.exceptions.RequestException as e:
        print(f"LLM API Error: {e}")
        raise Exception("Failed to generate explanation.")