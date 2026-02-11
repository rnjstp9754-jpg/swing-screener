#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
통합 스크리너 - 4개 전략 병렬 실행
- 미국 시장: Weinstein Stage, Aggressive SEPA
- 한국 시장: K-Weinstein, K-SEPA (Minervini Pro)
"""

import sys
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from src.data_loader import DataLoader
from src.market_universe import load_nasdaq100, load_sp500, get_korean_market_symbols
from strategies.weinstein_stage import WeinsteinStageStrategy
from strategies.sepa_minervini import AggressiveSEPAStrategy
from strategies.k_sepa import KMinerviniProStrategy
from src.telegram_notifier import get_notifier


def screen_us_weinstein(max_results=50):
    """미국 시장 - Weinstein Stage 스크리닝"""
    print("\n[US-Weinstein] Starting...")
    
    try:
        # NASDAQ-100 + S&P 500
        nasdaq_symbols = load_nasdaq100()
        sp500_symbols = load_sp500()
        all_symbols = list(set(nasdaq_symbols + sp500_symbols))
        
        print(f"[US-Weinstein] Screening {len(all_symbols)} stocks...")
        
        strategy = WeinsteinStageStrategy()
        loader = DataLoader(verbose=False)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        signals = []
        
        for symbol in all_symbols:
            try:
                data = loader.fetch_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if data.empty or len(data) < 30:
                    continue
                
                stock_signals = strategy.generate_signals(data)
                buy_signals = [s for s in stock_signals if s['type'] == 'BUY']
                
                if buy_signals:
                    for signal in buy_signals:
                        signals.append({
                            **signal,
                            'symbol': symbol,
                            'market': 'US'
                        })
            except Exception as e:
                continue
        
        # 날짜순 정렬 후 최대 개수 제한
        signals = sorted(signals, key=lambda x: x.get('date', ''), reverse=True)[:max_results]
        
        print(f"[US-Weinstein] Complete! Found {len(signals)} signals")
        return {'strategy': 'US-Weinstein', 'signals': signals}
    
    except Exception as e:
        print(f"[US-Weinstein] ERROR: {e}")
        return {'strategy': 'US-Weinstein', 'signals': []}


def screen_us_sepa(max_results=30):
    """미국 시장 - Aggressive SEPA 스크리닝"""
    print("\n[US-SEPA] Starting...")
    
    try:
        nasdaq_symbols = load_nasdaq100()[:50]  # 시간 절약을 위해 상위 50개만
        
        print(f"[US-SEPA] Screening {len(nasdaq_symbols)} growth stocks...")
        
        strategy = AggressiveSEPAStrategy()
        loader = DataLoader(verbose=False)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2년
        
        signals = []
        
        for symbol in nasdaq_symbols:
            try:
                data = loader.fetch_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if data.empty or len(data) < 200:
                    continue
                
                stock_signals = strategy.generate_signals(data)
                buy_signals = [s for s in stock_signals if s['type'] == 'BUY']
                
                if buy_signals:
                    for signal in buy_signals:
                        signals.append({
                            **signal,
                            'symbol': symbol,
                            'market': 'US'
                        })
            except Exception as e:
                continue
        
        # Confidence로 정렬 후 제한
        signals = sorted(signals, key=lambda x: x.get('confidence', 0), reverse=True)[:max_results]
        
        print(f"[US-SEPA] Complete! Found {len(signals)} signals")
        return {'strategy': 'US-SEPA', 'signals': signals}
    
    except Exception as e:
        print(f"[US-SEPA] ERROR: {e}")
        return {'strategy': 'US-SEPA', 'signals': []}


def screen_korean_weinstein(max_results=150):
    """한국 시장 - K-Weinstein 스크리닝"""
    print("\n[K-Weinstein] Starting...")
    
    try:
        # 한국 주요 종목 (시간 절약)
        symbols = get_korean_market_symbols(max_symbols=300)  # 상위 300개만
        
        print(f"[K-Weinstein] Screening {len(symbols)} stocks...")
        
        loader = DataLoader(verbose=False)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=250)
        
        signals = []
        
        for symbol in symbols:
            try:
                data = loader.fetch_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if data.empty or len(data) < 120:
                    continue
                
                # EMA120 계산
                data['EMA120'] = data['Close'].ewm(span=120, adjust=False).mean()
                data['Vol_MA20'] = data['Volume'].rolling(window=20).mean()
                
                curr_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2]
                curr_ema = data['EMA120'].iloc[-1]
                prev_ema = data['EMA120'].iloc[-2]
                curr_vol = data['Volume'].iloc[-1]
                avg_vol = data['Vol_MA20'].iloc[-1]
                
                # Stage 2 진입 확인
                is_breakout = (curr_price > curr_ema) and (prev_price <= prev_ema)
                is_volume_surge = curr_vol > avg_vol * 3
                is_ema_rising = curr_ema > prev_ema
                
                if is_breakout and is_volume_surge and is_ema_rising:
                    signals.append({
                        'symbol': symbol,
                        'price': curr_price,
                        'ema120': curr_ema,
                        'vol_ratio': curr_vol / avg_vol,
                        'market': 'KR',
                        'date': data.index[-1]
                    })
            
            except Exception as e:
                continue
        
        # 거래량 비율로 정렬 후 제한
        signals = sorted(signals, key=lambda x: x.get('vol_ratio', 0), reverse=True)[:max_results]
        
        print(f"[K-Weinstein] Complete! Found {len(signals)} signals")
        return {'strategy': 'K-Weinstein', 'signals': signals}
    
    except Exception as e:
        print(f"[K-Weinstein] ERROR: {e}")
        return {'strategy': 'K-Weinstein', 'signals': []}


def screen_korean_sepa(max_results=150):
    """한국 시장 - K-SEPA (Minervini Pro) 스크리닝"""
    print("\n[K-SEPA] Starting...")
    
    try:
        # 한국 대형주 위주
        symbols = get_korean_market_symbols(max_symbols=200)
        
        print(f"[K-SEPA] Screening {len(symbols)} stocks...")
        
        strategy = KMinerviniProStrategy()
        loader = DataLoader(verbose=False)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        
        signals = []
        
        for symbol in symbols:
            try:
                data = loader.fetch_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if data.empty or len(data) < 240:
                    continue
                
                stock_signals = strategy.generate_signals(data)
                buy_signals = [s for s in stock_signals if s['type'] == 'BUY']
                
                if buy_signals:
                    for signal in buy_signals:
                        signals.append({
                            **signal,
                            'symbol': symbol,
                            'market': 'KR'
                        })
            
            except Exception as e:
                continue
        
        # Confidence로 정렬 후 제한
        signals = sorted(signals, key=lambda x: x.get('confidence', 0), reverse=True)[:max_results]
        
        print(f"[K-SEPA] Complete! Found {len(signals)} signals")
        return {'strategy': 'K-SEPA', 'signals': signals}
    
    except Exception as e:
        print(f"[K-SEPA] ERROR: {e}")
        return {'strategy': 'K-SEPA', 'signals': []}


def send_telegram_summary(results):
    """텔레그램으로 전체 결과 요약 전송"""
    notifier = get_notifier()
    
    if not notifier.enabled:
        print("\n[Telegram] Not configured. Skipping notification.")
        return False
    
    message = "📊 *All Strategies Screening Results*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for result in results:
        strategy = result['strategy']
        signals = result['signals']
        
        if strategy == 'US-Weinstein':
            message += f"🇺🇸 *Weinstein Stage* ({len(signals)} signals)\n\n"
            for i, s in enumerate(signals[:5], 1):
                message += f"{i}. *{s['symbol']}* - ${s.get('price', 0):.2f}\n"
            if len(signals) > 5:
                message += f"_...and {len(signals) - 5} more_\n"
            message += "\n"
        
        elif strategy == 'US-SEPA':
            message += f"🇺🇸 *Aggressive SEPA* ({len(signals)} signals)\n\n"
            for i, s in enumerate(signals[:5], 1):
                message += f"{i}. *{s['symbol']}* - ${s.get('price', 0):.2f} (C: {s.get('confidence', 0):.2f})\n"
            if len(signals) > 5:
                message += f"_...and {len(signals) - 5} more_\n"
            message += "\n"
        
        elif strategy == 'K-Weinstein':
            message += f"🇰🇷 *K-Weinstein* ({len(signals)} signals)\n\n"
            for i, s in enumerate(signals[:5], 1):
                message += f"{i}. *{s['symbol']}* - {s.get('price', 0):,.0f}원 (Vol: {s.get('vol_ratio', 0):.1f}x)\n"
            if len(signals) > 5:
                message += f"_...and {len(signals) - 5} more_\n"
            message += "\n"
        
        elif strategy == 'K-SEPA':
            message += f"🇰🇷 *K-SEPA (Minervini Pro)* ({len(signals)} signals)\n\n"
            for i, s in enumerate(signals[:5], 1):
                message += f"{i}. *{s['symbol']}* - {s.get('price', 0):,.0f}원 (C: {s.get('confidence', 0):.2f})\n"
            if len(signals) > 5:
                message += f"_...and {len(signals) - 5} more_\n"
            message += "\n"
    
    # 총 요약
    total_signals = sum(len(r['signals']) for r in results)
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📈 *Total: {total_signals} signals*"
    
    if notifier.send_sync(message):
        print("[OK] Results sent to Telegram!")
        return True
    else:
        print("[FAIL] Failed to send to Telegram")
        return False


def main():
    print("\n" + "="*80)
    print("통합 스크리너 - 4개 전략 병렬 실행")
    print("="*80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 병렬 실행 (최대 4개 워커)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(screen_us_weinstein): 'US-Weinstein',
            executor.submit(screen_us_sepa): 'US-SEPA',
            executor.submit(screen_korean_weinstein): 'K-Weinstein',
            executor.submit(screen_korean_sepa): 'K-SEPA'
        }
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            strategy_name = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✅ {strategy_name} completed")
            except Exception as e:
                print(f"❌ {strategy_name} failed: {e}")
                results.append({'strategy': strategy_name, 'signals': []})
    
    # 결과 요약
    print("\n" + "="*80)
    print("스크리닝 완료!")
    print("="*80)
    
    for result in results:
        print(f"{result['strategy']}: {len(result['signals'])} signals")
    
    total = sum(len(r['signals']) for r in results)
    print(f"\n총 신호: {total}개")
    
    # 텔레그램 전송
    print("\n텔레그램 전송 중...")
    send_telegram_summary(results)
    
    print(f"\n완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # CSV 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for result in results:
        if result['signals']:
            df = pd.DataFrame(result['signals'])
            filename = f"results_{result['strategy'].lower().replace('-', '_')}_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"[SAVED] {filename}")


if __name__ == "__main__":
    main()
