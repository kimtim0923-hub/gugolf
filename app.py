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
from report_generator import generate_golf_report
import requests

# 설정 로드
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

app = FastAPI(title="Gugolf AI Preview Generator")

from fastapi.middleware.cors import CORSMiddleware

# CORS 설정 (러버블 프론트엔드 등 외부 도메인에서의 접속 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (또는 프론트엔드 주소)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

# 정적 파일 및 템플릿 설정
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

class GenerateRequest(BaseModel):
    date: Optional[str] = None
    community_reactions: Optional[dict] = None  # {대회별 커뮤니티 반응}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Vercel 실행 환경 진단용 엔드포인트"""
    import requests as req_lib
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    google_key = os.getenv("GOOGLE_API_KEY", "")
    result = {
        "status": "ok",
        "anthropic_key_prefix": anthropic_key[:15] + "..." if anthropic_key else "NOT SET",
        "google_key_set": bool(google_key),
        "claude_models": {},
        "gemini_models": {},
    }
    if anthropic_key:
        for model in ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
                      "claude-3-haiku-20240307", "claude-3-opus-20240229",
                      "claude-3-7-sonnet-20250219", "claude-2.1"]:
            try:
                r = req_lib.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": model, "max_tokens": 5,
                          "messages": [{"role": "user", "content": "hi"}]},
                    timeout=15,
                )
                result["claude_models"][model] = "OK" if r.ok else f"FAIL {r.status_code}"
            except Exception as e:
                result["claude_models"][model] = f"ERR: {str(e)[:60]}"
    if google_key:
        for model in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-001"]:
            try:
                r = req_lib.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={google_key}",
                    json={"contents": [{"role": "user", "parts": [{"text": "hi"}]}]},
                    timeout=15,
                )
                result["gemini_models"][model] = "OK" if r.ok else f"FAIL {r.status_code}: {r.text[:80]}"
            except Exception as e:
                result["gemini_models"][model] = f"ERR: {str(e)[:60]}"
    return result

@app.post("/api/generate_preview")
async def api_generate_preview(req: GenerateRequest):
    """이번 주 프리뷰 및 TTS 스크립트 생성"""
    try:
        ref_date = datetime.strptime(req.date, "%Y-%m-%d") if req.date else datetime.now()
        tournaments = collect_all_tours(ref_date)
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY가 없습니다.")
            
        result = generate_golf_news_script(
            tournaments=tournaments,
            reference_date=ref_date,
            api_key=api_key,
            community_reactions=req.community_reactions
        )
        
        return {
            "viewing_points": result.viewing_points,
            "tts_script": result.tts_script,
            "thumbnails": result.thumbnails,
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
            "thumbnails": getattr(result, 'thumbnails', []),
            "tournaments": tournaments
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
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
