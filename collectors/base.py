"""
골프 대회 정보 수집 베이스 클래스
각 투어별 collector는 이 클래스를 상속받아 구현
"""
from datetime import datetime, timedelta
from typing import Optional


def get_current_week_range(reference_date: Optional[datetime] = None):
    """
    기준 날짜가 속한 주의 월요일~일요일 범위 반환.
    reference_date가 없으면 오늘 기준.
    """
    today = reference_date or datetime.now()
    # 월요일(0)부터 일요일(6)
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0), \
           sunday.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_last_week_range(reference_date: Optional[datetime] = None):
    """
    기준 날짜 대비 지난주의 월요일~일요일 범위 반환.
    """
    today = reference_date or datetime.now()
    last_sunday = today - timedelta(days=today.weekday() + 1)
    last_monday = last_sunday - timedelta(days=6)
    return last_monday.replace(hour=0, minute=0, second=0, microsecond=0), \
           last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)


class TournamentInfo:
    """대회 정보 데이터 클래스"""

    def __init__(
        self,
        tour: str,
        name: str,
        location: str,
        date_range: str,
        prize: str = "미정",
        course: str = "",
        url: str = "",
        extra: dict = None,
    ):
        self.tour = tour          # 투어명 (PGA, LPGA 등)
        self.name = name          # 대회명
        self.location = location  # 장소 (도시, 국가)
        self.date_range = date_range  # 날짜 범위 (예: "3월 6일 ~ 3월 9일")
        self.prize = prize        # 상금
        self.course = course      # 코스명
        self.url = url            # 대회 공식 페이지
        self.extra = extra or {}  # 추가 정보

    def to_dict(self) -> dict:
        return {
            "tour": self.tour,
            "name": self.name,
            "location": self.location,
            "date_range": self.date_range,
            "prize": self.prize,
            "course": self.course,
            "url": self.url,
            **self.extra,
        }

    def __repr__(self):
        return f"<TournamentInfo [{self.tour}] {self.name} | {self.date_range} | {self.location}>"


class BaseTournamentCollector:
    """
    투어별 대회 정보 수집 베이스 클래스.
    각 서브클래스에서 `fetch_schedule()` 메서드를 구현해야 함.
    """
    TOUR_NAME = "Unknown"

    def fetch_schedule(self, reference_date: Optional[datetime] = None, mode: str = "current") -> Optional[TournamentInfo]:
        """
        대회 정보를 반환. mode='current'는 이번 주, mode='last'는 지난 주.
        서브클래스에서 구현 필요.
        """
        raise NotImplementedError

    def _is_in_week(self, start_date: datetime, end_date: datetime,
                    week_start: datetime, week_end: datetime) -> bool:
        """대회가 해당 주와 겹치는지 확인"""
        return start_date <= week_end and end_date >= week_start
