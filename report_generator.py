"""
제미나이 AI를 이용한 지난주 골프 대회 결과 리포트 생성 모듈
"""
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional
from google import genai
from google.genai import types

class GolfReportOutput:
    def __init__(self, summary: str, tts_script: str):
        self.summary = summary        # 요약 및 주요 이슈
        self.tts_script = tts_script  # 유튜브 TTS 스크립트

def generate_golf_report(
    tournaments: List[dict],
    reference_date: Optional[datetime] = None,
    api_key: Optional[str] = None
) -> GolfReportOutput:
    """
    지난주 대회의 결과와 흥미로운 이슈를 수집/분석하여 리포트 스크립트 생성
    """
    client = genai.Client(api_key=api_key)
    ref_date = reference_date or datetime.now()
    
    # 지난주(월~일) 범위 계산
    last_sunday = ref_date - timedelta(days=ref_date.weekday() + 1)
    last_monday = last_sunday - timedelta(days=6)
            
    # 프롬프트 구성 (구쌤의 골프이야기 채널 맞춤형)
    SYSTEM_PROMPT = """당신은 골프 전문 유튜버 '구쌤'입니다. 채널명은 '구쌤의 골프이야기'입니다.
제공된 지난주 골프 대회 정보를 바탕으로, AI TTS가 바로 읽을 수 있는 매끄러운 나레이션 대본을 작성합니다.

## 핵심 가이드:
1. **인트로**: 반드시 "안녕하세요! 구쌤의 골프이야기, 구쌤입니다."로 시작합니다.
2. **구조 (투어별 통합)**: 각 투어별로 [우승 결과 요약 + 해당 투어 한국 선수 소식]을 한 묶음으로 구성하여 흐름을 이어갑니다. 
   - 예: PGA 결과 -> PGA 한국 선수 -> LPGA 결과 -> LPGA 한국 선수 순서
3. **디피월드 투어**: 한국 선수가 없다면 아주 짧은 화제의 이슈만 전달하거나, 특별한 이슈가 없다면 생략해도 좋습니다.
4. **TTS 최적화 (매우 중요)**:
   - **모든 마크다운(##, **, -, * 등)을 제거**하세요. 텍스트만 작성합니다.
   - 불필요한 이미지 설명이나 특수 기호를 빼고, 사람이 말하는 듯한 자연스러운 구어체로만 작성합니다.
   - 숫자와 단위는 읽기 편하게 작성합니다 (예: 172만 8천 달러).
5. **한국 선수 비중**: 한국 선수들의 최종 순위와 활약상에 가장 많은 비중을 둡니다.

## 제약 사항:
- 전체 분량은 약 1500자 내외.
- **응답은 반드시 아래 JSON 형식으로만 하며, 텍스트 외의 설명은 금지입니다.**

## 출력 형식 (JSON):
{
  "summary": "핵심 결과 요약 (간략히)",
  "tts_script": "마크다운이 전혀 없는 순수 텍스트 나레이션 대본"
}"""

    # 제미나이의 구글 검색 기능을 활용하여 정보를 수집하도록 유도
    user_message = f"""{ref_date.year}년 {ref_date.month}월 {ref_date.day}일 기준, 지난주 종료된 골프 대회 결과를 리포트해주세요.
현재 한국 시간은 {datetime.now().strftime('%Y-%m-%d %H:%M')} 입니다.

[수집 대상 대회 리스트]
{json.dumps(tournaments, ensure_ascii=False)}

[요청 사항]
1. 리포트 기간: {last_monday.strftime('%-m월 %-d일')} ~ {last_sunday.strftime('%-m월 %-d일')}
2. 특히 LPGA, PGA 투어에서 한국 선수들이 몇 위를 했는지, 어떤 활약을 했는지 검색 도구를 사용해 상세히 기술해주세요.
3. 정보가 부족한 대회는 제외하고 정보가 확실한 '화제의 대회' 위주로 구성하세요."""

    try:
        model_name = "gemini-2.5-flash"
        print(f"DEBUG: Calling Gemini [{model_name}] for Korean-focused Report...")
        
        # Google Search Tool 설정
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            # response_mime_type="application/json", # 검색과 동시 사용 불가
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        response = client.models.generate_content(
            model=model_name,
            config=config,
            contents=user_message
        )
        
        # 텍스트에서 JSON 추출 및 정제 (가장 바깥쪽 { } 블록 추출)
        content = response.text
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        
        if json_match:
            try:
                # 추출된 블록에서 마크다운 코드 블록 기호(```json 등) 제거
                json_str = json_match.group(1)
                json_str = re.sub(r'```(?:json)?', '', json_str)
                json_str = re.sub(r'```', '', json_str).strip()
                
                data = json.loads(json_str)
            except Exception as e:
                print(f"JSON 파싱 실패: {e}")
                data = {"summary": "파싱 오류 (내용 확인 필요)", "tts_script": content}
        else:
            data = {"summary": "JSON 형식을 찾을 수 없음", "tts_script": content}

        return GolfReportOutput(
            summary=data.get("summary", "결과 요약 생성을 실패했습니다."),
            tts_script=data.get("tts_script", content)
        )
        
    except Exception as e:
        import traceback
        print(f"DEBUG ERROR: {e}")
        print(traceback.format_exc())
        return GolfReportOutput(
            summary="리포트 생성 실패",
            tts_script="죄송합니다. 지난주 대회 결과를 수집하는 중 오류가 발생했습니다. 다시 시도해 주세요."
        )
