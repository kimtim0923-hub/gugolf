"""
PGA / LPGA / DP World Tour 2026 전체 시즌 스케줄을 Google Sheets에 일괄 저장.
최초 1회만 실행하면 됩니다.

실행:
  python import_full_schedule.py
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SCHEDULE_FILES = {
    "PGA 2026 전체": Path(__file__).parent / "schedule_data" / "pga_2026.json",
    "LPGA 2026 전체": Path(__file__).parent / "schedule_data" / "lpga_2026.json",
    "DP World 2026 전체": Path(__file__).parent / "schedule_data" / "dpworld_2026.json",
}

FULL_SCHEDULE_HEADERS = [
    "투어",
    "대회명",
    "시작일",
    "종료일",
    "코스",
    "도시",
    "국가",
    "상금",
    "종류",
]

TOUR_LABELS = {
    "PGA 2026 전체": "PGA Tour",
    "LPGA 2026 전체": "LPGA Tour",
    "DP World 2026 전체": "DP World Tour",
}


def load_schedule(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_rows(sheet_title: str, tournaments: list[dict]) -> list[list]:
    tour_label = TOUR_LABELS.get(sheet_title, sheet_title)
    rows = []
    for t in tournaments:
        event_type = t.get("type", t.get("swing", ""))
        rows.append([
            tour_label,
            t.get("name", ""),
            t.get("start_date", ""),
            t.get("end_date", ""),
            t.get("course", ""),
            t.get("city", ""),
            t.get("country", ""),
            t.get("prize", ""),
            event_type,
        ])
    return rows


def main():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    credentials_path = os.getenv(
        "GOOGLE_CREDENTIALS_PATH",
        "credentials/google_service_account.json"
    )
    creds_full_path = Path(__file__).parent / credentials_path

    if not sheet_id:
        print("❌ GOOGLE_SHEET_ID가 설정되지 않았습니다.")
        print("   먼저 setup_sheets.py를 실행하여 스프레드시트를 생성하세요.")
        return

    if not creds_full_path.exists():
        print(f"❌ 서비스 계정 파일을 찾을 수 없습니다: {creds_full_path}")
        return

    from sheets import SheetsManager

    mgr = SheetsManager(
        spreadsheet_id=sheet_id,
        credentials_path=str(creds_full_path),
    )

    for sheet_title, json_path in SCHEDULE_FILES.items():
        if not json_path.exists():
            print(f"⚠️  파일 없음, 건너뜀: {json_path}")
            continue

        print(f"\n📋 {sheet_title} 저장 중...")
        tournaments = load_schedule(json_path)
        rows = build_rows(sheet_title, tournaments)
        mgr.save_full_schedule(
            sheet_title=sheet_title,
            headers=FULL_SCHEDULE_HEADERS,
            rows=rows,
        )
        print(f"   ✅ {len(rows)}개 대회 저장 완료")

    print("\n✅ 전체 시즌 스케줄 저장 완료!")


if __name__ == "__main__":
    main()
