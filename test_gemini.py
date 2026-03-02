
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def test_gemini():
    client = genai.Client(api_key=api_key)
    try:
        # gemini-2.5-flash 시도
        model_name = "gemini-2.5-flash"
        print(f"Testing Gemini [{model_name}]...")
        response = client.models.generate_content(
            model=model_name,
            contents="Say hello in JSON",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        print("Success:", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_gemini()
