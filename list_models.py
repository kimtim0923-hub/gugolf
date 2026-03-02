
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def list_models():
    client = genai.Client(api_key=api_key)
    try:
        # Using a list directly if it's an iterable or through client.models.list()
        # In newer versions of the SDK, list() returns an iterator of Model objects.
        for m in client.models.list():
            print(f"Name: {m.name}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    list_models()
