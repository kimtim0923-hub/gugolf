"""
골프 프리뷰 대본과 수집된 대회 정보를 기반으로 
이미지 생성용 프롬프트를 생성하는 모듈 (사용자 커스텀 프롬프트 반영)
"""
import json
import re
from typing import List
from google import genai
from google.genai import types

def generate_image_prompts(script: str, tournaments: List[dict], api_key: str) -> List[dict]:
    """
    사용자가 직접 작성한 지시문을 바탕으로 제미나이를 통해 프롬프트 생성
    """
    client = genai.Client(api_key=api_key)
    
    tour_context = ""
    for t in tournaments:
        if isinstance(t, dict) and t.get("name") and t.get("name") != "해당 없음":
            name = t.get('name', '미상')
            loc = t.get('location', '미상')
            course = t.get('course', '미상')
            tour_context += f"- {t['tour']}: {name} (장소: {loc}, 코스: {course})\n"

    # 사용자가 직접 작성한 내용을 시스템 프롬프트로 활용
    IMAGE_SYSTEM_PROMPT = """너는 골프 뉴스 영상 제작 유튜버야. 
골프 영상 배경에 들어갈 이미지를 제작할건데 글자수를 보고 10초 분량으로 잘라서 만들어줘.

## 출력형식:
- 반드시 아래 JSON 배열 형식으로만 응답해줘. (테이블 구조 생성을 위해 필수)
- 각 항목은 영문 이미지 프롬프트로 만들어줘.

## 핵심 요구사항:
1. **사실성 강화 (Fact-based Background)**:
   - 배경은 임의의 가상 공간이 아닌, 제공된 '대회 정보'와 '장소/코스'의 실제 특징을 반영해야 합니다.
   - 해당 경기장의 시그니처 홀이나 풍경, 실제 참가 선수의 특징을 상세히 묘사하세요.
2. **비주얼 스타일**: Ultra-realistic photo style, 8k resolution, cinematic lighting.

## JSON 출력 예시:
[
  {
    "segment_id": 1,
    "script": "구간 대본 내용...",
    "prompt": "Highly detailed English prompt...",
    "background_context": "[장소 특정] 실제 코스 특징 설명..."
  }
]"""

    user_message = f"제공된 정보를 바탕으로 이미지 생성 맵을 만드세요.\n\n[대본]\n{script}\n\n[대회 정보]\n{tour_context}"

    try:
        # 모델 명칭을 사용자 환경에서 성공적으로 테스트된 gemini-2.5-flash로 변경
        model_name = "gemini-2.5-flash"
        print(f"DEBUG: Calling Gemini [{model_name}] for Prompts...")
        
        response = client.models.generate_content(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=IMAGE_SYSTEM_PROMPT,
                response_mime_type="application/json"
            ),
            contents=user_message
        )
        
        full_text = response.text
        return json.loads(full_text)
            
    except Exception as e:
        import traceback
        print(f"DEBUG ERROR: {e}")
        print(traceback.format_exc())
        
        # 폴백 로직
        chunks = [script[i:i+60] for i in range(0, len(script), 60)]
        fallback_segments = []
        for i, chunk in enumerate(chunks):
            fallback_segments.append({
                "segment_id": i + 1,
                "script": chunk,
                "prompt": f"Ultra-realistic professional golf course photography, 8k resolution, cinematic lighting. Inspired by: '{chunk[:30]}...'",
                "background_context": "[알림] 시스템 최적화 중입니다. 잠시 후 다시 시도해 주세요."
            })
        return fallback_segments