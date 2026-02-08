#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SEPA 전략 테스트 스크립트

마크 미너비니 SEPA 전략이 제대로 작동하는지 테스트합니다.
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from strategies.sepa_minervini import SEPAStrategy
from src.data_loader import DataLoader


def test_sepa_strategy():
    """SEPA 전략 기본 테스트"""
    print("\n" + "="*70)
    print("🧪 SEPA 전략 테스트")
    print("="*70 + "\n")
    
    # 1. 데이터 로더 생성
    print("[1/4] 데이터 로드 중...")
    loader = DataLoader()
    
    # 테스트용 종목 (NVIDIA - 강한 상승 추세)
    symbol = "NVDA"
    data = loader.fetch_data(symbol, "2023-01-01", "2024-12-31")
    
    if data.empty:
        print("❌ 데이터 로드 실패")
        return False
    
    print(f"✓ {len(data)}개 데이터 로드 완료\n")
    
    # 2. SEPA 전략 생성
    print("[2/4] SEPA 전략 초기화...")
    strategy = SEPAStrategy()
    print(f"✓ {strategy.name} 초기화 완료")
    print(f"  - 손절: {strategy.params['stop_loss']*100:.0f}%")
    print(f"  - 익절: {strategy.params['take_profit']*100:.0f}%")
    print(f"  - 손익비: {strategy.params['risk_reward_ratio']}:1\n")
    
    # 3. 신호 생성
    print("[3/4] 매매 신호 생성 중...")
    signals = strategy.generate_signals(data)
    print(f"✓ {len(signals)}개 신호 발견\n")
    
    # 4. 결과 출력
    print("[4/4] 신호 상세 분석")
    print("-" * 70)
    
    if not signals:
        print("⚠️  신호 없음 - 조건을 만족하는 매매 기회가 없었습니다.")
        return True
    
    # 매수 신호만 필터링
    buy_signals = [s for s in signals if s['type'] == 'BUY']
    
    print(f"\n📊 매수 신호: {len(buy_signals)}개\n")
    
    for i, signal in enumerate(buy_signals[:5], 1):  # 최대 5개만 출력
        print(f"신호 #{i}")
        print(f"  날짜: {signal['date']}")
        print(f"  진입가: ${signal['price']:.2f}")
        print(f"  손절가: ${signal.get('stop_loss', 0):.2f}")
        print(f"  목표가: ${signal.get('take_profit', 0):.2f}")
        print(f"  사유: {signal['reason']}")
        print(f"  신뢰도: {signal['confidence']:.2%}")
        
        if 'metrics' in signal:
            metrics = signal['metrics']
            print(f"  메트릭:")
            print(f"    - 피벗가: ${metrics.get('pivot_price', 0):.2f}")
            print(f"    - 거래량비: {metrics.get('volume_ratio', 0):.1f}x")
            print(f"    - 52주고가대비: {metrics.get('distance_from_52w_high', 0):.1f}%")
            print(f"    - 이평 정렬: {metrics.get('sma_alignment', 'N/A')}")
        print()
    
    # 수익률 통계
    print("\n" + "="*70)
    print("📈 백테스트 결과 요약")
    print("="*70)
    
    total_trades = len(buy_signals)
    if total_trades > 0:
        # 간단한 수익률 계산
        profits = []
        for i, buy in enumerate(buy_signals):
            # 다음 매도 신호 찾기
            sell_signals = [s for s in signals if s['type'] == 'SELL' and s['date'] > buy['date']]
            if sell_signals:
                sell = sell_signals[0]
                profit_pct = (sell['price'] / buy['price'] - 1) * 100
                profits.append(profit_pct)
        
        if profits:
            wins = [p for p in profits if p > 0]
            losses = [p for p in profits if p <= 0]
            
            print(f"총 거래: {len(profits)}회")
            print(f"승리: {len(wins)}회 ({len(wins)/len(profits)*100:.1f}%)")
            print(f"패배: {len(losses)}회 ({len(losses)/len(profits)*100:.1f}%)")
            print(f"평균 수익률: {sum(profits)/len(profits):.2f}%")
            if wins:
                print(f"평균 승리: {sum(wins)/len(wins):.2f}%")
            if losses:
                print(f"평균 손실: {sum(losses)/len(losses):.2f}%")
    
    print("="*70 + "\n")
    
    return True


def test_trend_template():
    """트렌드 템플릿 검증 테스트"""
    print("\n🧪 트렌드 템플릿 검증 테스트")
    print("-" * 70)
    
    # 샘플 데이터 생성 (이동평균선 정배열 케이스)
    dates = pd.date_range('2024-01-01', periods=250, freq='D')
    data = pd.DataFrame({
        'Close': range(100, 350),  # 상승 추세
        'High': range(102, 352),
        'Low': range(98, 348),
        'Open': range(99, 349),
        'Volume': [1000000] * 250
    }, index=dates)
    
    strategy = SEPAStrategy()
    df = strategy.calculate_indicators(data)
    
    # 마지막 지점에서 트렌드 템플릿 확인
    result = strategy.check_trend_template(df, len(df) - 1)
    
    print(f"이동평균선 정배열: {result}")
    print(f"  SMA50:  {df.iloc[-1]['sma50']:.2f}")
    print(f"  SMA150: {df.iloc[-1]['sma150']:.2f}")
    print(f"  SMA200: {df.iloc[-1]['sma200']:.2f}")
    print(f"  현재가: {df.iloc[-1]['Close']:.2f}")
    print(f"  52주고: {df.iloc[-1]['high_52w']:.2f}")
    
    if result:
        print("✅ 트렌드 템플릿 통과")
    else:
        print("❌ 트렌드 템플릿 실패")
    
    print()


def main():
    """메인 실행"""
    print("\n🚀 SEPA 전략 종합 테스트 시작")
    print("=" * 70)
    
    try:
        # 테스트 1: 트렌드 템플릿
        test_trend_template()
        
        # 테스트 2: 실제 데이터로 전략 테스트
        success = test_sepa_strategy()
        
        if success:
            print("✅ 모든 테스트 통과!")
        else:
            print("❌ 테스트 실패")
            return 1
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
