# FnGuide 증권사 리포트 수집기

FnGuide에서 제공하는 증권사 리포트 데이터를 수집하여 이미지로 생성하고, 텔레그램과 API를 통해 전송하는 프로그램입니다.

## 주요 기능

- FnGuide 증권사 리포트 데이터 수집
- HTML 테이블을 이미지로 변환
- 페이지당 10개의 종목 데이터를 포함한 다중 페이지 생성
- 텔레그램 채널로 이미지 전송
- API를 통한 게시글 및 이미지 업로드
- 목표가 상향/하향 및 신규 종목 시각적 표시

## 설치 방법

1. 필수 프로그램 설치
   ```bash
   # wkhtmltopdf 설치 (이미지 생성에 필요)
   # Windows: https://wkhtmltopdf.org/downloads.html
   # Linux: sudo apt-get install wkhtmltopdf
   ```

2. Python 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```

3. 환경 변수 설정
   ```bash
   # .env.sample 파일을 .env로 복사
   cp .env.sample .env
   
   # .env 파일 수정
   # 필요한 환경 변수 값을 설정
   ```

## 환경 변수 설정

- `WKHTMLTOIMAGE_PATH`: wkhtmltoimage 실행 파일 경로
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 텔레그램 채널 ID
- `TELEGRAM_CHAT_TEST_ID`: 테스트용 텔레그램 채널 ID
- `API_BASE_URL`: API 서버 기본 URL

## 사용 방법

```bash
python main.py
```

## 출력 예시

1. 이미지 출력 형식
   - 종목명 (종목코드)
   - 리포트 제목 및 상세 내용
   - 투자의견
   - 목표주가 (상향/하향/신규 표시)
   - 전일종가
   - 증권사/작성자

2. 특수 표시
   - 목표가 상향: ▲ (빨간색)
   - 목표가 하향: ▼ (파란색)
   - 신규 종목: N (주황색)

## 주의사항

- wkhtmltopdf가 설치되어 있어야 합니다.
- 텔레그램 봇 설정이 필요합니다.
- API 서버가 구성되어 있어야 합니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
