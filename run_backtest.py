#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
스윙매매 전략 백테스트 실행 스크립트
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime
import sys

# TODO: 실제 구현 시 import 활성화
# from src.data_loader import DataLoader
# from src.backtester import Backtester
# from src.performance import PerformanceAnalyzer
# from src.visualizer import Visualizer

from src.market_universe import MarketUniverse


def load_config(config_path="config/config.yaml"):
    """설정 파일 로드"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✓ 설정 파일 로드 완료: {config_path}")
        return config
    except FileNotFoundError:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
        print("힌트: config.yaml.example 파일을 config.yaml로 복사하세요")
        sys.exit(1)


def run_single_backtest(strategy_name, symbol, config):
    """단일 전략 백테스트 실행"""
    print(f"\n{'='*70}")
    print(f"🎯 백테스트 시작: {strategy_name} - {symbol}")
    print(f"{'='*70}")
    
    # TODO: 실제 백테스트 로직 구현
    print(f"기간: {config['backtest']['start_date']} ~ {config['backtest']['end_date']}")
    print(f"초기 자본: {config['backtest']['initial_capital']:,}원")
    print("\n⚠️  구현 중: 실제 백테스트 엔진은 아직 개발 중입니다.")
    print("다음 단계:")
    print("  1. strategies/ 폴더에 전략 구현")
    print("  2. src/backtester.py 백테스트 엔진 구현")
    print("  3. src/performance.py 성과 분석 모듈 구현")
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'status': 'pending_implementation'
    }


def get_symbols(config):
    """
    설정에서 스크리닝 대상 종목 리스트 가져오기
    
    Returns:
        종목 코드 리스트
    """
    screening_config = config.get('screening', {})
    
    # 시장 전체 스크리닝
    if screening_config.get('use_market', False):
        market = screening_config.get('market', 'NASDAQ100')
        print(f"\n📊 시장 스크리닝 모드: {market}")
        
        universe = MarketUniverse()
        symbols = universe.get_universe(market)
        
        print(f"✓ {len(symbols)}개 종목 로드 완료")
        print(f"샘플: {', '.join(symbols[:10])}")
        
        return symbols
    
    # 개별 종목 리스트
    else:
        symbols = screening_config.get('symbols', config.get('symbols', []))
        print(f"\n📋 개별 종목 모드: {len(symbols)}개")
        print(f"종목: {', '.join(symbols)}")
        
        return symbols


def run_comparison(strategies, symbols, config):
    """여러 전략 비교 백테스트"""
    print(f"\n{'='*70}")
    print(f"📊 전략 비교 백테스트")
    print(f"{'='*70}")
    print(f"전략: {', '.join(strategies)}")
    print(f"종목: {', '.join(symbols)}")
    
    results = []
    for strategy in strategies:
        for symbol in symbols:
            result = run_single_backtest(strategy, symbol, config)
            results.append(result)
    
    return results


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='스윙매매 전략 백테스트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 모든 전략 테스트
  python run_backtest.py --all
  
  # 특정 전략만 테스트
  python run_backtest.py --strategy bollinger_rsi
  
  # 특정 종목만 테스트
  python run_backtest.py --symbol 005930.KS
  
  # 전략 비교
  python run_backtest.py --compare --strategies bollinger_rsi,ma_crossover
        """
    )
    
    parser.add_argument('--all', action='store_true',
                        help='모든 활성화된 전략 테스트')
    parser.add_argument('--strategy', type=str,
                        help='테스트할 전략 이름')
    parser.add_argument('--symbol', type=str,
                        help='테스트할 종목 코드')
    parser.add_argument('--compare', action='store_true',
                        help='여러 전략 비교 모드')
    parser.add_argument('--strategies', type=str,
                        help='비교할 전략들 (쉼표로 구분)')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='설정 파일 경로')
    
    args = parser.parse_args()
    
    # 시작 메시지
    print("\n" + "="*70)
    print("🚀 스윙매매 전략 백테스터")
    print("="*70)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 설정 로드
    config = load_config(args.config)
    
    # output 폴더 생성
    Path("output").mkdir(exist_ok=True)
    Path("output/charts").mkdir(exist_ok=True)
    Path("output/reports").mkdir(exist_ok=True)
    
    # 종목 리스트 로드
    symbols = get_symbols(config)
    
    # 실행 모드 결정
    if args.compare and args.strategies:
        strategies = args.strategies.split(',')
        results = run_comparison(strategies, symbols, config)
    elif args.all:
        enabled_strategies = [
            name for name, params in config['strategies'].items()
            if params.get('enabled', False)
        ]
        results = run_comparison(enabled_strategies, symbols, config)
    elif args.strategy:
        symbol = args.symbol if args.symbol else symbols[0]
        results = [run_single_backtest(args.strategy, symbol, config)]
    else:
        print("❌ 실행 모드를 선택해주세요. --help 참고")
        sys.exit(1)
    
    # 결과 요약
    print(f"\n{'='*70}")
    print("✅ 백테스트 완료")
    print(f"{'='*70}")
    print(f"총 {len(results)}개 테스트 실행")
    print("\n💾 결과는 output/ 폴더에서 확인하세요:")
    print("  - output/backtest_results.xlsx (상세 거래 내역)")
    print("  - output/performance_summary.csv (성과 요약)")
    print("  - output/charts/ (차트 이미지)")
    print("  - output/reports/ (HTML 리포트)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
