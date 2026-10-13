
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api():
    api_key = os.getenv("XAI_API_KEY")
    # Base URL depends on the key prefix
    if api_key and api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model = "llama-3.3-70b-versatile"
        provider = "Groq"
    else:
        base_url = os.getenv("BASE_URL", "https://api.x.ai/v1")
        model = "grok-beta"
        provider = "Grok (xAI)"

    print(f"--- API TEST START ---")
    print(f"Provider: {provider}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"API Key (first 8): {api_key[:8] if api_key else 'None'}")
    
    if not api_key:
        print("Error: No API key found in .env")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Translate the Sanskrit word 'नमस्ते' to English and tell me its Part of Speech."}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("\n[SUCCESS] API WORKING SUCCESSFULLY!")
            print("Response:", content)
        else:
            print(f"\n[ERROR] API ERROR: Status {response.status_code}")
            print("Message:", response.text)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {str(e)}")

if __name__ == "__main__":
    test_api()
