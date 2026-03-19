"""
Google Gemini API를 이용한 골프뉴스 유튜브 TTS 스크립트 생성
report_generator.py와 동일한 SDK 방식 사용: google.genai + gemini-2.5-flash
"""
import json
import os
import re
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel


class GolfNewsOutput(BaseModel):
    """Gemini API 구조화 출력 스키마"""
    viewing_points: str          # 이번 주 관전 포인트 요약 (200자 이내)
    tts_script: str              # 유튜브 TTS 스크립트 (1800자 이내)
    thumbnails: list[str]        # 영상 썸네일 문구 후보 3개


SYSTEM_PROMPT = """당신은 골프 전문 유튜브 채널 '구골프'의 베테랑 뉴스 작가입니다.
이번 주 골프 대회 정보와 관련 뉴스 헤드라인을 바탕으로, 한국 시청자를 위한 자연스러운 TTS 낭독용 뉴스 스크립트를 작성합니다.

## 핵심 작성 원칙:
1. **한국 선수 중심**: 한국 선수(KPGA, KLPGA, PGA/LPGA 진출 선수 포함)가 있는 대회라면 반드시 가장 먼저, 비중 있게 다룹니다
2. **헤드라인 기반 사실 전달**: 제공된 대회 정보와 뉴스 내용에 기반해서만 작성합니다. 추론·추측·예측 표현("~할 것으로 보입니다", "아마도", "기대됩니다" 등)은 절대 사용하지 않습니다
3. **TTS 최적화**: 모든 마크다운(##, **, -, * 등)을 제거합니다. 뉴스 앵커가 읽듯 자연스러운 구어체로만 씁니다
4. **글자 수 제한**: TTS 스크립트는 반드시 **1800자 이내**로 작성합니다 (약 1~1.5분 분량)
5. **없는 정보는 언급하지 않습니다**: 제공된 데이터에 없는 선수 성적, 순위, 통계는 절대 만들어서 쓰지 않습니다

## 스크립트 구성 순서:
1. **오프닝** (1~2문장): "안녕하세요, 구골프입니다" 형식으로 자연스럽게 시작
2. **이번 주 대회 간략 소개**: 투어별로 대회명·장소·날짜를 한 문장씩 자연스럽게 연결
3. **한국 선수 포커스**: 한국 선수가 출전하는 대회는 해당 선수 이름과 대회에서의 의미를 중심으로 서술
4. **주요 관전 포인트**: 뉴스 헤드라인에서 뽑은 이번 주 핵심 이슈 (사실 기반)
5. **클로징** (1문장): 시청·구독 독려

## 썸네일 문구 작성 기준:
- 한국 팬이 클릭하고 싶어지는 강렬한 한국어 문구로 작성합니다
- 각 후보는 **15자 이내**의 짧고 임팩트 있는 메인 문구 형태로 작성합니다
- 예시 형식: "이경훈, 마스터스 첫 도전", "박성현 부활의 시작?", "한국 언니들의 전쟁"

## 출력 형식 (JSON):
응답은 반드시 아래 JSON 형식으로만 하며, 텍스트 외의 설명은 금지입니다.
{
  "viewing_points": "이번 주 핵심 관전 포인트 2~3줄 요약 (한국 선수 이슈 중심, 200자 이내)",
  "tts_script": "마크다운이 전혀 없는 순수 텍스트 TTS 낭독용 스크립트 (1800자 이내)",
  "thumbnails": ["썸네일 후보 1 (15자 이내)", "썸네일 후보 2 (15자 이내)", "썸네일 후보 3 (15자 이내)"]
}"""


def generate_golf_news_script(
    tournaments: list[dict],
    reference_date: Optional[datetime] = None,
    api_key: Optional[str] = None,
    community_reactions: Optional[dict] = None,
) -> GolfNewsOutput:
    """
    수집된 골프 대회 정보를 바탕으로 TTS 스크립트 생성 (Gemini SDK 사용).
    """
    key = api_key or os.getenv("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError("GOOGLE_API_KEY가 없습니다.")

    client = genai.Client(api_key=key)
    ref_date = reference_date or datetime.now()

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

위 정보를 바탕으로 유튜브 구골프 채널의 TTS 뉴스 스크립트를 작성해주세요."""

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=config,
        contents=user_message,
    )

    content = response.text
    # JSON 블록 추출
    json_match = re.search(r'(\{.*\})', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        json_str = re.sub(r'```(?:json)?', '', json_str)
        json_str = re.sub(r'```', '', json_str).strip()
        data = json.loads(json_str)
    else:
        data = json.loads(content.strip())

    result = GolfNewsOutput(**data)

    script_len = len(result.tts_script)
    if script_len > 1800:
        print(f"[경고] TTS 스크립트가 {script_len}자입니다. 트리밍 중...")
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
        lines.append("")

    if no_tour:
        no_tour_names = [t.get("tour") for t in no_tour if t.get("tour")]
        lines.append(f"※ 이번 주 대회 없음: {', '.join(no_tour_names)}")

    return "\n".join(lines)
