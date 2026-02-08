#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Telegram Test - Korean Format
"""

from src.telegram_notifier import get_notifier

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
    }
]

notifier = get_notifier()

# 테스트
message = notifier.format_screening_results(
    market="NASDAQ100",
    strategy="Weinstein Stage",
    buy_signals=buy_signals
)

print("="*60)
print("Testing Korean Format Message")
print("="*60)

if notifier.enabled:
    print("\nSending to Telegram...")
    result = notifier.send_sync(message)
    if result:
        print("[OK] Message sent successfully!")
        print("Check your Telegram to see the Korean format!")
    else:
        print("[FAIL] Failed to send message")
else:
    print("\n[SKIP] Telegram not configured")
