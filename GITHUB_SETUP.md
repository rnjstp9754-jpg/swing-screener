# GitHub Actions 자동 실행 설정 가이드

매일 아침 8시에 주식 스크리너가 자동으로 돌아가게 하려면, GitHub에 **텔레그램 봇 토큰**을 비밀번호처럼 등록해줘야 합니다.

## 1단계: 코드 올리기 (Push)

먼저 작성된 코드를 GitHub 저장소에 올려야 합니다.

```bash
git add .
git commit -m "스윙 트레이딩 스크너 자동화 설정"
git push
```

## 2단계: GitHub 저장소 설정 이동

1. GitHub 웹사이트에서 본인 저장소(Repository)로 들어갑니다.
2. 상단 메뉴에서 ⚙️ **Settings** 클릭
3. 왼쪽 사이드바에서 **Secrets and variables** 클릭
4. 하위 메뉴에서 **Actions** 클릭

## 3단계: 비밀키(Secret) 등록

화면 오른쪽의 **New repository secret** 초록색 버튼을 눌러 두 가지를 각각 등록합니다.

### 첫 번째 Secret

- **Name**: `TELEGRAM_BOT_TOKEN`
- **Secret**: `8340566475:AAEPMJC8N4KZCmcLDNlABk_8qaYXPA7fiho`
- **Add secret** 버튼 클릭

### 두 번째 Secret

- **Name**: `TELEGRAM_CHAT_ID`
- **Secret**: `7580053187`
- **Add secret** 버튼 클릭

## 4단계: 작동 확인

1. 상단 메뉴에서 ▶️ **Actions** 탭 클릭
2. 왼쪽에서 **Daily Stock Screener** 워크플로우 클릭
3. 오른쪽 **Run workflow** 버튼을 눌러 수동으로 한 번 실행해봅니다.
4. 초록색 체크(✅)가 뜨고 텔레그램 메시지가 오면 성공!

---
이제 매일 한국 시간 **오전 8시**에 자동으로 실행됩니다. (PC가 꺼져 있어도 OK)
