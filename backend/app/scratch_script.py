import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path="/app/.env")

API_KEY = os.environ.get("GEMINI_API_KEY")

prompt = """
Please provide a comprehensive list of exactly 500 prominent and emerging tech startups from India. 
Include unicorns, soonicorns, and well-known tech product companies in Fintech, SaaS, E-commerce, EdTech, HealthTech, AI, Logistics, etc.
Output ONLY a raw JSON array of strings containing the names of the startups. Do not include any markdown formatting, backticks, or extra text. Just the JSON array starting with '[' and ending with ']'.
Example: ["Flipkart", "Zomato", "Swiggy"]
"""

def generate_startups():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = httpx.post(url, json=payload, timeout=120.0)
    data = response.json()
    if 'candidates' not in data:
        print("Error from API:", data)
        return
        
    text = data['candidates'][0]['content']['parts'][0]['text']
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    startups = json.loads(text.strip())
    print(f"Generated {len(startups)} startups.")
    
    with open("/app/startups_500.json", "w") as f:
        json.dump(startups, f, indent=2)

if __name__ == "__main__":
    generate_startups()
