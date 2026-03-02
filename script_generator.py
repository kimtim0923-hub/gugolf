"""
Claude API를 이용한 골프뉴스 유튜브 TTS 스크립트 생성
모델: claude-opus-4-6 (adaptive thinking)
"""
import json
from datetime import datetime
from typing import Optional

import anthropic
from pydantic import BaseModel


class GolfNewsOutput(BaseModel):
    """Claude API 구조화 출력 스키마"""
    viewing_points: str     # 이번 주 관전 포인트 요약 (200자 이내)
    tts_script: str         # 유튜브 TTS 스크립트 (1800자 이내)


SYSTEM_PROMPT = """당신은 골프 전문 방송 작가입니다.
제공된 이번 주 메이저 골프 대회 정보를 바탕으로 유튜브 채널용 TTS 스크립트를 작성합니다.

## 반드시 지켜야 할 규칙:
1. **확인된 데이터만 사용**: 제공된 정보에 없는 선수 성적, 랭킹, 통계는 절대 언급하지 마세요
2. **추측 금지**: "아마도", "~일 것입니다" 같은 추측성 표현 사용 금지
3. **총 1800자 이내**: TTS 스크립트는 1800자를 넘으면 안 됩니다 (약 1분 분량)
4. **자연스러운 구어체 한국어**: 딱딱한 문어체가 아닌 뉴스 앵커처럼 자연스럽게
5. **흥미 유발**: 팬들이 시청하고 싶어지도록 핵심 볼거리 위주로 작성

## 스크립트 구성 순서:
1. 인사/오프닝 (2~3문장)
2. 이번 주 대회 소개 (투어별로 대회명, 장소, 날짜 간단히)
3. 핵심 관전 포인트 (가장 주목할 대회/선수 스토리)
4. 클로징 (시청 독려)

## 관전 포인트 작성 기준:
- 대회의 역사적 의미나 특별한 배경
- 주목할 코스 특성
- 시즌 맥락 (시즌 초반/중반/후반 등)
- 대회 규모(상금) 등 팩트 기반 정보"""


def generate_golf_news_script(
    tournaments: list[dict],
    reference_date: Optional[datetime] = None,
    api_key: Optional[str] = None,
) -> GolfNewsOutput:
    """
    수집된 골프 대회 정보를 바탕으로 TTS 스크립트 생성.

    Args:
        tournaments: 투어별 대회 정보 딕셔너리 리스트
        reference_date: 기준 날짜 (없으면 오늘)
        api_key: Anthropic API 키 (없으면 환경변수 ANTHROPIC_API_KEY 사용)

    Returns:
        GolfNewsOutput: 관전 포인트 + TTS 스크립트
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    ref_date = reference_date or datetime.now()

    # 대회 정보를 프롬프트용 텍스트로 변환
    tour_info_text = _format_tournaments_for_prompt(tournaments, ref_date)

    user_message = f"""다음은 {ref_date.year}년 {ref_date.month}월 {ref_date.day}일 기준 이번 주 골프 대회 정보입니다.

{tour_info_text}

위 정보를 바탕으로 유튜브 골프뉴스 채널용 TTS 스크립트를 작성해주세요.
반드시 제공된 정보만 활용하고, 없는 선수 정보나 성적은 언급하지 마세요.

응답은 반드시 다음 JSON 형식으로 작성하세요:
{{
  "viewing_points": "이번 주 핵심 관전 포인트 요약 (200자 이내)",
  "tts_script": "유튜브 TTS 스크립트 전문 (1800자 이내)"
}}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "viewing_points": {
                            "type": "string",
                            "description": "이번 주 핵심 관전 포인트 요약 (200자 이내)"
                        },
                        "tts_script": {
                            "type": "string",
                            "description": "유튜브 TTS 스크립트 전문 (1800자 이내)"
                        }
                    },
                    "required": ["viewing_points", "tts_script"],
                    "additionalProperties": False
                }
            }
        }
    )

    # 텍스트 블록에서 JSON 파싱
    text_block = next(b for b in response.content if b.type == "text")
    data = json.loads(text_block.text)
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
        lines.append(f"※ 이번 주 대회 없음: {', '.join(no_tour_names)}")

    return "\n".join(lines)
