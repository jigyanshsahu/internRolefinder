import os
import json
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY", "")

prompt = """
Output exactly 500 prominent tech startups from India. 
Include startups in Fintech, SaaS, E-commerce, EdTech, HealthTech, AI, Logistics, etc.
Output ONLY a raw JSON array of strings. Do not include any markdown formatting, backticks, or extra text. Just the JSON array starting with '[' and ending with ']'.
"""

def generate_startups():
    # Let's try gemini-1.5-pro or gemini-1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = httpx.post(url, json=payload, timeout=120.0)
    data = response.json()
    
    if 'candidates' not in data:
        print("API Error:", data)
        return
        
    text = data['candidates'][0]['content']['parts'][0]['text']
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    try:
        startups = json.loads(text.strip())
        print(f"Generated {len(startups)} startups.")
        
        with open("/app/startups_500.json", "w") as f:
            json.dump(startups, f, indent=2)
    except Exception as e:
        print("JSON Decode Error:", e)
        print(text[:200])

if __name__ == "__main__":
    generate_startups()
