#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
K-SEPA (K-Minervini Pro) Screener
한국형 미너비니 프로 전략 스크리너

특징:
- 240일선(1년선) 기관 매집 확인
- 한국형 VCP 패턴 검증
- 한국형 거래량 폭증 (3.5배)
- KOSPI + KOSDAQ 전 종목 스크리닝
"""

import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from src.data_loader import DataLoader
from strategies.k_sepa import KMinerviniProStrategy


def k_sepa_screener(max_results=150):
    """
    한국형 SEPA 스크리너
    
    Args:
        max_results: 최대 결과 개수 (기본값: 150)
    
    Returns:
        (buy_signals, watch_signals)
    """
    
    print("\n" + "="*80)
    print("K-SEPA (K-Minervini Pro) Screener")
    print("Market: KOSPI + KOSDAQ")
    print(f"Max Results: {max_results} per category")
    print("="*80)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 전 종목 리스트 확보
    print("[1/4] Loading KRX stock list...")
    df_krx = fdr.StockListing('KRX')
    
    print(f"[OK] Total {len(df_krx)} stocks loaded")
    print(f"     - KOSPI: {len(df_krx[df_krx['Market'] == 'KOSPI'])} stocks")
    print(f"     - KOSDAQ: {len(df_krx[df_krx['Market'] == 'KOSDAQ'])} stocks\n")
    
    # KONEX 제외, 대형주 위주
    df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])]
    target_list = df_krx['Code'].tolist()
    
    # 2. 날짜 설정 (240일 데이터 필요)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2년 데이터
    
    print(f"[2/4] Data period: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}\n")
    
    # 3. 전략 초기화
    loader = DataLoader(verbose=False)
    strategy = KMinerviniProStrategy()
    
    # 4. 스크리닝 시작
    print("[3/4] Screening stocks...")
    print(f"{'Progress':<15} {'Code':<10} {'Name':<20} {'Status'}")
    print("-" * 80)
    
    buy_signals = []
    watch_signals = []
    
    success_count = 0
    error_count = 0
    
    for i, code in enumerate(target_list, 1):
        try:
            # 데이터 로드
            data = loader.fetch_data(
                f"{code}.KS" if code[0] != 'A' else f"{code[1:]}.KS",
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if data.empty or len(data) < 240:
                continue
            
            # 종목명 찾기
            stock_info = df_krx[df_krx['Code'] == code]
            stock_name = stock_info['Name'].values[0] if not stock_info.empty else "N/A"
            
            # 전략 실행
            signals = strategy.generate_signals(data)
            
            # 매수 신호 필터
            buys = [s for s in signals if s['type'] == 'BUY']
            watches = [s for s in signals if s.get('type') == 'WATCH']
            
            if buys:
                for signal in buys:
                    buy_signals.append({
                        **signal,
                        'code': code,
                        'name': stock_name
                    })
                print(f"[{i}/{len(target_list)}] {code:<10} {stock_name:<20} [BUY] K-STRIKE!")
            elif watches:
                for signal in watches:
                    watch_signals.append({
                        **signal,
                        'code': code,
                        'name': stock_name
                    })
            
            success_count += 1
            
            # 진행률 출력 (100개마다)
            if i % 100 == 0:
                progress_pct = (i / len(target_list)) * 100
                print(f"[{i}/{len(target_list)}] Progress: {progress_pct:.1f}% (Buy: {len(buy_signals)}, Watch: {len(watch_signals)})")
        
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # 처음 10개 에러만 출력
                print(f"[{i}/{len(target_list)}] {code:<10} {'ERROR':<20} {str(e)[:30]}")
            continue
    
    # 5. 결과 정리 (confidence 기준 정렬 후 최대 개수로 제한)
    print("\n" + "="*80)
    print("[4/4] Screening Results")
    print("="*80)
    print(f"Total Processed: {success_count}")
    print(f"Errors: {error_count}")
    
    # confidence로 정렬 후 상위 N개 선택
    buy_signals = sorted(buy_signals, key=lambda x: x.get('confidence', 0), reverse=True)[:max_results]
    watch_signals = sorted(watch_signals, key=lambda x: x.get('confidence', 0), reverse=True)[:max_results]
    
    print()
    
    # K-STRIKE 매수 신호 (최대 150개, 출력 30개)
    print(f"\n{'█'*20} K-STRIKE 매수 신호 ({len(buy_signals)}개) {'█'*20}")
    if buy_signals:
        print(f"\n{'Code':<10} {'Name':<20} {'Price':<12} {'Confidence':<12} {'Vol Ratio'}")
        print("-" * 80)
        for signal in buy_signals[:30]:
            print(f"{signal['code']:<10} {signal['name']:<20} "
                  f"{signal['price']:<12,.0f} {signal['confidence']:<12.2f} "
                  f"{signal['metrics']['volume_ratio']:.1f}x")
    else:
        print("No K-STRIKE signals found.")
    
    # VCP 준비 신호 (최대 150개, 출력 20개)
    print(f"\n{'█'*20} VCP 준비 중 ({len(watch_signals)}개) {'█'*20}")
    if watch_signals:
        print(f"\n{'Code':<10} {'Name':<20} {'Price':<12} {'Reason'}")
        print("-" * 80)
        for signal in watch_signals[:20]:
            print(f"{signal['code']:<10} {signal['name']:<20} "
                  f"{signal.get('price', 0):<12,.0f} {signal.get('reason', 'VCP forming')[:40]}")
    else:
        print("No VCP watch signals found.")
    
    print("\n" + "="*80)
    print("Screening Complete!")
    print("="*80 + "\n")
    
    # 텔레그램 알림 전송
    try:
        from src.telegram_notifier import get_notifier
        
        notifier = get_notifier()
        
        if notifier.enabled and buy_signals:
            print("[Telegram] Sending K-SEPA notifications...")
            
            message = f"🇰🇷 *K-SEPA (K-Minervini Pro)*\n"
            message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            message += f"🎯 *K-STRIKE Signals ({len(buy_signals)})*\n\n"
            
            for i, signal in enumerate(buy_signals[:10], 1):
                message += f"*{i}. {signal['code']}* {signal['name']}\n"
                message += f"💵 {signal['price']:,.0f}원\n"
                message += f"📊 Confidence: {signal['confidence']:.2f}\n"
                message += f"📈 Volume: {signal['metrics']['volume_ratio']:.1f}x\n\n"
            
            if len(buy_signals) > 10:
                message += f"_...and {len(buy_signals) - 10} more_\n"
            
            if notifier.send_sync(message):
                print(f"[OK] Sent K-SEPA results (Buy: {len(buy_signals)})")
            else:
                print("[FAIL] Failed to send K-SEPA results")
            
            print("[Telegram] Notification complete!\n")
        else:
            if not notifier.enabled:
                print("\n[Telegram] Not configured (skipped)\n")
    
    except Exception as e:
        print(f"\n[ERROR] Telegram notification failed: {e}\n")
    
    return buy_signals, watch_signals


if __name__ == "__main__":
    try:
        buy_signals, watch_signals = k_sepa_screener(max_results=150)
        
        # 결과 저장 (CSV)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if buy_signals:
            df_buy = pd.DataFrame(buy_signals)
            df_buy.to_csv(f'k_sepa_buy_{timestamp}.csv', index=False, encoding='utf-8-sig')
            print(f"[SAVED] k_sepa_buy_{timestamp}.csv")
        
        if watch_signals:
            df_watch = pd.DataFrame(watch_signals)
            df_watch.to_csv(f'k_sepa_watch_{timestamp}.csv', index=False, encoding='utf-8-sig')
            print(f"[SAVED] k_sepa_watch_{timestamp}.csv")
    
    except Exception as e:
        print(f"\n[ERROR] Screener failed: {e}")
        import traceback
        traceback.print_exc()
