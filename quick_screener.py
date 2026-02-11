#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
빠른 통합 스크리너 (안정화 버전)
- 메모리 효율적
- 에러에 강건함
- 주요 종목만 스크리닝
"""

import sys
from datetime import datetime, timedelta
import pandas as pd
from src.data_loader import DataLoader
from src.telegram_notifier import get_notifier


def quick_us_screen():
    """미국 주요 종목만 빠르게 스크리닝"""
    print("\n[미국 시장] 스크리닝 중...")
    
    # 주요 종목만 (메모리 절약)
    symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
        'AVGO', 'ORCL', 'ADBE', 'NFLX', 'CSCO', 'QCOM', 'AMD',
        'JPM', 'V', 'MA', 'BAC', 'WFC', 'BRK-B',
        'UNH', 'JNJ', 'PFE', 'ABBV', 'LLY',
        'HD', 'MCD', 'SBUX', 'COST', 'NKE',
        'XOM', 'CVX', 'COP', 'BA', 'CAT'
    ]
    
    loader = DataLoader(verbose=False)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    signals = []
    
    for symbol in symbols:
        try:
            data = loader.fetch_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if data.empty or len(data) < 30:
                continue
            
            # 간단한 Weinstein Stage 체크
            data['MA30'] = data['Close'].rolling(window=30).mean()
            data['Vol_MA20'] = data['Volume'].rolling(window=20).mean()
            
            curr_price = data['Close'].iloc[-1]
            curr_ma30 = data['MA30'].iloc[-1]
            prev_ma30 = data['MA30'].iloc[-2]
            curr_vol = data['Volume'].iloc[-1]
            avg_vol = data['Vol_MA20'].iloc[-1]
            
            # Stage 2 확인
            if curr_price > curr_ma30 and curr_ma30 > prev_ma30:
                vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1
                signals.append({
                    'symbol': symbol,
                    'price': curr_price,
                    'ma30': curr_ma30,
                    'vol_ratio': vol_ratio
                })
        
        except Exception as e:
            continue
    
    print(f"[미국 시장] {len(signals)}개 신호 발견")
    return signals


def quick_korean_screen():
    """한국 주요 종목만 빠르게 스크리닝"""
    print("\n[한국 시장] 스크리닝 중...")
    
    # 주요 대형주만
    symbols = [
        '005930.KS',  # 삼성전자
        '000660.KS',  # SK하이닉스
        '035420.KS',  # NAVER
        '035720.KS',  # 카카오
        '051910.KS',  # LG화학
        '006400.KS',  # 삼성SDI
        '207940.KS',  # 삼성바이오로직스
        '068270.KS',  # 셀트리온
        '005380.KS',  # 현대차
        '000270.KS',  # 기아
        '105560.KS',  # KB금융
        '055550.KS',  # 신한지주
        '373220.KS',  # LG에너지솔루션
        '066570.KS',  # LG전자
        '012330.KS',  # 현대모비스
        '003670.KS',  # 포스코퓨처엠
        '028260.KS',  # 삼성물산
        '009150.KS',  # 삼성전기
        '017670.KS',  # SK텔레콤
        '032830.KS',  # 삼성생명
    ]
    
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
            
            # K-Weinstein: EMA120 체크
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
            is_volume_surge = curr_vol > avg_vol * 2.5  # 완화된 조건
            is_ema_rising = curr_ema > prev_ema
            
            if is_breakout and is_volume_surge and is_ema_rising:
                signals.append({
                    'symbol': symbol,
                    'price': curr_price,
                    'ema120': curr_ema,
                    'vol_ratio': curr_vol / avg_vol
                })
            elif curr_price > curr_ema and is_ema_rising:
                # Stage 2 유지 중
                if curr_vol > avg_vol * 1.5:
                    signals.append({
                        'symbol': symbol,
                        'price': curr_price,
                        'ema120': curr_ema,
                        'vol_ratio': curr_vol / avg_vol,
                        'status': 'Stage 2 유지'
                    })
        
        except Exception as e:
            continue
    
    print(f"[한국 시장] {len(signals)}개 신호 발견")
    return signals


def send_to_telegram(us_signals, kr_signals):
    """텔레그램 전송"""
    notifier = get_notifier()
    
    if not notifier.enabled:
        print("\n[텔레그램] 설정되지 않음")
        return False
    
    message = "📊 *빠른 스크리닝 결과*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 미국 시장
    message += f"🇺🇸 *미국 시장* ({len(us_signals)}개)\n\n"
    if us_signals:
        for i, s in enumerate(sorted(us_signals, key=lambda x: x.get('vol_ratio', 0), reverse=True)[:10], 1):
            message += f"{i}. *{s['symbol']}*\n"
            message += f"   ${s['price']:.2f} | Vol: {s['vol_ratio']:.1f}x\n"
    else:
        message += "신호 없음\n"
    
    message += "\n"
    
    # 한국 시장
    message += f"🇰🇷 *한국 시장* ({len(kr_signals)}개)\n\n"
    if kr_signals:
        for i, s in enumerate(sorted(kr_signals, key=lambda x: x.get('vol_ratio', 0), reverse=True)[:10], 1):
            status = s.get('status', 'Stage 2 진입')
            message += f"{i}. *{s['symbol']}*\n"
            message += f"   {s['price']:,.0f}원 | Vol: {s['vol_ratio']:.1f}x\n"
            if status != 'Stage 2 진입':
                message += f"   _{status}_\n"
    else:
        message += "신호 없음\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📈 총 {len(us_signals) + len(kr_signals)}개 신호"
    
    if notifier.send_sync(message):
        print("\n[OK] 텔레그램 전송 성공!")
        return True
    else:
        print("\n[FAIL] 텔레그램 전송 실패")
        return False


def main():
    print("\n" + "="*60)
    print("빠른 통합 스크리너")
    print("="*60)
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # 1. 미국 시장 스크리닝
        us_signals = quick_us_screen()
        
        # 2. 한국 시장 스크리닝
        kr_signals = quick_korean_screen()
        
        # 3. 결과 출력
        print("\n" + "="*60)
        print("스크리닝 완료!")
        print("="*60)
        print(f"미국: {len(us_signals)}개")
        print(f"한국: {len(kr_signals)}개")
        print(f"총: {len(us_signals) + len(kr_signals)}개")
        
        # 4. 텔레그램 전송
        if us_signals or kr_signals:
            print("\n텔레그램 전송 중...")
            send_to_telegram(us_signals, kr_signals)
        
        # 5. 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if us_signals:
            df = pd.DataFrame(us_signals)
            df.to_csv(f'quick_us_{timestamp}.csv', index=False, encoding='utf-8-sig')
            print(f"\n[저장] quick_us_{timestamp}.csv")
        
        if kr_signals:
            df = pd.DataFrame(kr_signals)
            df.to_csv(f'quick_kr_{timestamp}.csv', index=False, encoding='utf-8-sig')
            print(f"[저장] quick_kr_{timestamp}.csv")
        
        print(f"\n완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
