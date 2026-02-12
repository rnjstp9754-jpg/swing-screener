# -*- coding: utf-8 -*-
"""
Data Loader

야후 파이낸스에서 주식 데이터를 가져오는 모듈
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class DataLoader:
    """데이터 로더 클래스"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        # 전역 타임아웃 설정 (15초)
        import socket
        socket.setdefaulttimeout(15)
    
    def fetch_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        주식 데이터 가져오기 (전역 타임아웃 적용)
        """
        if self.verbose:
            print(f"[DATA] Loading {symbol} ({start_date} ~ {end_date})")
        
        try:
            # yfinance 호환성을 위해 기본 세션 사용
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if data.empty:
                if self.verbose:
                    print(f"[WARN] No data: {symbol}")
                return pd.DataFrame()
            
            # 컬럼 정리
            data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
            data.index.name = 'Date'
            
            if self.verbose:
                print(f"[OK] {len(data)} bars loaded")
            return data
            
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Failed to load {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """
        최근 N일 데이터 가져오기
        
        Args:
            symbol: 종목 코드
            days: 가져올 일수
        
        Returns:
            OHLCV 데이터프레임
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.fetch_data(
            symbol,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
