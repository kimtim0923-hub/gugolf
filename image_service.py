"""
Nano Banana (Gemini 3.1 Flash Image)를 이용한 실제 이미지 생성 모듈
최신 google-genai SDK 사용
"""
import os
import io
import time
from typing import List, Dict
from pathlib import Path
from google import genai
from PIL import Image

def generate_nano_banana_images(prompt_segments: List[Dict], output_dir: str = "static/images"):
    """
    각 세그먼트의 프롬프트를 기반으로 나노바나나(Gemini 3.1) 이미지를 생성하고 저장
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise Exception("GOOGLE_API_KEY가 설정되지 않았습니다.")

    # 출력 디렉토리 생성
    images_path = Path(output_dir)
    images_path.mkdir(parents=True, exist_ok=True)
    
    # 최신 google-genai 클라이언트 초기화
    client = genai.Client(api_key=api_key)
    
    results = []
    
    for seg in prompt_segments:
        seg_id = seg.get("segment_id")
        prompt = seg.get("prompt")
        
        print(f"Generating Image with Nano Banana for Segment {seg_id}...")
        
        try:
            # 1. 모델 설정 (사용자 URL 기반: gemini-3.1-flash-image-preview)
            # 'models/gemini-3.1-flash-image-preview' 또는 'gemini-3.1-flash-image-preview'
            model_id = 'gemini-3.1-flash-image-preview'
            
            # 2. 이미지 생성 요청
            response = client.models.generate_content(
                model=model_id,
                contents=[prompt]
            )
            
            # 3. 응답에서 이미지 추출 및 저장
            image_filename = f"nano_segment_{seg_id}_{int(time.time())}.png"
            full_path = images_path / image_filename
            
            image_found = False
            if response.parts:
                for part in response.parts:
                    # google-genai SDK는 as_image() 또는 inline_data를 사용함
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # binary data를 PIL Image로 변환 혹은 바로 저장
                        with open(full_path, "wb") as f:
                            f.write(part.inline_data.data)
                        image_found = True
                        break
                    elif hasattr(part, 'as_image') and callable(part.as_image):
                        # SDK 버전에 따라 as_image helper 제공 가능
                        img = part.as_image()
                        img.save(full_path)
                        image_found = True
                        break

            if image_found:
                relative_url = f"/static/images/{image_filename}"
                results.append({
                    "segment_id": seg_id,
                    "image_url": relative_url,
                    "prompt": prompt
                })
            else:
                raise Exception("응답에 이미지 데이터가 포함되어 있지 않습니다.")
            
        except Exception as e:
            print(f"Segment {seg_id} Nano Banana Generation Failed: {e}")
            results.append({
                "segment_id": seg_id,
                "image_url": None,
                "error": str(e)
            })
            
    return results
