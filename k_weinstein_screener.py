#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
K-Weinstein Stage Screener
한국형 와인스타인 스테이지 분석 스크리너

특징:
- EMA120 (120일 지수이동평균) 기준
- Stage 2 진입: 120일선 돌파 + 거래량 3배 폭증
- Stage 4 진입: 120일선 하향 돌파
- KOSPI + KOSDAQ 전 종목 스크리닝
"""

import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta


def k_weinstein_screener():
    """
    한국형 와인스타인 스크리너
    
    Returns:
        (buy_list, sell_list, watch_list)
    """
    
    print("\n" + "="*80)
    print("K-Weinstein Stage Analysis Screener")
    print("Market: KOSPI + KOSDAQ")
    print("="*80)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 전 종목 리스트 확보 (KRX = KOSPI + KOSDAQ)
    print("[1/4] Loading KRX stock list...")
    df_krx = fdr.StockListing('KRX')
    
    print(f"[OK] Total {len(df_krx)} stocks loaded")
    print(f"     - KOSPI: {len(df_krx[df_krx['Market'] == 'KOSPI'])} stocks")
    print(f"     - KOSDAQ: {len(df_krx[df_krx['Market'] == 'KOSDAQ'])} stocks")
    print(f"     - KONEX: {len(df_krx[df_krx['Market'] == 'KONEX'])} stocks\n")
    
    # KONEX 제외
    df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])]
    target_list = df_krx['Code'].tolist()
    
    # 2. 날짜 설정 (200일 데이터)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d')
    
    print(f"[2/4] Data period: {start_date} ~ {end_date}\n")
    
    # 3. 스크리닝 시작
    print("[3/4] Screening stocks...")
    print(f"{'Progress':<15} {'Code':<10} {'Name':<20} {'Status'}")
    print("-" * 80)
    
    buy_list = []
    sell_list = []
    watch_list = []
    
    success_count = 0
    error_count = 0
    
    for i, code in enumerate(target_list, 1):
        try:
            # 데이터 로드
            df = fdr.DataReader(code, start_date, end_date)
            
            if len(df) < 120:
                continue
            
            # 지표 계산
            df['EMA120'] = df['Close'].ewm(span=120, adjust=False).mean()
            df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
            
            curr_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            curr_ema = df['EMA120'].iloc[-1]
            prev_ema = df['EMA120'].iloc[-2]
            curr_vol = df['Volume'].iloc[-1]
            avg_vol = df['Vol_MA20'].iloc[-1]
            
            # 종목명 찾기
            stock_info = df_krx[df_krx['Code'] == code]
            stock_name = stock_info['Name'].values[0] if not stock_info.empty else "N/A"
            
            # [Stage 2 진입 - BUY]
            # 1) 가격이 120일선 돌파
            # 2) 거래량이 평균 3배 이상
            # 3) EMA120 우상향
            is_breakout = (curr_price > curr_ema) and (prev_price <= prev_ema)
            is_volume_surge = curr_vol > avg_vol * 3
            is_ema_rising = curr_ema > prev_ema
            
            if is_breakout and is_volume_surge and is_ema_rising:
                buy_list.append({
                    'code': code,
                    'name': stock_name,
                    'price': curr_price,
                    'ema120': curr_ema,
                    'vol_ratio': curr_vol / avg_vol
                })
                status = "[BUY] Stage 2 Breakout!"
                print(f"[{i}/{len(target_list)}] {code:<10} {stock_name:<20} {status}")
            
            # [Stage 4 진입 - SELL]
            # 가격이 120일선 하향 돌파
            elif (curr_price < curr_ema) and (prev_price >= prev_ema):
                sell_list.append({
                    'code': code,
                    'name': stock_name,
                    'price': curr_price,
                    'ema120': curr_ema
                })
                status = "[SELL] Stage 4 Break"
                if i % 50 == 0:  # 매도는 50개마다만 출력
                    print(f"[{i}/{len(target_list)}] {code:<10} {stock_name:<20} {status}")
            
            # [Stage 2 유지 - WATCH]
            # 이미 120일선 위에 있고, 우상향 중
            elif (curr_price > curr_ema) and is_ema_rising:
                watch_list.append({
                    'code': code,
                    'name': stock_name,
                    'price': curr_price,
                    'ema120': curr_ema
                })
            
            success_count += 1
            
            # 진행률 출력 (100개마다)
            if i % 100 == 0:
                progress_pct = (i / len(target_list)) * 100
                print(f"[{i}/{len(target_list)}] Progress: {progress_pct:.1f}%")
        
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # 처음 10개 에러만 출력
                print(f"[{i}/{len(target_list)}] {code:<10} {'ERROR':<20} {str(e)[:30]}")
            continue
    
    # 4. 결과 요약
    print("\n" + "="*80)
    print("[4/4] Screening Results")
    print("="*80)
    print(f"Total Processed: {success_count}")
    print(f"Errors: {error_count}")
    print()
    
    # Stage 2 매수 후보
    print(f"\n{'█'*20} Stage 2 진입: 매수 후보 ({len(buy_list)}개) {'█'*20}")
    if buy_list:
        print(f"\n{'Code':<10} {'Name':<20} {'Price':<12} {'EMA120':<12} {'Vol Ratio'}")
        print("-" * 80)
        for stock in sorted(buy_list, key=lambda x: x['vol_ratio'], reverse=True)[:30]:
            print(f"{stock['code']:<10} {stock['name']:<20} "
                  f"{stock['price']:<12,.0f} {stock['ema120']:<12,.0f} "
                  f"{stock['vol_ratio']:.1f}x")
    else:
        print("No Stage 2 breakout signals found.")
    
    # Stage 4 매도 신호
    print(f"\n{'█'*20} Stage 4 진입: 매도 신호 ({len(sell_list)}개) {'█'*20}")
    if sell_list:
        print(f"\n{'Code':<10} {'Name':<20} {'Price':<12} {'EMA120':<12}")
        print("-" * 80)
        for stock in sell_list[:20]:
            print(f"{stock['code']:<10} {stock['name']:<20} "
                  f"{stock['price']:<12,.0f} {stock['ema120']:<12,.0f}")
    else:
        print("No Stage 4 breakdown signals found.")
    
    # Stage 2 유지 종목 (참고용)
    print(f"\n{'█'*20} Stage 2 유지: 관찰 대상 ({len(watch_list)}개) {'█'*20}")
    print(f"Total {len(watch_list)} stocks in Stage 2 uptrend\n")
    
    print("="*80)
    print("Screening Complete!")
    print("="*80 + "\n")
    
    return buy_list, sell_list, watch_list


if __name__ == "__main__":
    try:
        buy_list, sell_list, watch_list = k_weinstein_screener()
        
        # 결과 저장 (CSV)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if buy_list:
            df_buy = pd.DataFrame(buy_list)
            df_buy.to_csv(f'k_weinstein_buy_{timestamp}.csv', index=False, encoding='utf-8-sig')
            print(f"[SAVED] k_weinstein_buy_{timestamp}.csv")
        
        if sell_list:
            df_sell = pd.DataFrame(sell_list)
            df_sell.to_csv(f'k_weinstein_sell_{timestamp}.csv', index=False, encoding='utf-8-sig')
            print(f"[SAVED] k_weinstein_sell_{timestamp}.csv")
    
    except Exception as e:
        print(f"\n[ERROR] Screener failed: {e}")
        import traceback
        traceback.print_exc()
