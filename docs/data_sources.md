# 데이터 소스 가이드

## 📊 데이터 출처

이 프로젝트는 **무료 데이터 소스**를 사용합니다. 별도의 유료 구독이 필요 없습니다.

---

## 🇺🇸 미국 시장 데이터

### yfinance (Yahoo Finance)

**사용 전략:**

- Weinstein Stage Analysis
- Aggressive SEPA 2026

**설치:**

```bash
pip install yfinance
```

**데이터:**

- **종목 범위**: NASDAQ-100, S&P 500, Russell 2000
- **데이터 항목**: Open, High, Low, Close, Volume
- **주기**: 일봉 (Daily)
- **지연 시간**: 약 15-20분 지연 (무료)
- **히스토리**: 최대 수십 년 (종목별 상이)

**장점:**

- ✅ 무료
- ✅ 설치 간편
- ✅ 안정적인 데이터
- ✅ 광범위한 종목 지원

**단점:**

- ⚠️ 실시간 아님 (15-20분 지연)
- ⚠️ 간혹 연결 오류 발생
- ⚠️ API 제한 (분당 2,000 호출)

**코드 예시:**

```python
import yfinance as yf

# 단일 종목
data = yf.download('AAPL', start='2024-01-01', end='2024-12-31')

# 여러 종목
data = yf.download(['AAPL', 'MSFT', 'GOOGL'], start='2024-01-01')
```

**프로젝트 구현:**

- `src/data_loader.py` - DataLoader 클래스
- `fetch_data()` 메서드로 자동 다운로드

---

## 🇰🇷 한국 시장 데이터

### FinanceDataReader

**사용 전략:**

- K-Minervini Pro
- K-Weinstein Stage

**설치:**

```bash
pip install finance-datareader
```

**데이터:**

- **종목 범위**: KOSPI, KOSDAQ, KONEX 전 종목 (2,000+ 종목)
- **데이터 항목**: Open, High, Low, Close, Volume, Change
- **주기**: 일봉 (Daily)
- **지연 시간**: 당일 종가 후 업데이트 (무료)
- **히스토리**: 최대 20년+

**데이터 소스:**

- KRX (한국거래소)
- Naver Finance
- Investing.com

**장점:**

- ✅ 완전 무료
- ✅ 한국 전 종목 커버
- ✅ 종목 코드 자동 매칭
- ✅ 기업 정보 제공 (시가총액, 업종 등)

**단점:**

- ⚠️ 당일 실시간 불가 (종가 후 업데이트)
- ⚠️ 간혹 데이터 누락 (중소형 종목)
- ⚠️ 서버 부하 시 속도 저하

**코드 예시:**

```python
import FinanceDataReader as fdr

# 단일 종목
df = fdr.DataReader('005930', '2024-01-01', '2024-12-31')  # 삼성전자

# 전체 종목 리스트
df_krx = fdr.StockListing('KRX')  # KOSPI + KOSDAQ + KONEX
df_kospi = fdr.StockListing('KOSPI')
df_kosdaq = fdr.StockListing('KOSDAQ')
```

**프로젝트 구현:**

- `k_weinstein_screener.py` - 직접 사용
- `test_k_sepa.py` - K-Minervini Pro 테스트

---

## 📦 종목 리스트

### 미국 종목 (`src/market_universe.py`)

**NASDAQ-100:**

- AAPL, MSFT, GOOGL, AMZN, TSLA 등
- 나스닥 상장 대형 기술주

**S&P 500:**

- 미국 대표 500개 기업
- AAPL, JPM, XOM, WMT 등

**Russell 2000:**

- 미국 중소형주 2,000개

**수동 관리:**

```python
# src/market_universe.py
NASDAQ100 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', ...
]

SP500 = [
    'AAPL', 'MSFT', 'JPM', 'BAC', ...
]
```

### 한국 종목 (자동)

**자동 로드:**

```python
import FinanceDataReader as fdr

# 실시간 전체 종목 리스트 자동 다운로드
df_krx = fdr.StockListing('KRX')
```

**업데이트:**

- 매 실행 시 최신 상장 종목 자동 갱신
- 상장폐지/신규상장 자동 반영

---

## 🔄 데이터 업데이트 주기

### 미국 시장

- **일중**: 15-20분 지연
- **일봉 확정**: 미국 시간 16:00 (종가 후)
- **스크리너 실행 권장**: 한국 시간 오전 6-7시 (미국 장 마감 후)

### 한국 시장

- **일중**: 실시간 불가
- **일봉 확정**: 한국 시간 15:30 (장 마감 후)
- **스크리너 실행 권장**: 한국 시간 16:00 이후

---

## 💡 데이터 품질

### 체크 항목

1. **결측치**: 거래 정지일 제외
2. **이상치**: 액면분할/병합 자동 조정
3. **배당**: 조정가격(Adjusted Close) 사용

### 프로젝트 처리

```python
# 최소 데이터 요구사항
if len(data) < 120:
    continue  # 데이터 부족 시 스킵

# NaN 체크
if pd.isna(row['sma50']) or pd.isna(row['sma120']):
    continue
```

---

## 🚀 대안 데이터 소스

### 유료 옵션 (업그레이드 시)

#### 1. Alpha Vantage

- **가격**: 무료 ~ $49/월
- **특징**: 실시간 데이터, 더 많은 지표
- **제한**: 무료는 하루 500 호출

#### 2. Polygon.io

- **가격**: $29/월 ~
- **특징**: 틱 단위 데이터, WebSocket 지원
- **용도**: 고빈도 트레이딩

#### 3. 키움증권 Open API (한국)

- **가격**: 무료 (계좌 필수)
- **특징**: 실시간, 주문 가능
- **단점**: 복잡한 설정, Windows 전용

#### 4. 한국투자증권 Open API

- **가격**: 무료 (계좌 필수)
- **특징**: 실시간 시세, REST API
- **장점**: 크로스 플랫폼

---

## 📝 데이터 소스 변경 방법

### 미국 주식

`src/data_loader.py` 수정:

```python
# 현재 (yfinance)
import yfinance as yf

def fetch_data(self, symbol, start_date, end_date):
    data = yf.download(symbol, start=start_date, end=end_date)
    return data

# Alpha Vantage로 변경
from alpha_vantage.timeseries import TimeSeries

def fetch_data(self, symbol, start_date, end_date):
    ts = TimeSeries(key='YOUR_API_KEY')
    data, meta_data = ts.get_daily_adjusted(symbol=symbol, outputsize='full')
    return pd.DataFrame(data).T
```

### 한국 주식

`k_weinstein_screener.py` 수정:

```python
# 현재 (FinanceDataReader)
import FinanceDataReader as fdr
df = fdr.DataReader(code, start_date, end_date)

# 키움 OpenAPI로 변경 (예시)
from kiwoom import Kiwoom
kiwoom = Kiwoom()
df = kiwoom.GetOHLCV(code, start_date, end_date)
```

---

## ⚠️ 주의사항

### API 제한

- **yfinance**: 분당 2,000 호출 제한
- **FinanceDataReader**: 초당 1-2 호출 권장

### 해결 방법

```python
import time

for symbol in symbols:
    data = fetch_data(symbol)
    time.sleep(0.5)  # 0.5초 대기
```

### 데이터 캐싱

```python
# 중복 다운로드 방지
if os.path.exists(f'cache/{symbol}.csv'):
    data = pd.read_csv(f'cache/{symbol}.csv')
else:
    data = fetch_data(symbol)
    data.to_csv(f'cache/{symbol}.csv')
```

---

## 📚 추가 자료

### 공식 문서

- **yfinance**: <https://github.com/ranaroussi/yfinance>
- **FinanceDataReader**: <https://github.com/FinanceData/FinanceDataReader>

### 관련 라이브러리

- **pandas-datareader**: 다양한 소스 통합
- **mplfinance**: 캔들차트 시각화
- **TA-Lib**: 기술적 지표 계산

---

## 🆘 트러블슈팅

### "No data found" 에러

- 종목 코드 확인 (AAPL vs AAPL.US)
- 날짜 범위 확인 (미래 날짜 불가)
- 인터넷 연결 확인

### 데이터 누락

- 거래 정지일 확인
- 최소 데이터 기간 완화 (120일 → 60일)

### 속도 느림

- 병렬 처리 활용 (multiprocessing)
- 캐싱 시스템 구축
- 종목 수 제한 (상위 N개만)

---

**완전 무료로 시작할 수 있습니다!** 📈✨
