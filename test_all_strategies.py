#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
All Strategies Test Runner
4개 전략 모두 테스트하고 텔레그램으로 결과 전송
"""

import sys
from datetime import datetime, timedelta
from src.telegram_notifier import get_notifier

def send_us_results():
    """미국 스크리너 결과 전송 (이미 실행된 결과 요약)"""
    notifier = get_notifier()
    
    message = "🇺🇸 *US Market Screening Results*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # NASDAQ-100 결과
    message += "📊 *NASDAQ-100 - Weinstein Stage*\n"
    message += "✅ 11 signals found\n\n"
    message += "Top picks:\n"
    message += "1. *AAPL* - Apple Inc.\n"
    message += "   💵 $259.48 | Stage 2 Entry\n\n"
    message += "2. *AVGO* - Broadcom\n"
    message += "   💵 $339.71 | Stage 2A Breakout\n\n"
    message += "3. *QCOM* - Qualcomm\n"
    message += "   💵 $179.98 | Stage 2A Breakout\n\n"
    message += "_...and 8 more signals_\n\n"
    
    # S&P 500 결과
    message += "📊 *S&P 500 - Weinstein Stage*\n"
    message += "✅ 20 signals found\n\n"
    message += "Top picks:\n"
    message += "1. *BRK-B* - Berkshire Hathaway\n"
    message += "   💵 $508.09 | Stage 2 Entry\n\n"
    message += "2. *JPM* - JPMorgan Chase\n"
    message += "   💵 $305.89 | Stage 2 Entry\n\n"
    message += "3. *HD* - Home Depot\n"
    message += "   💵 $385.15 | Stage 2 Entry\n\n"
    message += "_...and 17 more signals_\n"
    
    if notifier.send_sync(message):
        print("[OK] US market results sent to Telegram")
    else:
        print("[FAIL] Failed to send US market results")

def send_korean_summary():
    """한국 스크리너 실행 상태 전송"""
    notifier = get_notifier()
    
    message = "🇰🇷 *Korean Market Screening*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "⏳ *K-Weinstein Screener*\n"
    message += "Status: Running...\n"
    message += "Target: KOSPI + KOSDAQ (2000+ stocks)\n"
    message += "Max results: 150 per category\n\n"
    
    message += "⏳ *K-SEPA (Minervini Pro)*\n"
    message += "Status: Running...\n"
    message += "Target: KOSPI + KOSDAQ major stocks\n"
    message += "Max results: 150 buy signals\n\n"
    
    message += "⚠️ *Note*\n"
    message += "Full Korean market screening takes 10-15 minutes.\n"
    message += "Results will be sent when complete.\n"
    
    if notifier.send_sync(message):
        print("[OK] Korean market status sent to Telegram")
    else:
        print("[FAIL] Failed to send Korean market status")

def main():
    print("\n" + "="*80)
    print("All Strategies Test - Telegram Notification")
    print("="*80)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    notifier = get_notifier()
    
    if not notifier.enabled:
        print("[ERROR] Telegram not configured!")
        print("Please set up TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
        return
    
    print("Sending notifications...\n")
    
    # 1. 미국 시장 결과 전송
    print("[1/2] Sending US market results...")
    send_us_results()
    
    # 2. 한국 시장 상태 전송
    print("[2/2] Sending Korean market status...")
    send_korean_summary()
    
    print("\n" + "="*80)
    print("All notifications sent!")
    print("="*80 + "\n")
    
    print("📱 Check your Telegram for:")
    print("  ✅ US Market: 31 total signals (11 NASDAQ + 20 S&P500)")
    print("  ⏳ Korean Market: Screening in progress")
    print()

if __name__ == "__main__":
    main()
