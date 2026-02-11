# Telegram Bot Setup Guide

## 1. 텔레그램 봇 생성

1. 텔레그램에서 **@BotFather** 검색
2. `/newbot` 명령어 입력
3. 봇 이름 입력 (예: Stock Screener Bot)
4. 봇 username 입력 (예: my_stock_screener_bot)
5. **토큰(token)** 을 받음 (예: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## 2. Chat ID 확인

### 방법 1: @userinfobot 사용 (개인 채팅)

1. 텔레그램에서 **@userinfobot** 검색
2. `/start` 또는 아무 메시지 전송
3. **Your user ID** 값 복사 (예: `987654321`)

### 방법 2: 그룹 채팅에 추가

1. 그룹 생성 또는 기존 그룹 선택
2. 생성한 봇을 그룹에 추가
3. 브라우저에서 다음 URL 접속:

   ```text
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```

4. JSON 응답에서 `"chat":{"id": -1234567890}` 값 확인

## 3. .env 파일 설정

프로젝트 루트에 `.env` 파일 생성:

```bash
# .env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

**주의**: `.env` 파일은 Git에 커밋하지 마세요! (이미 .gitignore에 추가됨)

## 4. 라이브러리 설치

```bash
pip install python-telegram-bot python-dotenv
```

## 5. 테스트

```python
from src.telegram_notifier import send_telegram

# 간단한 메시지 전송
send_telegram("🚀 Test message from Stock Screener!")

# 마크다운 형식
message = """
*Stock Screener Alert* 🎯

📊 *AAPL* - Apple Inc.
💵 Price: $259.48
📈 Volume: 2.5x

_Stage 2 Breakout!_
"""
send_telegram(message)
```

## 6. 스크리너에서 사용

```python
from src.telegram_notifier import get_notifier

notifier = get_notifier()

# 스크리닝 결과 전송
if buy_signals:
    message = notifier.format_screening_results(
        market="NASDAQ-100",
        strategy="Weinstein Stage",
        buy_signals=buy_signals
    )
    notifier.send_sync(message)
```

## 트러블슈팅

### 봇이 메시지를 못 받는 경우

1. 봇과 **개인 채팅**을 먼저 시작하세요 (`/start` 명령)
2. 그룹에서는 봇에게 **관리자 권한** 부여 (선택사항)

### Chat ID가 작동하지 않는 경우

- 개인 채팅: 양수 (예: `987654321`)
- 그룹 채팅: 음수 (예: `-1234567890`)
- ID 앞에 마이너스 기호 확인

### API 에러

- 봇 토큰이 정확한지 확인
- 네트워크 연결 확인
- 텔레그램 API 상태 확인: <https://core.telegram.org/bots/api>
