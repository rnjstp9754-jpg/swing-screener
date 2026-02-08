#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Screener Test
빠른 스크리닝 테스트 (소수 종목)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

from src.market_universe import MarketUniverse
from src.data_loader import DataLoader
from strategies.weinstein_stage import WeinsteinStrategy
from src.telegram_notifier import get_notifier


def quick_test():
    """빠른 테스트 - 10개 종목만"""
    print("\n" + "="*80)
    print("Quick Screener Test - Weinstein Stage")
    print("Testing with 10 stocks only")
    print("="*80)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 소수 종목만 테스트
    test_symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
        'TSLA', 'META', 'NFLX', 'AVGO', 'CSCO'
    ]
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1년
    
    # 데이터 로더 & 전략
    loader = DataLoader()
    strategy = WeinsteinStrategy()
    
    # 결과 저장
    buy_signals = []
    
    print(f"Testing {len(test_symbols)} stocks...\n")
    print(f"{'Symbol':<10} {'Status'}")
    print("-" * 80)
    
    for symbol in test_symbols:
        try:
            # 데이터 로드
            data = loader.fetch_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if data.empty or len(data) < 50:
                print(f"{symbol:<10} [SKIP] Insufficient data")
                continue
            
            # 신호 생성
            signals = strategy.generate_signals(data)
            
            if signals:
                # 매수 신호만 필터링
                buy_sigs = [s for s in signals if s['type'] == 'BUY']
                if buy_sigs:
                    buy_signals.append({
                        'symbol': symbol,
                        'signals': len(buy_sigs),
                        'latest_signal': buy_sigs[-1]
                    })
                    print(f"{symbol:<10} [SIGNAL] {len(buy_sigs)} buy signals found")
                else:
                    print(f"{symbol:<10} [OK] No buy signals")
            else:
                print(f"{symbol:<10} [OK] No signals")
        
        except Exception as e:
            print(f"{symbol:<10} [ERROR] {str(e)[:40]}")
            continue
    
    # 결과 요약
    print("\n" + "="*80)
    print("Test Results")
    print("="*80)
    print(f"Total Buy Signals: {len(buy_signals)}\n")
    
    if buy_signals:
        print(f"{'Symbol':<10} {'Signals':<10} {'Latest Date':<15} {'Price':<12}")
        print("-" * 80)
        
        for result in buy_signals:
            latest = result['latest_signal']
            print(f"{result['symbol']:<10} {result['signals']:<10} "
                  f"{str(latest['date'])[:10]:<15} "
                  f"${latest['price']:<11.2f}")
    
    print("\n" + "="*80)
    
    # 텔레그램 알림 전송
    try:
        notifier = get_notifier()
        
        if notifier.enabled:
            print("\n[Telegram] Sending test notification...")
            
            # 신호가 없으면 테스트 메시지
            if not buy_signals:
                message = "🧪 *스크리너 테스트 완료*\n\n"
                message += f"📊 테스트 종목: {len(test_symbols)}개\n"
                message += "📈 매수 신호: 0개\n\n"
                message += "_신호가 발견되지 않았습니다._"
                
                if notifier.send_sync(message):
                    print("[OK] Test message sent!")
                else:
                    print("[FAIL] Failed to send message")
            else:
                # 실제 신호가 있으면 포맷팅해서 전송
                message = notifier.format_screening_results(
                    market="NASDAQ (Test)",
                    strategy="Weinstein Stage",
                    buy_signals=[{
                        'symbol': r['symbol'],
                        'price': r['latest_signal']['price'],
                        'volume_ratio': 2.5,  # 예시
                        'reason': r['latest_signal'].get('reason', 'Stage 2 Entry')
                    } for r in buy_signals],
                    max_results=10
                )
                
                if notifier.send_sync(message):
                    print(f"[OK] Sent {len(buy_signals)} signals to Telegram!")
                else:
                    print("[FAIL] Failed to send message")
            
            print("[Telegram] Complete!\n")
        else:
            print("\n[Telegram] Not configured (skipped)\n")
    
    except Exception as e:
        print(f"\n[ERROR] Telegram notification failed: {e}\n")
    
    print("="*80)
    print("Test Complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    quick_test()
