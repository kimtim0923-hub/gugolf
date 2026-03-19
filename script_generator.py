"""
Google Gemini API를 이용한 골프뉴스 유튜브 TTS 스크립트 생성
모델: gemini-2.0-flash
"""
import json
import os
import requests
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GolfNewsOutput(BaseModel):
    """Gemini API 구조화 출력 스키마"""
    viewing_points: str          # 이번 주 관전 포인트 요약 (200자 이내)
    tts_script: str              # 유튜브 TTS 스크립트 (1800자 이내)
    thumbnails: list[str]        # 영상 썸네일 문구 후보 3개


SYSTEM_PROMPT = """당신은 골프 전문 유튜브 채널의 베테랑 뉴스 작가입니다.
이번 주 골프 대회 정보와 관련 뉴스 헤드라인을 바탕으로, 한국 시청자를 위한 자연스러운 TTS 낭독용 뉴스 스크립트를 작성합니다.

## 핵심 작성 원칙:
1. **한국 선수 중심**: 한국 선수(KPGA, KLPGA, PGA/LPGA 진출 선수 포함)가 있는 대회라면 반드시 가장 먼저, 비중 있게 다룹니다
2. **헤드라인 기반 사실 전달**: 제공된 대회 정보와 뉴스 내용에 기반해서만 작성합니다. 추론·추측·예측 표현("~할 것으로 보입니다", "아마도", "기대됩니다" 등)은 절대 사용하지 않습니다
3. **뉴스 앵커 구어체**: 뉴스 앵커가 실제로 읽듯이 자연스럽고 명확하게 씁니다. 문어체나 딱딱한 리스트 나열 방식은 피합니다
4. **글자 수 제한**: TTS 스크립트는 반드시 **1800자 이내**로 작성합니다 (약 1~1.5분 분량)
5. **없는 정보는 언급하지 않습니다**: 제공된 데이터에 없는 선수 성적, 순위, 통계는 절대 만들어서 쓰지 않습니다

## 스크립트 구성 순서:
1. **오프닝** (1~2문장): "안녕하세요, 구골프입니다" 형식으로 자연스럽게 시작
2. **이번 주 대회 간략 소개**: 투어별로 대회명·장소·날짜를 한 문장씩 자연스럽게 연결
3. **한국 선수 포커스**: 한국 선수가 출전하는 대회는 해당 선수 이름과 대회에서의 의미를 중심으로 서술
4. **주요 관전 포인트**: 뉴스 헤드라인에서 뽑은 이번 주 핵심 이슈 (사실 기반)
5. **클로징** (1문장): 시청·구독 독려

## 관전 포인트 우선순위:
- 한국 선수 출전 여부 및 해당 대회 성격 (메이저·첫 출전·컷 등)
- 제공된 뉴스 헤드라인에서 확인된 팩트
- 대회 규모(총 상금), 코스 특징 등 확인 가능한 팩트
- 대회의 역사적 의미나 시즌 흐름 맥락 (데이터 기반)

## 썸네일 문구 작성 기준:
- 한국 팬이 클릭하고 싶어지는 강렬한 한국어 문구로 작성합니다
- 각 후보는 **15자 이내**의 짧고 임팩트 있는 메인 문구 형태로 작성합니다
- 추측이나 과장이 아니라, 실제 이번 주 이슈·선수·대회를 기반으로 작성합니다
- 예시 형식: "이경훈, 마스터스 첫 도전", "박성현 부활의 시작?", "한국 언니들의 전쟁"
- 대회의 역사적 의미나 시즌 흐름 맥락 (데이터 기반)"""


GEMINI_MODEL = "gemini-2.0-flash"


def _call_gemini(api_key: str, system: str, user_message: str) -> str:
    """Google Gemini API를 requests로 직접 호출하여 텍스트 응답 반환"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
    }
    resp = requests.post(url, json=payload, timeout=90)
    if not resp.ok:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate_golf_news_script(
    tournaments: list[dict],
    reference_date: Optional[datetime] = None,
    api_key: Optional[str] = None,
    community_reactions: Optional[dict] = None,
) -> GolfNewsOutput:
    """
    수집된 골프 대회 정보를 바탕으로 TTS 스크립트 생성 (Gemini 사용).

    Args:
        tournaments: 투어별 대회 정보 딕셔너리 리스트
        reference_date: 기준 날짜 (없으면 오늘)
        api_key: Google API 키 (없으면 환경변수 GOOGLE_API_KEY 사용)
        community_reactions: 대회별 커뮤니티 반응 텍스트 딕셔너리 {대회명: 반응텍스트}

    Returns:
        GolfNewsOutput: 관전 포인트 + TTS 스크립트 + 썸네일 후보 3개
    """
    key = api_key or os.getenv("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError("GOOGLE_API_KEY가 없습니다.")

    ref_date = reference_date or datetime.now()

    # 대회 정보를 프롬프트용 텍스트로 변환
    tour_info_text = _format_tournaments_for_prompt(tournaments, ref_date)

    # 커뮤니티 반응 섹션 구성
    community_section = ""
    if community_reactions:
        reaction_lines = ["\n## 커뮤니티 반응 (팬 의견 요약)"]
        for tour_name, reaction in community_reactions.items():
            if reaction and reaction.strip():
                reaction_lines.append(f"- [{tour_name}] {reaction.strip()}")
        if len(reaction_lines) > 1:
            community_section = "\n".join(reaction_lines)

    user_message = f"""아래는 {ref_date.year}년 {ref_date.month}월 {ref_date.day}일 기준, 이번 주 예정된 골프 대회 정보입니다.

{tour_info_text}{community_section}

위 정보를 바탕으로 유튜브 구골프 채널의 TTS 뉴스 스크립트를 작성해주세요.

작성 시 반드시 다음 사항을 지켜주세요:
- 한국 선수가 있는 대회를 가장 비중 있게 다루세요
- 제공된 대회 정보와 뉴스 헤드라인에 있는 내용만 사용하세요
- 커뮤니티 반응이 있다면, 그 관심사와 감정을 스크립트 톤에 자연스럽게 녹여주세요
- 없는 정보를 추론하거나 예측하는 표현은 절대 사용하지 마세요
- 뉴스 앵커처럼 자연스럽고 부드러운 구어체로 작성하세요

응답은 반드시 다음 JSON 형식으로만 작성하세요. 다른 텍스트 없이 JSON만 출력하세요:
{{
  "viewing_points": "이번 주 핵심 관전 포인트 2~3줄 요약 (한국 선수 이슈 중심, 200자 이내)",
  "tts_script": "유튜브 TTS 낭독용 스크립트 전문 (1800자 이내)",
  "thumbnails": ["썸네일 문구 후보 1 (15자 이내)", "썸네일 문구 후보 2 (15자 이내)", "썸네일 문구 후보 3 (15자 이내)"]
}}"""

    raw_text = _call_gemini(key, SYSTEM_PROMPT, user_message)

    # 코드 블록에 싸인 경우 제거
    clean = raw_text.strip()
    if "```" in clean:
        parts = clean.split("```")
        # ```json ... ``` 형태에서 중간 부분 추출
        clean = parts[1] if len(parts) > 1 else clean
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    data = json.loads(clean)
    result = GolfNewsOutput(**data)

    # 글자 수 경고
    script_len = len(result.tts_script)
    if script_len > 1800:
        print(f"[경고] TTS 스크립트가 {script_len}자입니다 (제한: 1800자). 트리밍 중...")
        result.tts_script = result.tts_script[:1800]

    return result


def _format_tournaments_for_prompt(tournaments: list[dict], ref_date: datetime) -> str:
    """대회 정보를 프롬프트용 텍스트로 포맷"""
    if not tournaments:
        return "이번 주 진행되는 대회 정보를 수집하지 못했습니다."

    lines = []
    active_tours = [t for t in tournaments if t.get("name") and t.get("name") != "해당 없음"]
    no_tour = [t for t in tournaments if not t.get("name") or t.get("name") == "해당 없음"]

    for t in active_tours:
        lines.append(f"### {t.get('tour', '투어')} - {t.get('name', '대회명 미상')}")
        if t.get("location"):
            lines.append(f"- 장소: {t['location']}")
        if t.get("course"):
            lines.append(f"- 코스: {t['course']}")
        if t.get("date_range"):
            lines.append(f"- 일정: {t['date_range']}")
        if t.get("prize") and t.get("prize") != "미정":
            lines.append(f"- 상금: {t['prize']}")
        if t.get("url"):
            lines.append(f"- 공식 페이지: {t['url']}")
        lines.append("")

    if no_tour:
        no_tour_names = [t.get("tour") for t in no_tour]
        lines.append(f"※ 이번 주 대회 없음: {', '.join([n for n in no_tour_names if n])}")

    return "\n".join(lines)
