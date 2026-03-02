"""
Google Sheets 초기 설정 스크립트
처음 한 번만 실행하면 됩니다.

실행 전 필수:
1. credentials/google_service_account.json 파일 준비
2. .env 파일에 GOOGLE_CREDENTIALS_PATH 설정 (선택)

실행:
  python setup_sheets.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def main():
    credentials_path = os.getenv(
        "GOOGLE_CREDENTIALS_PATH",
        "credentials/google_service_account.json"
    )
    creds_full_path = Path(__file__).parent / credentials_path

    if not creds_full_path.exists():
        print(f"❌ 서비스 계정 파일이 없습니다: {creds_full_path}")
        print()
        print("Google Sheets 설정 방법:")
        print("1. https://console.cloud.google.com 접속")
        print("2. 새 프로젝트 생성 또는 기존 프로젝트 선택")
        print("3. 'API 및 서비스' → 'API 라이브러리'에서 다음 두 API 활성화:")
        print("   - Google Sheets API")
        print("   - Google Drive API")
        print("4. 'API 및 서비스' → '사용자 인증 정보' → '서비스 계정 만들기'")
        print("5. 서비스 계정 생성 후 '키 추가' → 'JSON 다운로드'")
        print(f"6. 다운로드한 파일을 {creds_full_path} 로 저장")
        print("7. 이 스크립트를 다시 실행")
        return

    from sheets import create_or_open_spreadsheet

    print("📊 Google Sheets 스프레드시트 생성 중...")
    sheet_id = create_or_open_spreadsheet(
        credentials_path=str(creds_full_path),
        title="골프뉴스 프리뷰"
    )

    print(f"\n✅ 완료!")
    print(f"Spreadsheet ID: {sheet_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    print()
    print("다음 단계:")
    print(f"1. .env 파일에 다음을 추가하세요:")
    print(f"   GOOGLE_SHEET_ID={sheet_id}")
    print()
    print("2. 스프레드시트를 직접 열어 편집 권한을 추가하려면:")
    print("   구글 시트 → 공유 → 서비스 계정 이메일 추가")

    # .env 파일에 자동 업데이트
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if "GOOGLE_SHEET_ID" not in content:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\nGOOGLE_SHEET_ID={sheet_id}\n")
            print(f"\n✅ .env 파일에 GOOGLE_SHEET_ID가 자동으로 추가되었습니다.")
        else:
            print(f"\n⚠️  .env 파일에 이미 GOOGLE_SHEET_ID가 있습니다. 수동으로 확인하세요.")
    else:
        env_path.write_text(
            f"ANTHROPIC_API_KEY=\nGOOGLE_SHEET_ID={sheet_id}\n"
            f"GOOGLE_CREDENTIALS_PATH=credentials/google_service_account.json\n",
            encoding="utf-8"
        )
        print(f"\n✅ .env 파일이 생성되었습니다. ANTHROPIC_API_KEY를 추가하세요.")


if __name__ == "__main__":
    main()
