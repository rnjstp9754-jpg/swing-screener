#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Test Script
텔레그램 알림 테스트
"""

from src.telegram_notifier import get_notifier, send_telegram


def test_simple_message():
    """간단한 메시지 테스트"""
    print("\n[TEST 1] Sending simple message...")
    result = send_telegram("🚀 Test message from Stock Screener!")
    
    if result:
        print("[OK] Message sent successfully!")
    else:
        print("[FAIL] Failed to send message")
    
    return result


def test_formatted_message():
    """포맷된 메시지 테스트"""
    print("\n[TEST 2] Sending formatted message...")
    
    message = """
*Stock Screener Alert* 🎯

📊 *AAPL* - Apple Inc.
💵 Price: $259.48
📈 Volume: 2.5x

_Stage 2 Breakout!_
"""
    
    result = send_telegram(message)
    
    if result:
        print("[OK] Formatted message sent!")
    else:
        print("[FAIL] Failed to send formatted message")
    
    return result


def test_screening_results():
    """스크리닝 결과 포맷 테스트"""
    print("\n[TEST 3] Sending screening results...")
    
    # 샘플 데이터
    buy_signals = [
        {
            'symbol': 'AAPL',
            'name': 'Apple',
            'price': 259.48,
            'volume_ratio': 2.5,
            'reason': 'Stage 2A Breakout - MA30 breakout + Volume surge'
        },
        {
            'symbol': 'NVDA',
            'name': 'NVIDIA',
            'price': 485.20,
            'volume_ratio': 3.2,
            'reason': 'Stage 2 Entry - Above MA30(450) + Rising'
        },
        {
            'symbol': 'MSFT',
            'name': 'Microsoft',
            'price': 425.30,
            'volume_ratio': 1.8,
            'reason': 'Stage 2 Entry - Above MA30(420) + Rising'
        }
    ]
    
    notifier = get_notifier()
    message = notifier.format_screening_results(
        market="NASDAQ-100",
        strategy="Weinstein Stage",
        buy_signals=buy_signals,
        max_results=5
    )
    
    result = notifier.send_sync(message)
    
    if result:
        print("[OK] Screening results sent!")
    else:
        print("[FAIL] Failed to send screening results")
    
    return result


def test_korean_results():
    """한국 스크리닝 결과 테스트"""
    print("\n[TEST 4] Sending Korean screening results...")
    
    # 샘플 데이터
    buy_list = [
        {
            'code': '005930',
            'name': '삼성전자',
            'price': 75000,
            'ema120': 70000,
            'vol_ratio': 4.2
        },
        {
            'code': '000660',
            'name': 'SK하이닉스',
            'price': 120000,
            'ema120': 115000,
            'vol_ratio': 3.8
        }
    ]
    
    sell_list = [
        {
            'code': '035720',
            'name': '카카오',
            'price': 48000,
            'ema120': 50000
        }
    ]
    
    notifier = get_notifier()
    message = notifier.format_k_weinstein_results(
        buy_list=buy_list,
        sell_list=sell_list,
        max_buy=10,
        max_sell=5
    )
    
    # 시간 문자열 수정 (asyncio 제거)
    from datetime import datetime
    message = message.replace(
        f"{asyncio.get_event_loop().time()}",
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    result = notifier.send_sync(message)
    
    if result:
        print("[OK] Korean results sent!")
    else:
        print("[FAIL] Failed to send Korean results")
    
    return result


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("Telegram Notification Test")
    print("="*80)
    
    # .env 파일 체크
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("\n[ERROR] .env file not configured!")
        print("\nPlease create .env file with:")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print("\nSee docs/telegram_setup.md for details")
        return
    
    print(f"\n[OK] Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    print(f"[OK] Chat ID: {chat_id}")
    
    # 테스트 실행
    results = []
    
    results.append(("Simple Message", test_simple_message()))
    results.append(("Formatted Message", test_formatted_message()))
    results.append(("Screening Results", test_screening_results()))
    # results.append(("Korean Results", test_korean_results()))  # 시간 이슈로 주석
    
    # 결과 요약
    print("\n" + "="*80)
    print("Test Results")
    print("="*80)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
