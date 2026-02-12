#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
통합 스크리너 v2 - 효율 최적화
- 미국: Weinstein + SEPA (Minervini)
- 한국: K-Weinstein + K-SEPA (Minervini Pro)
- 텔레그램: 각 시장별 상위 10개만 전송
- CSV: 전체 결과 저장
"""

import sys
from datetime import datetime, timedelta
import pandas as pd
from src.data_loader import DataLoader
from src.telegram_notifier import get_notifier
from src.market_universe import load_nasdaq100, load_sp500
from strategies.sepa_minervini import SEPAStrategy
from strategies.k_sepa import KMinerviniProStrategy


def screen_us_all_strategies():
    """미국 시장 - Weinstein Stage + SEPA 전략"""
    print("\n[미국 시장] 스크리닝 중...")

    # NASDAQ-100 전체 + S&P 500 상위 150개
    nasdaq_symbols = load_nasdaq100()
    sp500_all = load_sp500()
    sp500_symbols = sp500_all[:150]

    # 중복 제거 (순서 보존)
    all_symbols = list(dict.fromkeys(nasdaq_symbols + sp500_symbols))

    print(f"[미국 시장] NASDAQ-100: {len(nasdaq_symbols)}개, S&P 500: {len(sp500_symbols)}개")
    print(f"[미국 시장] 중복 제거 후 총 {len(all_symbols)}개 종목 스크리닝")

    loader = DataLoader(verbose=False)
    sepa_strategy = SEPAStrategy()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2년치 (주봉 변환 필요)

    # S&P 500 지수 데이터 로드 (맨스필드 상대강도용)
    print("[미국 시장] S&P 500 지수 로딩 (상대강도 계산용)...")
    sp500_data = loader.fetch_data('^GSPC', start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    sp500_weekly = None
    if not sp500_data.empty:
        sp500_weekly = sp500_data['Close'].resample('W').last().dropna()
        print(f"[미국 시장] S&P 500 지수 {len(sp500_weekly)}주 로딩 완료")
    else:
        print("[미국 시장] S&P 500 지수 로딩 실패, 상대강도 생략")

    weinstein_signals = []
    sepa_signals = []
    processed = 0
    skipped = 0

    for symbol in all_symbols:
        try:
            data = loader.fetch_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if data.empty or len(data) < 200:
                skipped += 1
                continue

            # --- SEPA 전략 (현재 시점 직접 체크) ---
            if len(data) >= 250:
                try:
                    df_sepa = sepa_strategy.calculate_indicators(data)
                    idx_last = len(df_sepa) - 1
                    # 1차: STRIKE (VCP + 돌파 + 거래량)
                    signal = sepa_strategy.check_strike(df_sepa, idx_last)
                    if signal and signal['type'] == 'BUY':
                        sepa_signals.append({
                            'symbol': symbol,
                            'strategy': 'SEPA',
                            'stage': 'STRIKE',
                            'price': signal['price'],
                            'confidence': signal.get('confidence', 0),
                            'vol_ratio': signal['metrics']['volume_ratio'],
                            'reason': signal.get('reason', '미너비니 VCP 돌파')
                        })
                    else:
                        # 2차: 트렌드 템플릿만 통과 → Setup 대기 (관심 종목)
                        tt_pass, tt_detail = sepa_strategy.check_trend_template(df_sepa, idx_last)
                        if tt_pass:
                            row = df_sepa.iloc[idx_last]
                            vol_ratio = row['Volume'] / row['vol_avg_50'] if pd.notna(row['vol_avg_50']) and row['vol_avg_50'] > 0 else 0
                            pct_high = (row['Close'] / row['high_52w'] * 100) if pd.notna(row['high_52w']) and row['high_52w'] > 0 else 0
                            sepa_signals.append({
                                'symbol': symbol,
                                'strategy': 'SEPA',
                                'stage': 'Setup 대기',
                                'price': row['Close'],
                                'confidence': 0.3,
                                'vol_ratio': vol_ratio,
                                'reason': f"TT통과 | 52주고가 {pct_high:.0f}% | VCP/돌파 대기"
                            })
                except Exception:
                    pass

            # --- 와인스태인 Stage Analysis (주봉 기반) ---
            # 일봉 -> 주봉 변환
            weekly = data.resample('W').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last', 'Volume': 'sum'
            }).dropna()

            if len(weekly) < 35:  # 30주 SMA + 기울기 판단 필요
                continue

            # 1) 30주 이동평균선 (핵심 지표)
            weekly['SMA30W'] = weekly['Close'].rolling(window=30).mean()

            # 2) 이평선 기울기 (5주간 변화)
            weekly['SMA30W_slope'] = weekly['SMA30W'] - weekly['SMA30W'].shift(5)

            # 3) 4주 평균 거래량
            weekly['Vol_4W'] = weekly['Volume'].rolling(window=4).mean()

            # 4) 52주 신고가
            weekly['High_52W'] = weekly['High'].rolling(window=52, min_periods=30).max()

            # 5) 맨스필드 상대강도 (RSM)
            rsm = None
            if sp500_weekly is not None and len(sp500_weekly) > 52:
                # 주봉 인덱스 맞추기
                aligned = weekly['Close'].reindex(sp500_weekly.index, method='ffill')
                sp500_aligned = sp500_weekly.reindex(weekly.index, method='ffill')

                if len(sp500_aligned.dropna()) >= 52:
                    last_stock = weekly['Close'].iloc[-1]
                    last_index = sp500_aligned.iloc[-1]
                    if pd.notna(last_index) and last_index > 0:
                        rsd_current = (last_stock / last_index) * 100
                        # 52주 평균 RSD
                        rsd_series = (weekly['Close'] / sp500_aligned) * 100
                        rsd_sma52 = rsd_series.rolling(window=52, min_periods=30).mean().iloc[-1]
                        if pd.notna(rsd_sma52) and rsd_sma52 > 0:
                            rsm = ((rsd_current / rsd_sma52) - 1) * 100

            # 현재 주봉 = 아직 미완성일 수 있음 (주중)
            # 가격/SMA는 최신(-1) 사용, 거래량은 직전 완성 주봉(-2) 사용
            curr = weekly.iloc[-1]   # 최신 (가격/SMA용)
            last_complete = weekly.iloc[-2]  # 직전 완성 주봉 (거래량용)

            if pd.isna(curr['SMA30W']) or pd.isna(last_complete['Vol_4W']):
                continue

            curr_price = curr['Close']
            curr_sma30 = curr['SMA30W']
            sma30_slope = curr['SMA30W_slope']
            last_vol = last_complete['Volume']        # 직전 완성 주봉 거래량
            avg_vol_4w = last_complete['Vol_4W']      # 직전 기준 4주 평균
            high_52w = curr['High_52W']

            # --- 4단계 판별 ---
            is_above_sma = curr_price > curr_sma30
            is_sma_rising = pd.notna(sma30_slope) and sma30_slope > 0
            vol_ratio = last_vol / avg_vol_4w if avg_vol_4w > 0 else 1
            is_vol_burst = vol_ratio >= 2.0  # 4주 평균의 2배
            pct_from_high = (curr_price / high_52w * 100) if pd.notna(high_52w) and high_52w > 0 else 0
            is_near_high = pct_from_high >= 75  # 52주 고가 대비 75% 이상

            # Stage 판별
            if is_above_sma and is_sma_rising:
                stage = 'Stage 2'
            elif is_above_sma and not is_sma_rising:
                stage = 'Stage 3'
            elif not is_above_sma and not is_sma_rising:
                stage = 'Stage 4'
            else:
                stage = 'Stage 1'

            # Stage 2만 매수 후보
            if stage != 'Stage 2':
                processed += 1
                continue

            # 상대강도 필터 (RSM > 0: 시장 대비 강함)
            rs_ok = (rsm is not None and rsm > 0) or (rsm is None)

            if not rs_ok:
                processed += 1
                continue

            # 신호 이유 구성
            reasons = []
            if is_vol_burst:
                reasons.append(f'Vol {vol_ratio:.1f}x 폭증')
            elif vol_ratio >= 1.3:
                reasons.append(f'Vol {vol_ratio:.1f}x')
            if is_near_high:
                reasons.append(f'52주고가 {pct_from_high:.0f}%')
            if rsm is not None and rsm > 0:
                reasons.append(f'RS+{rsm:.1f}')

            reason_str = ' | '.join(reasons) if reasons else 'Stage 2 유지'

            # Stage 2A: 돌파 격발 (거래량 2배 + 52주 고가 근접)
            if is_vol_burst and is_near_high:
                weinstein_signals.append({
                    'symbol': symbol,
                    'strategy': 'Weinstein',
                    'stage': 'Stage 2A (돌파)',
                    'price': curr_price,
                    'sma30w': curr_sma30,
                    'vol_ratio': vol_ratio,
                    'rsm': rsm if rsm else 0,
                    'pct_from_high': pct_from_high,
                    'reason': '30주선 돌파 격발 | ' + reason_str
                })
            # Stage 2: 상승 추세 유지 (52주 고가 근접)
            elif is_near_high:
                weinstein_signals.append({
                    'symbol': symbol,
                    'strategy': 'Weinstein',
                    'stage': 'Stage 2 (상승)',
                    'price': curr_price,
                    'sma30w': curr_sma30,
                    'vol_ratio': vol_ratio,
                    'rsm': rsm if rsm else 0,
                    'pct_from_high': pct_from_high,
                    'reason': 'Stage 2 상승 유지 | ' + reason_str
                })

            processed += 1
            if processed % 50 == 0:
                print(f"[미국 시장] 진행: {processed}/{len(all_symbols)} (W:{len(weinstein_signals)}, S:{len(sepa_signals)})")

        except Exception:
            skipped += 1
            continue

    print(f"[미국 시장] 완료 - Weinstein: {len(weinstein_signals)}개, SEPA: {len(sepa_signals)}개 (스킵: {skipped}개)")
    return weinstein_signals, sepa_signals


def screen_korean_all_strategies():
    """한국 시장 - K-Weinstein + K-SEPA 전략"""
    print("\n[한국 시장] 스크리닝 중...")

    try:
        import FinanceDataReader as fdr

        print("[한국 시장] 종목 리스트 로딩 중...")
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])]
        df_top = df_krx.nlargest(150, 'Marcap')

        symbols = []
        stock_names = {}

        for _, row in df_top.iterrows():
            code = row['Code']
            name = row['Name']
            market = row['Market']
            suffix = '.KS' if market == 'KOSPI' else '.KQ'
            symbol = f"{code}{suffix}"
            symbols.append(symbol)
            stock_names[symbol] = name

        kospi_cnt = len(df_top[df_top['Market'] == 'KOSPI'])
        kosdaq_cnt = len(df_top[df_top['Market'] == 'KOSDAQ'])
        print(f"[한국 시장] 시총 상위 150개 선택 (KOSPI: {kospi_cnt}, KOSDAQ: {kosdaq_cnt})")

    except Exception as e:
        print(f"[한국 시장] 종목 리스트 로딩 실패: {e}")
        symbols = []
        stock_names = {}

    loader = DataLoader(verbose=False)
    sepa_strategy = KMinerviniProStrategy()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)

    weinstein_signals = []
    sepa_signals = []
    processed = 0

    for symbol in symbols:
        try:
            data = loader.fetch_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if data.empty or len(data) < 120:
                continue

            name = stock_names.get(symbol, 'N/A')

            # K-SEPA 전략 (현재 시점 직접 체크)
            if len(data) >= 280:
                try:
                    df_ksepa = sepa_strategy.calculate_indicators(data)
                    idx_last = len(df_ksepa) - 1
                    signal = sepa_strategy.check_k_strike(df_ksepa, idx_last)
                    if signal and signal['type'] == 'BUY':
                        sepa_signals.append({
                            'symbol': symbol,
                            'name': name,
                            'strategy': 'K-SEPA',
                            'stage': 'STRIKE',
                            'price': signal['price'],
                            'confidence': signal.get('confidence', 0),
                            'vol_ratio': signal['metrics']['volume_ratio'],
                            'reason': signal.get('reason', '미너비니 VCP 돌파')
                        })
                    else:
                        tt_pass, _ = sepa_strategy.check_k_trend_template(df_ksepa, idx_last)
                        if tt_pass:
                            row = df_ksepa.iloc[idx_last]
                            vol_ratio = row['Volume'] / row['vol_avg_50'] if pd.notna(row['vol_avg_50']) and row['vol_avg_50'] > 0 else 0
                            sepa_signals.append({
                                'symbol': symbol,
                                'name': name,
                                'strategy': 'K-SEPA',
                                'stage': 'Setup 대기',
                                'price': row['Close'],
                                'confidence': 0.3,
                                'vol_ratio': vol_ratio,
                                'reason': 'TT통과 | VCP/돌파 대기'
                            })
                except Exception:
                    pass

            # K-Weinstein (120일 EMA)
            data['EMA120'] = data['Close'].ewm(span=120, adjust=False).mean()
            data['Vol_MA20'] = data['Volume'].rolling(window=20).mean()

            curr_price = data['Close'].iloc[-1]
            prev_price = data['Close'].iloc[-2]
            curr_ema = data['EMA120'].iloc[-1]
            prev_ema = data['EMA120'].iloc[-2]
            curr_vol = data['Volume'].iloc[-1]
            avg_vol = data['Vol_MA20'].iloc[-1]

            if pd.isna(avg_vol) or avg_vol <= 0:
                continue

            vol_ratio = curr_vol / avg_vol
            is_above_ema = curr_price > curr_ema
            is_breakout = is_above_ema and (prev_price <= prev_ema)
            is_ema_rising = curr_ema > prev_ema

            # 1) 돌파 신호 (거래량 2.5배 이상)
            if is_breakout and vol_ratio >= 2.5 and is_ema_rising:
                weinstein_signals.append({
                    'symbol': symbol,
                    'name': name,
                    'strategy': 'K-Weinstein',
                    'price': curr_price,
                    'vol_ratio': vol_ratio,
                    'status': '돌파',
                    'reason': 'EMA120 돌파 + 거래량 폭증'
                })
            # 2) Stage 2 유지 중 (거래량 1.3배 이상)
            elif is_above_ema and vol_ratio >= 1.3 and is_ema_rising:
                weinstein_signals.append({
                    'symbol': symbol,
                    'name': name,
                    'strategy': 'K-Weinstein',
                    'price': curr_price,
                    'vol_ratio': vol_ratio,
                    'status': 'Stage 2 유지',
                    'reason': 'EMA120 위 + 거래량 증가'
                })

            processed += 1
            if processed % 50 == 0:
                print(f"[한국 시장] 진행: {processed}/{len(symbols)}")

        except Exception:
            continue

    print(f"[한국 시장] 완료 - K-Weinstein: {len(weinstein_signals)}개, K-SEPA: {len(sepa_signals)}개")
    return weinstein_signals, sepa_signals


def merge_signals(weinstein, sepa, market_prefix=''):
    """Weinstein + SEPA 신호를 통합하고 정렬"""
    all_signals = []
    for s in sepa:
        all_signals.append({**s, 'sort_key': s.get('confidence', 0) + 10})  # SEPA 우선
    for s in weinstein:
        all_signals.append({**s, 'sort_key': s.get('vol_ratio', 0)})
    return sorted(all_signals, key=lambda x: x['sort_key'], reverse=True)


def send_to_telegram(us_all, kr_all):
    """텔레그램 전송 - 전략별 분리 + 풍부한 이모티콘"""
    notifier = get_notifier()

    if not notifier.enabled:
        print("\n[텔레그램] 설정되지 않음")
        return False

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    messages = []

    # ═══════════════════════════════════════
    # 1️⃣ 헤더 메시지
    # ═══════════════════════════════════════
    header = "🔔 *주식 스크리너 알림*\n"
    header += f"📅 {now_str}\n"
    header += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # 요약 카운트
    us_w = [s for s in us_all if s.get('strategy') == 'Weinstein']
    us_s = [s for s in us_all if s.get('strategy') == 'SEPA']
    kr_w = [s for s in kr_all if s.get('strategy') in ('K-Weinstein', 'Weinstein')]
    kr_s = [s for s in kr_all if s.get('strategy') == 'K-SEPA']

    us_s_strike = [s for s in us_s if s.get('stage') == 'STRIKE']
    us_s_setup = [s for s in us_s if s.get('stage') != 'STRIKE']
    kr_s_strike = [s for s in kr_s if s.get('stage') == 'STRIKE']
    kr_s_setup = [s for s in kr_s if s.get('stage') != 'STRIKE']

    header += "📊 *오늘의 스크리닝 요약*\n\n"
    header += f"🇺🇸 *미국* — 총 {len(us_all)}개\n"
    header += f"  📈 Weinstein Stage 2: {len(us_w)}개\n"
    if us_s_strike:
        header += f"  🚀 SEPA STRIKE: {len(us_s_strike)}개\n"
    header += f"  🎯 SEPA Setup 대기: {len(us_s_setup)}개\n\n"

    header += f"🇰🇷 *한국* — 총 {len(kr_all)}개\n"
    header += f"  📈 K-Weinstein: {len(kr_w)}개\n"
    if kr_s_strike:
        header += f"  🚀 K-SEPA STRIKE: {len(kr_s_strike)}개\n"
    header += f"  🎯 K-SEPA Setup 대기: {len(kr_s_setup)}개\n"

    messages.append(header)

    # ═══════════════════════════════════════
    # 2️⃣ 미국 SEPA STRIKE (있으면 최우선)
    # ═══════════════════════════════════════
    if us_s_strike:
        msg = "🚀 *미국 SEPA STRIKE — 즉시 매수 후보*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, s in enumerate(us_s_strike[:10], 1):
            msg += f"🔥 *{i}. {s['symbol']}* — ${s['price']:.2f}\n"
            msg += f"   💥 Vol: {s.get('vol_ratio', 0):.1f}x | {s.get('reason', '')}\n\n"
        messages.append(msg)

    # ═══════════════════════════════════════
    # 3️⃣ 미국 Weinstein Stage 2 (상위 15개)
    # ═══════════════════════════════════════
    if us_w:
        msg = "📈 *미국 Weinstein Stage 2 — 상승 추세*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Stage 2A (돌파) 우선
        us_w_2a = [s for s in us_w if '2A' in str(s.get('stage', ''))]
        us_w_2 = [s for s in us_w if '2A' not in str(s.get('stage', ''))]

        if us_w_2a:
            msg += "🔴 *Stage 2A (돌파 격발)*\n"
            for s in us_w_2a[:5]:
                rsm = s.get('rsm', 0)
                rs_icon = "💪" if rsm > 5 else "📊"
                msg += f"  ⚡ *{s['symbol']}* ${s['price']:.2f}"
                msg += f" | Vol:{s.get('vol_ratio', 0):.1f}x"
                msg += f" | {rs_icon} RS:{rsm:+.1f}\n"
            msg += "\n"

        msg += "🟢 *Stage 2 (상승 유지)* — 상위 10개\n"
        for s in us_w_2[:10]:
            pct = s.get('pct_from_high', 0)
            rsm = s.get('rsm', 0)
            # 52주 고가 근접도 아이콘
            if pct >= 95:
                hi_icon = "🏆"
            elif pct >= 90:
                hi_icon = "🔝"
            else:
                hi_icon = "📍"
            msg += f"  {hi_icon} *{s['symbol']}* ${s['price']:.2f}"
            msg += f" | {pct:.0f}%고가"
            if rsm > 0:
                msg += f" | RS:+{rsm:.0f}"
            msg += "\n"

        if len(us_w) > 15:
            msg += f"\n_...외 {len(us_w) - 15}개 (CSV 참고)_\n"

        messages.append(msg)

    # ═══════════════════════════════════════
    # 4️⃣ 미국 SEPA Setup 대기 (상위 15개)
    # ═══════════════════════════════════════
    if us_s_setup:
        msg = "🎯 *미국 SEPA Setup 대기 — TT 통과*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += "_트렌드 템플릿 8조건 통과, VCP 형성 대기_\n\n"

        for i, s in enumerate(us_s_setup[:15], 1):
            msg += f"  🔹 *{s['symbol']}* ${s['price']:.2f}\n"

        if len(us_s_setup) > 15:
            msg += f"\n_...외 {len(us_s_setup) - 15}개_\n"

        messages.append(msg)

    # ═══════════════════════════════════════
    # 5️⃣ 한국 SEPA STRIKE (있으면)
    # ═══════════════════════════════════════
    if kr_s_strike:
        msg = "🚀 *한국 K-SEPA STRIKE — 즉시 매수 후보*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, s in enumerate(kr_s_strike[:10], 1):
            name = s.get('name', '')
            msg += f"🔥 *{i}. {s['symbol']}* {name}\n"
            msg += f"   {s['price']:,.0f}원 | Vol:{s.get('vol_ratio', 0):.1f}x\n"
            msg += f"   {s.get('reason', '')}\n\n"
        messages.append(msg)

    # ═══════════════════════════════════════
    # 6️⃣ 한국 K-Weinstein (상위 15개)
    # ═══════════════════════════════════════
    if kr_w:
        msg = "📈 *한국 K-Weinstein — 상승 추세*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, s in enumerate(kr_w[:15], 1):
            name = s.get('name', '')
            status = s.get('status', '')
            # 상태별 아이콘
            if '돌파' in status or '골든' in status:
                icon = "⚡"
            elif '상승' in status:
                icon = "🟢"
            else:
                icon = "📊"
            msg += f"  {icon} *{s['symbol']}* {name}\n"
            msg += f"     {s['price']:,.0f}원 | Vol:{s.get('vol_ratio', 0):.1f}x | {status}\n"

        if len(kr_w) > 15:
            msg += f"\n_...외 {len(kr_w) - 15}개 (CSV 참고)_\n"

        messages.append(msg)

    # ═══════════════════════════════════════
    # 7️⃣ 한국 K-SEPA Setup 대기 (상위 15개)
    # ═══════════════════════════════════════
    if kr_s_setup:
        msg = "🎯 *한국 K-SEPA Setup 대기 — TT 통과*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, s in enumerate(kr_s_setup[:15], 1):
            name = s.get('name', '')
            msg += f"  🔹 *{s['symbol']}* {name} — {s['price']:,.0f}원\n"

        if len(kr_s_setup) > 15:
            msg += f"\n_...외 {len(kr_s_setup) - 15}개_\n"

        messages.append(msg)

    # ═══════════════════════════════════════
    # 8️⃣ 푸터
    # ═══════════════════════════════════════
    footer = "━━━━━━━━━━━━━━━━━━━━\n"
    footer += "📌 *전략 가이드*\n\n"
    footer += "📈 *Weinstein* — 30주선 기반 추세 추종\n"
    footer += "  ⚡ Stage 2A: 돌파 격발 (강매수)\n"
    footer += "  🟢 Stage 2: 상승 추세 유지\n\n"
    footer += "🎯 *SEPA* — 미너비니 슈퍼퍼포머 발굴\n"
    footer += "  🚀 STRIKE: VCP 돌파+거래량 (즉시 진입)\n"
    footer += "  🔹 Setup: TT 통과, 돌파 대기 (관찰)\n\n"
    footer += "⚠️ _본 알림은 투자 권유가 아닙니다_\n"
    footer += f"🕐 _{now_str} 기준_"
    messages.append(footer)

    # ═══════════════════════════════════════
    # 전송 (하나의 이벤트 루프로 일괄 전송)
    # ═══════════════════════════════════════
    success_count = notifier.send_multiple_sync(messages)

    if success_count == len(messages):
        print(f"\n[OK] 텔레그램 전송 성공! ({len(messages)}개 메시지)")
        return True
    else:
        print(f"\n[WARN] 텔레그램 {success_count}/{len(messages)}개 메시지 전송")
        return success_count > 0


def save_results(signals, filename):
    """결과를 CSV로 저장"""
    if not signals:
        return
    df = pd.DataFrame(signals)
    # sort_key 컬럼 제거
    if 'sort_key' in df.columns:
        df = df.drop(columns=['sort_key'])
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"[저장] {filename} ({len(signals)}개)")


def main():
    print("\n" + "="*70)
    print("통합 스크리너 v2 - Weinstein + Minervini")
    print("="*70)
    start_time = datetime.now()
    print(f"시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # 1. 미국 시장 스크리닝
        us_weinstein, us_sepa = screen_us_all_strategies()

        # 2. 한국 시장 스크리닝
        kr_weinstein, kr_sepa = screen_korean_all_strategies()

        # 3. 통합 및 정렬
        us_all = merge_signals(us_weinstein, us_sepa)
        kr_all = merge_signals(kr_weinstein, kr_sepa)

        # 4. 결과 출력
        print("\n" + "="*70)
        print("스크리닝 완료!")
        print("="*70)
        print(f"미국: Weinstein {len(us_weinstein)}개, SEPA {len(us_sepa)}개 = 총 {len(us_all)}개")
        print(f"한국: K-Weinstein {len(kr_weinstein)}개, K-SEPA {len(kr_sepa)}개 = 총 {len(kr_all)}개")
        print(f"전체: {len(us_all) + len(kr_all)}개")

        # 5. 텔레그램 전송
        print("\n텔레그램 전송 중...")
        send_to_telegram(us_all, kr_all)

        # 6. CSV 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_results(us_all, f'full_us_{timestamp}.csv')
        save_results(kr_all, f'full_kr_{timestamp}.csv')

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (소요: {elapsed:.0f}초)")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
