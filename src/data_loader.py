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
    
    def __init__(self):
        pass
    
    def fetch_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        주식 데이터 가져오기
        
        Args:
            symbol: 종목 코드 (예: "005930.KS", "AAPL")
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            interval: 데이터 간격 (1d, 1wk, 1mo)
        
        Returns:
            OHLCV 데이터프레임
        """
        print(f"📊 데이터 다운로드 중: {symbol} ({start_date} ~ {end_date})")
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if data.empty:
                print(f"⚠️  데이터 없음: {symbol}")
                return pd.DataFrame()
            
            # 컬럼 정리
            data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
            data.index.name = 'Date'
            
            print(f"✓ {len(data)}개 데이터 로드 완료")
            return data
            
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {symbol} - {e}")
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
