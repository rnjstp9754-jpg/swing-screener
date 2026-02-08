#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get Telegram Chat ID Helper
텔레그램 Chat ID 확인 도구
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ .env 파일에 TELEGRAM_BOT_TOKEN이 없습니다!")
    exit(1)

print("\n" + "="*80)
print("Telegram Chat ID Confirmation Guide")
print("="*80)
print()
print("[Method 1] Using @userinfobot (Personal Chat)")
print()
print("1. Search '@userinfobot' in Telegram")
print("2. Send /start or any message")
print("3. Copy 'Your user ID' value")
print("   Example: 987654321")
print()
print("="*80)
print()
print("[Method 2] Check via Browser")
print()
print("1. Send a message to your bot (/start)")
print("2. Open this URL in your browser:")
print()
print(f"   https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
print()
print("3. Find 'chat':{'id': number} in JSON response")
print()
print("="*80)
print()
print("[After Getting Chat ID]")
print()
print("1. Open .env file")
print("2. Change TELEGRAM_CHAT_ID=your_chat_id_here")
print("   to TELEGRAM_CHAT_ID=987654321")
print("3. Run: python test_telegram.py")
print()
print("="*80)
print()
