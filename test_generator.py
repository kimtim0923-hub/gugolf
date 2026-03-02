
import os
from dotenv import load_dotenv
from image_prompt_generator import generate_image_prompts

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")

tournaments = [
    {"tour": "PGA Tour", "name": "Test Tournament", "location": "Test Location", "course": "Test Course"}
]
script = "안녕하세요. 오늘 골프 소식입니다. PGA 투어가 열립니다."

print("Starting test...")
try:
    segments = generate_image_prompts(script, tournaments, api_key)
    print(f"Success! Generated {len(segments)} segments.")
    for s in segments:
        print(f"ID {s['segment_id']}: {s['prompt'][:50]}...")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    print(traceback.format_exc())
