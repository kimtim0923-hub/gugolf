"""
Google Sheets 연동 모듈
gspread + google-auth 서비스 계정 방식 사용
"""
import os
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = [
    "업데이트 일시",
    "기준 날짜",
    "투어",
    "대회명",
    "장소",
    "코스",
    "일시",
    "상금",
    "관전 포인트",
    "TTS 스크립트",
    "대회 URL",
]


class SheetsManager:
    """Google Sheets 업데이트 관리자"""

    def __init__(self, spreadsheet_id: str, credentials_path: str):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds = Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            self._client = gspread.authorize(creds)
        return self._client

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        if self._spreadsheet is None:
            client = self._get_client()
            self._spreadsheet = client.open_by_key(self.spreadsheet_id)
        return self._spreadsheet

    def _get_or_create_worksheet(self, title: str) -> gspread.Worksheet:
        """워크시트를 가져오거나 없으면 생성"""
        ss = self._get_spreadsheet()
        try:
            ws = ss.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = ss.add_worksheet(title=title, rows=1000, cols=len(SHEET_HEADERS))
            # 헤더 설정
            ws.append_row(SHEET_HEADERS)
            print(f"[Sheets] 새 워크시트 생성: {title}")
        return ws

    def update(
        self,
        tournaments: list[dict],
        script: str,
        viewing_points: str,
        reference_date: Optional[datetime] = None,
    ):
        """
        대회 정보와 TTS 스크립트를 Google Sheets에 업데이트.
        각 투어별로 한 행씩 추가.
        """
        ref_date = reference_date or datetime.now()
        year_title = str(ref_date.year)
        ws = self._get_or_create_worksheet(year_title)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        ref_date_str = ref_date.strftime("%Y-%m-%d")

        rows_to_add = []
        for t in tournaments:
            row = [
                now_str,
                ref_date_str,
                t.get("tour", ""),
                t.get("name", "해당 없음"),
                t.get("location", ""),
                t.get("course", ""),
                t.get("date_range", ""),
                t.get("prize", ""),
                viewing_points,
                script,
                t.get("url", ""),
            ]
            rows_to_add.append(row)

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            print(f"[Sheets] {len(rows_to_add)}개 행 추가 완료 (워크시트: {year_title})")
        else:
            print("[Sheets] 추가할 데이터 없음")

    def save_full_schedule(
        self,
        sheet_title: str,
        headers: list[str],
        rows: list[list],
    ):
        """
        전체 시즌 스케줄을 별도 워크시트에 저장 (기존 내용 전체 교체).
        """
        ss = self._get_spreadsheet()
        try:
            ws = ss.worksheet(sheet_title)
            ws.clear()
            print(f"[Sheets] 기존 워크시트 초기화: {sheet_title}")
        except gspread.WorksheetNotFound:
            ws = ss.add_worksheet(title=sheet_title, rows=max(len(rows) + 10, 200), cols=len(headers))
            print(f"[Sheets] 새 워크시트 생성: {sheet_title}")

        ws.append_row(headers)
        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
        print(f"[Sheets] {sheet_title}: 헤더 + {len(rows)}개 행 저장 완료")


def create_or_open_spreadsheet(
    credentials_path: str,
    title: str = "골프뉴스 프리뷰",
) -> str:
    """
    새 Google Sheets 스프레드시트를 생성하고 ID를 반환.
    이미 존재하면 기존 것을 반환.
    """
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)

    try:
        ss = client.open(title)
        print(f"[Sheets] 기존 스프레드시트 사용: {ss.url}")
    except gspread.SpreadsheetNotFound:
        ss = client.create(title)
        # 서비스 계정 소유이므로 편집 공유 (선택사항)
        print(f"[Sheets] 새 스프레드시트 생성: {ss.url}")

    return ss.id
