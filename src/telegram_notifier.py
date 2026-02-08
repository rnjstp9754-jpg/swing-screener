#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Notification Module
텔레그램 알림 모듈
"""

import os
from typing import List, Dict
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv


class TelegramNotifier:
    """텔레그램 알림 클래스"""
    
    def __init__(self):
        # .env 파일 로드
        load_dotenv()
        
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            print("[WARNING] Telegram credentials not found in .env file")
            print("Please create .env file with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            self.enabled = False
        else:
            self.bot = Bot(token=self.bot_token)
            self.enabled = True
    
    async def send_message(self, message: str, parse_mode: str = 'Markdown'):
        """
        텔레그램 메시지 전송
        
        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드 ('Markdown' or 'HTML')
        """
        if not self.enabled:
            print("[SKIP] Telegram not configured")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            print(f"[ERROR] Failed to send Telegram message: {e}")
            return False
    
    def send_sync(self, message: str, parse_mode: str = 'Markdown'):
        """
        동기 방식 메시지 전송 (일반 스크립트에서 사용)
        
        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드
        """
        if not self.enabled:
            print("[SKIP] Telegram not configured")
            return False
        
        try:
            # 이벤트 루프 생성 및 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.send_message(message, parse_mode))
            loop.close()
            return result
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram message: {e}")
            return False
    
    def format_screening_results(
        self,
        market: str,
        strategy: str,
        buy_signals: List[Dict],
        max_results: int = 10
    ) -> str:
        """
        스크리닝 결과를 텔레그램 메시지 형식으로 변환
        
        Args:
            market: 시장 이름
            strategy: 전략 이름
            buy_signals: 매수 신호 리스트
            max_results: 최대 표시 개수
        
        Returns:
            포맷된 메시지
        """
        # 전략 한글 매핑
        strategy_kr = {
            'Weinstein Stage': '와인스타인 스테이지',
            'SEPA': 'SEPA (미너비니)',
            'Aggressive SEPA': '공격적 SEPA 2026',
            'K-Minervini Pro': '한국형 미너비니 프로',
            'Bollinger RSI': '볼린저밴드 + RSI'
        }.get(strategy, strategy)
        
        # 시장 한글 매핑
        market_kr = {
            'NASDAQ100': '나스닥 100',
            'SP500': 'S&P 500',
            'RUSSELL2000': '러셀 2000'
        }.get(market, market)
        
        if not buy_signals:
            message = f"📊 *{market_kr}*\n"
            message += f"전략: *{strategy_kr}*\n\n"
            message += "신호 없음\n"
            return message
        
        # 헤더
        message = f"🚀 *{market_kr} - {strategy_kr}*\n"
        message += f"📈 *{len(buy_signals)}개 매수 신호*\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # 상위 결과만 표시
        for i, signal in enumerate(buy_signals[:max_results], 1):
            symbol = signal.get('symbol', signal.get('code', 'N/A'))
            name = signal.get('name', '')
            price = signal.get('price', 0)
            
            message += f"*{i}. {symbol}*"
            if name:
                message += f" ({name})"
            message += "\n"
            
            # 가격 정보
            if isinstance(price, (int, float)) and price > 0:
                if price < 1000:
                    message += f"💵 가격: ${price:.2f}\n"
                else:
                    message += f"💵 가격: {price:,.0f}원\n"
            
            # 거래량 정보 (있는 경우)
            vol_ratio = signal.get('vol_ratio', signal.get('volume_ratio'))
            if vol_ratio:
                message += f"📊 거래량: {vol_ratio:.1f}배\n"
            
            # 이유 (있는 경우)
            reason = signal.get('reason')
            if reason:
                # 마크다운 특수문자 이스케이프
                reason_escaped = reason.replace('_', '\\_').replace('*', '\\*')
                message += f"📌 {reason_escaped[:50]}\n"
            
            message += "\n"
        
        # 더 많은 결과가 있는 경우
        if len(buy_signals) > max_results:
            message += f"_...외 {len(buy_signals) - max_results}개 신호_\n"
        
        return message
    
    def format_k_weinstein_results(
        self,
        buy_list: List[Dict],
        sell_list: List[Dict],
        max_buy: int = 10,
        max_sell: int = 5
    ) -> str:
        """
        한국 와인스타인 스크리닝 결과 포맷
        
        Args:
            buy_list: 매수 신호 리스트
            sell_list: 매도 신호 리스트
            max_buy: 최대 매수 신호 표시 개수
            max_sell: 최대 매도 신호 표시 개수
        
        Returns:
            포맷된 메시지
        """
        message = "🇰🇷 *K-Weinstein Stage Analysis*\n"
        message += f"📅 {asyncio.get_event_loop().time()}\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # 매수 신호
        message += f"🚀 *Stage 2 진입 ({len(buy_list)}개)*\n\n"
        
        if buy_list:
            # 거래량 비율로 정렬
            sorted_buy = sorted(buy_list, key=lambda x: x.get('vol_ratio', 0), reverse=True)
            
            for i, stock in enumerate(sorted_buy[:max_buy], 1):
                message += f"*{i}. {stock['code']}* {stock['name']}\n"
                message += f"💵 {stock['price']:,.0f}원 "
                message += f"(EMA120: {stock['ema120']:,.0f})\n"
                message += f"📈 Volume: {stock['vol_ratio']:.1f}x\n\n"
            
            if len(buy_list) > max_buy:
                message += f"_...and {len(buy_list) - max_buy} more_\n\n"
        else:
            message += "❌ No signals\n\n"
        
        # 매도 신호
        message += f"⚠️ *Stage 4 진입 ({len(sell_list)}개)*\n\n"
        
        if sell_list and max_sell > 0:
            for i, stock in enumerate(sell_list[:max_sell], 1):
                message += f"{i}. {stock['code']} {stock['name']}\n"
            
            if len(sell_list) > max_sell:
                message += f"_...and {len(sell_list) - max_sell} more_\n"
        
        return message


# 전역 인스턴스
_notifier = None


def get_notifier() -> TelegramNotifier:
    """전역 텔레그램 알림 인스턴스 반환"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


def send_telegram(message: str, parse_mode: str = 'Markdown') -> bool:
    """
    간편 텔레그램 전송 함수
    
    Args:
        message: 전송할 메시지
        parse_mode: 파싱 모드
    
    Returns:
        성공 여부
    """
    notifier = get_notifier()
    return notifier.send_sync(message, parse_mode)
