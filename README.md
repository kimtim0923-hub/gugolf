# ⛳️ Gugolf AI Preview Generator

골프 전문 뉴스 채널을 위한 AI 기반 프리뷰 및 이미지 프롬프트 생성 자동화 시스템입니다.

## 🌟 주요 기능

1.  **실시간 대회 정보 수집**: PGA, LPGA, KPGA, KLPGA, DP World Tour의 이번 주 개최 정보를 자동으로 수집합니다.
2.  **Claude 3 Opus 기반 뉴스 대본 생성**: 수집된 데이터를 바탕으로 전문적인 골프 뉴스 YouTuber 스타일의 TTS용 대본과 관전 포인트를 생성합니다.
3.  **Gemini 2.5 Flash 기반 지능형 이미지 기획**:
    *   대본을 문맥 단위로 자연스럽게 분할 (약 10초 분량).
    *   실제 골프 코스의 특징(아일랜드 그린, 시그니처 랜드마크 등)을 반영한 **사실 기반(Fact-based)** 고퀄리티 영문 프롬프트 생성.
4.  **Nano Banana (Gemini) 이미지 생성**: 생성된 프롬프트를 바탕으로 실제 미리보기 이미지를 즉시 생성하고 다운로드할 수 있습니다.

## 🛠 기술 스택

*   **Backend**: FastAPI, Python 3.11+
*   **AI Models**:
    *   **Claude 3 Opus** (Script & Analysis)
    *   **Gemini 2.5 Flash** (Image Prompting & Segmentation)
    *   **Gemini Image Generation** (Visual Assets)
*   **Infrastructure**: Git, Vercel/Render (Deployment ready)

## 🚀 시작하기

1.  **환경 설정**:
    `.env` 파일을 생성하고 다음 API 키를 입력하세요.
    ```env
    ANTHROPIC_API_KEY=your_anthropic_key
    GOOGLE_API_KEY=your_google_key
    ```

2.  **종속성 설치**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **서버 실행**:
    ```bash
    python app.py
    ```
    접속 주소: `http://localhost:8000`

## 👨‍💻 설계 철학

이 프로젝트는 **최고의 사실성**과 **제작 효율성**에 집중합니다. 단순한 이미지가 아닌, 실제 골퍼들이 공감할 수 있는 경기장의 특징을 AI가 직접 찾아내어 시각화합니다.
