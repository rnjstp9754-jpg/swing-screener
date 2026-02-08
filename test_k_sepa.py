#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
K-SEPA Strategy Tester (Relaxed Version)
한국형 SEPA 전략 테스트 (완화 버전)
"""

import sys
from datetime import datetime, timedelta
import pandas as pd

from src.data_loader import DataLoader
from strategies.k_sepa import KMinerviniProStrategy


def test_k_sepa_relaxed():
    """K-SEPA 전략 테스트 (완화 조건)"""
    
    print("\n" + "="*80)
    print("K-SEPA Strategy Test (Relaxed Parameters)")
    print("="*80)
    
    # 테스트할 한국 종목
    korean_stocks = [
        '005930.KS',  # 삼성전자
        '000660.KS',  # SK하이닉스
        '035420.KS',  # NAVER
        '035720.KS',  # 카카오
        '051910.KS',  # LG화학
        '006400.KS',  # 삼성SDI
        '207940.KS',  # 삼성바이오로직스
        '068270.KS',  # 셀트리온
        '005380.KS',  # 현대차
        '105560.KS',  # KB금융
        '003670.KS',  # 포스코퓨처엠
        '373220.KS',  # LG에너지솔루션
        '066570.KS',  # LG전자
        '012330.KS',  # 현대모비스
        '000270.KS',  # 기아
    ]
    
    # 날짜 설정 (24개월)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    print(f"\nTest Period: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"Stocks: {len(korean_stocks)} Korean stocks")
    
    # 완화된 파라미터
    relaxed_params = {
        'volume_surge': 2.0,          # 3.0 -> 2.0 (200% 폭증으로 완화)
        'volume_dry_up': 0.4,         # 0.3 -> 0.4 (40% 이하로 완화)
        'new_high_threshold': 0.30,   # 0.25 -> 0.30 (-30% 이내로 완화)
    }
    
    print("\nRelaxed Parameters:")
    print(f"  - Volume Surge: 2.0x (200%) [Original: 3.0x]")
    print(f"  - Volume Dry-up: 40% [Original: 30%]")
    print(f"  - New High Range: -30% [Original: -25%]")
    print()
    
    # 데이터 로더 & 전략
    loader = DataLoader(verbose=False)
    strategy = KMinerviniProStrategy(params=relaxed_params)
    
    # 결과 저장
    all_signals = []
    
    print(f"{'Symbol':<15} {'Name':<20} {'Status'}")
    print("-" * 80)
    
    for symbol in korean_stocks:
        try:
            # 데이터 로드
            data = loader.fetch_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if data.empty or len(data) < 240:
                print(f"{symbol:<15} {'N/A':<20} [SKIP] Need 240+ days")
                continue
            
            # 전략 실행
            signals = strategy.generate_signals(data)
            
            # 매수 신호만 필터
            buy_signals = [s for s in signals if s['type'] == 'BUY']
            watch_signals = [s for s in signals if s.get('type') == 'WATCH']
            
            if buy_signals:
                all_signals.extend([{**s, 'symbol': symbol} for s in buy_signals])
                print(f"{symbol:<15} {'':<20} [SIGNAL] {len(buy_signals)} K-STRIKE")
            elif watch_signals:
                print(f"{symbol:<15} {'':<20} [WATCH] VCP Ready")
            else:
                print(f"{symbol:<15} {'':<20} [OK] No signals")
        
        except Exception as e:
            print(f"{symbol:<15} {'':<20} [ERROR] {str(e)[:40]}")
            import traceback
            traceback.print_exc()
            continue
    
    # 결과 요약
    print("\n" + "="*80)
    print("K-SEPA Test Results (Relaxed)")
    print("="*80)
    
    if all_signals:
        print(f"\nTotal Signals: {len(all_signals)}")
        print()
        print(f"{'Symbol':<12} {'Date':<12} {'Price':<10} {'Stop':<10} {'Target':<10} {'Confidence':<12} {'Reason'}")
        print("-" * 100)
        
        for signal in sorted(all_signals, key=lambda x: x['date'], reverse=True):
            print(f"{signal['symbol']:<12} "
                  f"{str(signal['date'])[:10]:<12} "
                  f"{signal['price']:<10.0f} "
                  f"{signal['stop_loss']:<10.0f} "
                  f"{signal['take_profit']:<10.0f} "
                  f"{signal['confidence']:<12.2f} "
                  f"{signal['reason'][:40]}")
        
        # 통계
        print("\n" + "="*80)
        print("Statistics")
        print("="*80)
        
        avg_confidence = sum(s['confidence'] for s in all_signals) / len(all_signals)
        print(f"Average Confidence: {avg_confidence:.2f}")
        
        # 거래량 비율
        vol_ratios = [s['metrics']['volume_ratio'] for s in all_signals]
        avg_vol_ratio = sum(vol_ratios) / len(vol_ratios)
        max_vol_ratio = max(vol_ratios)
        min_vol_ratio = min(vol_ratios)
        
        print(f"Volume Surge - Avg: {avg_vol_ratio:.1f}x, Max: {max_vol_ratio:.1f}x, Min: {min_vol_ratio:.1f}x")
        
    else:
        print("\nNo K-STRIKE signals found even with relaxed parameters.")
        print("\nThis suggests:")
        print("  1. Korean market is in consolidation/downtrend phase")
        print("  2. Major stocks are not showing VCP patterns")
        print("  3. Trend template requirements (SMA alignment) not met")
        print("\nRecommendation:")
        print("  - Wait for market to form new uptrend")
        print("  - Focus on Weinstein Stage analysis for trend detection")
        print("  - Monitor for VCP WATCH signals as leading indicators")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    test_k_sepa_relaxed()
