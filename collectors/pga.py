"""
PGA Tour 대회 정보 수집
데이터 소스: schedule_data/pga_2026.json (사용자 제공)
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import BaseTournamentCollector, TournamentInfo, get_current_week_range

SCHEDULE_FILE = Path(__file__).parent.parent / "schedule_data" / "pga_2026.json"
PGA_SCHEDULE_URL = "https://www.pgatour.com/schedule"


class PGACollector(BaseTournamentCollector):
    TOUR_NAME = "PGA Tour"

    def fetch_schedule(self, reference_date: Optional[datetime] = None, mode: str = "current") -> Optional[TournamentInfo]:
        from .base import get_current_week_range, get_last_week_range
        if mode == "last":
            week_start, week_end = get_last_week_range(reference_date)
        else:
            week_start, week_end = get_current_week_range(reference_date)
            
        print(f"[PGA] 검색 주간 ({mode}): {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")

        if not SCHEDULE_FILE.exists():
            print(f"[PGA] 스케줄 파일 없음: {SCHEDULE_FILE}")
            return None

        with open(SCHEDULE_FILE, encoding="utf-8") as f:
            tournaments = json.load(f)

        # 해당 주 대회 목록 수집 (복수 가능)
        matches = []
        for t in tournaments:
            try:
                start = datetime.strptime(t["start_date"], "%Y-%m-%d")
                end = datetime.strptime(t["end_date"], "%Y-%m-%d")
            except (KeyError, ValueError):
                continue
            if self._is_in_week(start, end, week_start, week_end):
                matches.append((t, start, end))

        if not matches:
            return None

        # 우선순위: MAJOR > SIGNATURE EVENT > 일반 대회
        def priority(item):
            t_type = item[0].get("type", "")
            if "MAJOR" in t_type:
                return 0
            if "SIGNATURE" in t_type:
                return 1
            return 2

        matches.sort(key=priority)
        t, start, end = matches[0]

        # 복수 대회가 있을 때 extra에 병행 대회 정보 추가
        concurrent = []
        for other, os_, oe_ in matches[1:]:
            concurrent.append(f"{other['name']} ({other.get('course', '')})")

        parts = [t.get("course", ""), t.get("city", ""), t.get("state", ""), t.get("country", "")]
        location = ", ".join(p for p in parts if p)
        date_range = f"{start.month}월 {start.day}일 ~ {end.month}월 {end.day}일"
        prize = t.get("prize", "미정") or "미정"

        extra = {}
        if concurrent:
            extra["concurrent"] = " / ".join(concurrent)
        if t.get("previous_winner"):
            extra["previous_winner"] = t["previous_winner"]
        if t.get("type"):
            extra["event_type"] = t["type"]

        return TournamentInfo(
            tour=self.TOUR_NAME,
            name=t["name"],
            location=location,
            date_range=date_range,
            prize=prize,
            course=t.get("course", ""),
            url=PGA_SCHEDULE_URL,
            extra=extra,
        )
