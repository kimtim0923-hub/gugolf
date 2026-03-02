"""
골프뉴스 프리뷰 자동 생성기 - 메인 실행 파일

실행 방법:
  python main.py                    # 오늘 날짜 기준 (매주 화요일 실행 권장)
  python main.py --date 2026-03-03  # 특정 날짜 기준 테스트
  python main.py --no-sheets        # Google Sheets 업데이트 없이 스크립트만 생성

cron 설정 (매주 화요일 오전 9시):
  0 9 * * 2 /usr/local/bin/python3 /Users/sorakim/Desktop/gugolf/main.py
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(Path(__file__).parent / ".env", override=True)


def parse_args():
    parser = argparse.ArgumentParser(description="골프뉴스 프리뷰 자동 생성기")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="기준 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)",
    )
    parser.add_argument(
        "--no-sheets",
        action="store_true",
        help="Google Sheets 업데이트 건너뜀",
    )
    parser.add_argument(
        "--no-script",
        action="store_true",
        help="Claude API TTS 스크립트 생성 건너뜀",
    )
    return parser.parse_args()


def collect_all_tours(reference_date: datetime, mode: str = "current") -> list[dict]:
    """5개 투어 대회 정보를 병렬로 수집"""
    from collectors import (
        PGACollector, LPGACollector, KPGACollector, KLPGACollector, DPWorldCollector
    )

    collectors = [
        PGACollector(),
        LPGACollector(),
        KPGACollector(),
        KLPGACollector(),
        DPWorldCollector(),
    ]

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_collector = {
            executor.submit(c.fetch_schedule, reference_date, mode): c
            for c in collectors
        }
        for future in as_completed(future_to_collector):
            collector = future_to_collector[future]
            try:
                info = future.result()
                if info:
                    results.append(info.to_dict())
                    print(f"✅ [{collector.TOUR_NAME}] {info.name} | {info.date_range} ({mode})")
                else:
                    results.append({
                        "tour": collector.TOUR_NAME,
                        "name": "해당 없음",
                        "location": "",
                        "date_range": "",
                        "prize": "",
                        "course": "",
                        "url": "",
                    })
                    print(f"⚪ [{collector.TOUR_NAME}] 해당 주 대회 없음 ({mode})")
            except Exception as e:
                print(f"❌ [{collector.TOUR_NAME}] 수집 실패: {e}")
                results.append({
                    "tour": collector.TOUR_NAME,
                    "name": "수집 실패",
                    "location": "",
                    "date_range": "",
                    "prize": "",
                    "course": "",
                    "url": "",
                })

    # 투어 순서 정렬
    tour_order = ["PGA Tour", "LPGA Tour", "DP World Tour", "KPGA", "KLPGA"]
    results.sort(key=lambda x: tour_order.index(x["tour"]) if x["tour"] in tour_order else 99)
    return results


def save_csv_to_file(tournaments: list[dict], reference_date: datetime):
    """대회 정보를 output 폴더에 CSV로 저장 (Google Sheets 미설정 시 폴백)"""
    import csv
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    date_str = reference_date.strftime("%Y%m%d")
    file_path = output_dir / f"schedule_{date_str}.csv"

    fieldnames = ["tour", "name", "location", "course", "date_range", "prize", "url"]
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(tournaments)
    print(f"💾 대회 정보 CSV 저장: {file_path}")


def save_script_to_file(script: str, viewing_points: str, reference_date: datetime):
    """스크립트를 output 폴더에 저장"""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    date_str = reference_date.strftime("%Y%m%d")
    file_path = output_dir / f"script_{date_str}.txt"

    content = f"""골프뉴스 프리뷰 스크립트
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}
기준 날짜: {reference_date.strftime('%Y-%m-%d')}

=== 관전 포인트 ===
{viewing_points}

=== TTS 스크립트 ===
{script}

=== 글자 수 ===
TTS 스크립트: {len(script)}자 (제한: 1800자)
"""
    file_path.write_text(content, encoding="utf-8")
    print(f"\n💾 스크립트 저장: {file_path}")


def main():
    args = parse_args()

    # 기준 날짜 설정
    if args.date:
        try:
            reference_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"날짜 형식 오류: {args.date} (YYYY-MM-DD 형식으로 입력하세요)")
            sys.exit(1)
    else:
        reference_date = datetime.now()

    print(f"\n{'='*60}")
    print(f"🏌️  골프뉴스 프리뷰 자동 생성기")
    print(f"기준 날짜: {reference_date.strftime('%Y년 %m월 %d일')}")
    print(f"{'='*60}\n")

    # Step 1: 대회 정보 수집
    print("📡 대회 정보 수집 중...\n")
    tournaments = collect_all_tours(reference_date)

    active_tournaments = [t for t in tournaments if t.get("name") not in ("해당 없음", "수집 실패", "")]
    print(f"\n✨ 이번 주 대회: {len(active_tournaments)}개\n")

    for t in tournaments:
        status = "✅" if t.get("name") not in ("해당 없음", "수집 실패", "") else "⚪"
        print(f"  {status} {t.get('tour')}: {t.get('name', '해당 없음')}")
        if t.get("date_range"):
            print(f"       날짜: {t['date_range']}")
        if t.get("location"):
            print(f"       장소: {t['location']}")
        if t.get("prize") and t.get("prize") != "미정":
            print(f"       상금: {t['prize']}")
        print()

    # Step 2: TTS 스크립트 생성 (Claude API)
    viewing_points = ""
    script = ""

    if not args.no_script:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
            print("   .env 파일에 ANTHROPIC_API_KEY를 추가하거나")
            print("   export ANTHROPIC_API_KEY=your_key 를 실행하세요.")
        else:
            print("🤖 Claude AI로 TTS 스크립트 생성 중...\n")
            from script_generator import generate_golf_news_script
            try:
                result = generate_golf_news_script(
                    tournaments=tournaments,
                    reference_date=reference_date,
                    api_key=api_key,
                )
                viewing_points = result.viewing_points
                script = result.tts_script

                print("=" * 60)
                print("📌 관전 포인트")
                print("=" * 60)
                print(viewing_points)
                print()
                print("=" * 60)
                print(f"📝 TTS 스크립트 ({len(script)}자)")
                print("=" * 60)
                print(script)
                print()

                save_script_to_file(script, viewing_points, reference_date)
            except Exception as e:
                print(f"❌ 스크립트 생성 실패: {e}")

    # Step 3: Google Sheets 업데이트
    # Sheets 미설정 시 CSV 저장
    if not args.no_sheets and not os.getenv("GOOGLE_SHEET_ID"):
        save_csv_to_file(tournaments, reference_date)

    if not args.no_sheets and (viewing_points or script):
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        credentials_path = os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            "credentials/google_service_account.json"
        )
        creds_full_path = Path(__file__).parent / credentials_path

        if not sheet_id:
            print("⚠️  GOOGLE_SHEET_ID가 설정되지 않았습니다.")
            print("   먼저 setup_sheets.py를 실행하여 스프레드시트를 생성하세요.")
        elif not creds_full_path.exists():
            print(f"⚠️  구글 서비스 계정 파일을 찾을 수 없습니다: {creds_full_path}")
            print("   README의 Google Sheets 설정 가이드를 참조하세요.")
        else:
            print("📊 Google Sheets 업데이트 중...")
            from sheets import SheetsManager
            try:
                mgr = SheetsManager(
                    spreadsheet_id=sheet_id,
                    credentials_path=str(creds_full_path),
                )
                mgr.update(
                    tournaments=tournaments,
                    script=script,
                    viewing_points=viewing_points,
                    reference_date=reference_date,
                )
                print("✅ Google Sheets 업데이트 완료!")
            except Exception as e:
                print(f"❌ Google Sheets 업데이트 실패: {e}")

    print(f"\n{'='*60}")
    print("완료!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
