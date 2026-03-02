import os
from datetime import datetime
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

# 기존 모듈 임포트
from main import collect_all_tours
from script_generator import generate_golf_news_script
from image_prompt_generator import generate_image_prompts
from image_service import generate_nano_banana_images
from report_generator import generate_golf_report
import requests

# 설정 로드
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

app = FastAPI(title="Gugolf AI Preview Generator")

# 정적 파일 및 템플릿 설정
templates = Jinja2Templates(directory="templates")

# static 및 images 폴더 생성
static_path = Path(__file__).parent / "static"
images_path = static_path / "images"
images_path.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

class GenerateRequest(BaseModel):
    date: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate_preview")
async def api_generate_preview(req: GenerateRequest):
    """이번 주 프리뷰 및 TTS 스크립트 생성"""
    try:
        ref_date = datetime.strptime(req.date, "%Y-%m-%d") if req.date else datetime.now()
        tournaments = collect_all_tours(ref_date)
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 없습니다.")
            
        result = generate_golf_news_script(
            tournaments=tournaments,
            reference_date=ref_date,
            api_key=api_key
        )
        
        return {
            "viewing_points": result.viewing_points,
            "tts_script": result.tts_script,
            "tournaments": tournaments
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_report")
async def api_generate_report(req: GenerateRequest):
    """지난주 대회 결과 리포트 생성"""
    try:
        ref_date = datetime.strptime(req.date, "%Y-%m-%d") if req.date else datetime.now()
        # 지난주 대회 정보 수집 (mode='last')
        tournaments = collect_all_tours(ref_date, mode="last")
        
        api_key = os.getenv("GOOGLE_API_KEY") # 리포트 생성은 검색 기능이 필요하므로 제미나이 사용
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY가 없습니다.")
            
        result = generate_golf_report(
            tournaments=tournaments,
            reference_date=ref_date,
            api_key=api_key
        )
        
        return {
            "viewing_points": result.summary,
            "tts_script": result.tts_script,
            "tournaments": tournaments
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_prompts")
async def api_generate_prompts(req: dict):
    """대본 기반 이미지 프롬프트 생성"""
    print(f"DEBUG: /api/generate_prompts requested - script length: {len(req.get('script', ''))}")
    script = req.get("script")
    tournaments = req.get("tournaments", [])
    if not script:
        raise HTTPException(status_code=400, detail="대본이 없습니다.")
        
    try:
        # 이미지 프롬프트 생성에 제미나이(Google)를 사용하도록 변경됨
        api_key = os.getenv("GOOGLE_API_KEY")
        segments = generate_image_prompts(script, tournaments, api_key)
        return {"segments": segments}
    except Exception as e:
        print(f"이미지 프롬프트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_actual_images")
async def api_generate_actual_images(req: dict):
    """나노바나나(Gemini)를 통한 실제 이미지 생성"""
    segments = req.get("segments")
    if not segments:
        raise HTTPException(status_code=400, detail="프롬프트 세그먼트가 없습니다.")
    
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY (Gemini/Nano Banana용)가 설정되지 않았습니다.")

    try:
        # 실제 나노바나나 API 호출 및 로컬 저장
        results = generate_nano_banana_images(segments, str(images_path))
        return {"images": results}
    except Exception as e:
        print(f"나노바나나 이미지 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export_notion")
async def api_export_notion(req: dict):
    """결과 데이터를 노션으로 내보내기"""
    notion_token = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        raise HTTPException(status_code=500, detail="노션 API 설정(KEY/DATABASE_ID)이 완료되지 않았습니다.")

    try:
        # 데이터 정리
        date_str = req.get("date", datetime.now().strftime("%Y-%m-%d"))
        tts_script = req.get("tts_script", "")
        viewing_points = req.get("viewing_points", "")
        tournaments = req.get("tournaments", [])
        segments = req.get("segments", [])

        # 노션 페이지 생성 데이터 구성
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        # 유형 결정 (프리뷰/리포트)
        content_type = req.get("type", "프리뷰")

        # 1. 페이지 본문 블록 구성
        children = [
            {"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": "🎙️ TTS 스크립트"}}]}},
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": tts_script[:2000]}}]}}, # 노션 글자수 제한 대응
            {"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": "⛳ 관전 포인트"}}]}},
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": viewing_points[:2000]}}]}},
            {"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": "📊 수집된 대회"}}]}}
        ]

        # 대회 정보 추가
        for t in tournaments:
            status = "✅" if t.get("name") not in ["해당 없음", "수집 실패"] else "⚪"
            children.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"{status} [{t.get('tour')}] {t.get('name')} (일시: {t.get('date', '미정')})"}}] }
            })

        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": "🎨 이미지 생성 맵"}}]}})

        # 세그먼트별 프롬프트 정보 추가 (콜아웃 형태로 구성)
        for s in segments:
            children.append({
                "object": "block", "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "🖼️"},
                    "color": "gray_background",
                    "rich_text": [{"type": "text", "text": {"content": f"순서: {s.get('segment_id')}\n뉴스 내용: {s.get('script')}\n\n[추천 프롬프트]\n{s.get('prompt')}\n\n[강화 포인트]\n{s.get('background_context')}"}}]
                }
            })

        # 노션 API 호출 (페이지 생성)
        notion_url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "타이틀": {"title": [{"text": {"content": date_str}}]},
                "유형": {"select": {"name": content_type}}
            },
            "children": children
        }

        response = requests.post(notion_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_data = response.json()
            print(f"Notion API Error: {error_data}")
            raise Exception(f"노션 API 오류: {error_data.get('message', '알 수 없는 오류')}")

        return {"status": "success", "message": "노션 저장 완료"}

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
