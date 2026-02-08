#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
실전 스크리너 - SEPA & Weinstein 전략 테스트

최근 6개월 데이터로 나스닥/러셀 종목 스크리닝
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

from src.market_universe import MarketUniverse
from src.data_loader import DataLoader
# from strategies.sepa_minervini import SEPAStrategy
from strategies.weinstein_stage import WeinsteinStrategy


def screen_market(market_name: str, strategies: list, months: int = 6):
    """
    시장 전체 스크리닝
    
    Args:
        market_name: 시장 이름 (NASDAQ100, RUSSELL2000 등)
        strategies: 전략 리스트
        months: 데이터 기간 (개월)
    """
    print("\n" + "="*80)
    print(f"Market Screening: {market_name}")
    print("="*80)
    
    # 종목 리스트 로드
    universe = MarketUniverse()
    symbols = universe.get_universe(market_name)
    
    print(f"\nTotal Symbols: {len(symbols)}")
    print(f"Period: Last {months} months")
    print(f"Strategies: {', '.join([s.name for s in strategies])}")
    print()
    
    # 날짜 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # 데이터 로더
    loader = DataLoader()
    
    # 각 전략별 결과
    all_results = {strategy.name: [] for strategy in strategies}
    
    # 종목별 스크리닝
    print(f"\n{'Symbol':<10} {'Name':<30} {'Status'}")
    print("-" * 80)
    
    success_count = 0
    error_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        try:
            # 데이터 로드
            data = loader.fetch_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if data.empty or len(data) < 50:
                print(f"{symbol:<10} {'N/A':<30} [SKIP] Insufficient data")
                error_count += 1
                continue
            
            # 각 전략 테스트
            signals_found = []
            
            for strategy in strategies:
                signals = strategy.generate_signals(data)
                
                if signals:
                    buy_signals = [s for s in signals if s['type'] == 'BUY']
                    if buy_signals:
                        signals_found.append(strategy.name)
                        all_results[strategy.name].append({
                            'symbol': symbol,
                            'signals': len(buy_signals),
                            'latest_signal': buy_signals[-1]
                        })
            
            # 결과 출력
            if signals_found:
                status = f"[SIGNAL] {', '.join(signals_found)}"
                print(f"{symbol:<10} {'':<30} {status}")
            else:
                status = "[OK] No signals"
                print(f"{symbol:<10} {'':<30} {status}")
            
            success_count += 1
            
        except Exception as e:
            print(f"{symbol:<10} {'':<30} [ERROR] {str(e)[:40]}")
            error_count += 1
            continue
    
    # 결과 요약
    print("\n" + "="*80)
    print("Screening Results Summary")
    print("="*80)
    print(f"Total Processed: {success_count + error_count}")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    print()
    
    # 전략별 신호 요약
    for strategy_name, results in all_results.items():
        print(f"\n[{strategy_name}] - {len(results)} signals")
        
        if results:
            print(f"{'Symbol':<10} {'Signals':<10} {'Latest Date':<15} {'Price':<12} {'Reason'}")
            print("-" * 80)
            
            for r in results[:20]:  # 상위 20개만 출력
                latest = r['latest_signal']
                print(f"{r['symbol']:<10} {r['signals']:<10} "
                      f"{str(latest['date'])[:10]:<15} "
                      f"${latest['price']:<11.2f} "
                      f"{latest['reason'][:40]}")
    
    print("\n" + "="*80)
    
    return all_results


def main():
    """메인 실행"""
    print("\n" + "="*80)
    print("Real Stock Screener - Weinstein Stage Analysis")
    print("Markets: NASDAQ-100 & S&P 500")
    print("="*80)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 전략 초기화 (Weinstein만 사용)
    strategies = [
        WeinsteinStrategy()
    ]
    
    # 테스트할 시장 (NASDAQ & S&P500)
    markets = ['NASDAQ100', 'SP500']
    
    all_market_results = {}
    
    for market in markets:
        try:
            results = screen_market(market, strategies, months=12)
            all_market_results[market] = results
        except Exception as e:
            print(f"\n[ERROR] Market {market} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # 최종 요약
    print("\n" + "="*80)
    print("Final Summary")
    print("="*80)
    
    for market, results in all_market_results.items():
        print(f"\n{market}:")
        for strategy_name, signals in results.items():
            print(f"  {strategy_name}: {len(signals)} signals")
    
    print("\n" + "="*80)
    print("Screening Complete!")
    print("="*80 + "\n")
    
    # 텔레그램 알림 전송
    try:
        from src.telegram_notifier import get_notifier
        
        notifier = get_notifier()
        
        if notifier.enabled:
            print("\n[Telegram] Sending notifications...")
            
            for market, results in all_market_results.items():
                for strategy_name, signals in results.items():
                    if signals:
                        message = notifier.format_screening_results(
                            market=market,
                            strategy=strategy_name,
                            buy_signals=signals,
                            max_results=10
                        )
                        if notifier.send_sync(message):
                            print(f"[OK] Sent {market} - {strategy_name} ({len(signals)} signals)")
                        else:
                            print(f"[FAIL] Failed to send {market} - {strategy_name}")
            
            print("[Telegram] Notifications complete!\n")
        else:
            print("\n[Telegram] Not configured (skipped)\n")
    
    except Exception as e:
        print(f"\n[ERROR] Telegram notification failed: {e}\n")


if __name__ == "__main__":
    main()
