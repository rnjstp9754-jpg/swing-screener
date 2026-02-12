# -*- coding: utf-8 -*-
"""
Market Universe Loader

나스닥, S&P500 등 주요 지수 구성 종목 리스트를 가져오는 모듈
"""

import pandas as pd
import yfinance as yf
from typing import List, Dict
import requests
from bs4 import BeautifulSoup


class MarketUniverse:
    """시장 종목 리스트 로더"""
    
    def __init__(self):
        self.cache = {}
    
    def get_nasdaq_100(self) -> List[str]:
        """
        나스닥 100 종목 리스트 (실제 100개)
        
        Returns:
            종목 코드 리스트
        """
        if 'NASDAQ100' in self.cache:
            return self.cache['NASDAQ100']
        
        print("[NASDAQ-100] Loading...")
        
        nasdaq_100 = [
            # Mega Cap Tech
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
            'AVGO', 'ADBE', 'CSCO', 'NFLX', 'INTC', 'AMD', 'QCOM', 'TXN',
            'INTU', 'AMAT', 'ADI', 'LRCX', 'KLAC', 'SNPS', 'CDNS', 'MRVL',
            'ASML', 'PANW', 'CRWD', 'WDAY', 'TEAM', 'NOW', 'DDOG', 'ZS',

            # Software / Cloud
            'ORCL', 'CRM', 'ADSK', 'FTNT', 'SPLK', 'ANSS', 'CPRT', 'MCHP',
            'ON', 'GFS', 'SMCI', 'ARM', 'MDB', 'DASH',

            # Consumer / Internet
            'COST', 'SBUX', 'BKNG', 'MAR', 'ABNB', 'MELI', 'PDD', 'JD',
            'PYPL', 'AEP', 'EXC', 'XEL', 'LULU', 'ROST',

            # Healthcare / Biotech
            'AMGN', 'GILD', 'REGN', 'VRTX', 'BIIB', 'MRNA', 'ILMN', 'DXCM',
            'IDXX', 'ALGN',

            # Industrial / Other
            'PEP', 'ADP', 'ISRG', 'MDLZ', 'MNST', 'CTAS', 'PAYX', 'PCAR',
            'ODFL', 'FAST', 'CSX', 'HON', 'GEHC', 'VRSK',
            'CEG', 'AZN', 'CCEP', 'TTWO', 'EA', 'WBD',
            'KHC', 'KDP', 'DLTR', 'BKR', 'FANG',

            # Communications
            'CMCSA', 'TMUS', 'CHTR', 'WBA',
        ]

        # 중복 제거
        nasdaq_100 = list(dict.fromkeys(nasdaq_100))
        
        self.cache['NASDAQ100'] = nasdaq_100
        print(f"[OK] {len(nasdaq_100)} symbols loaded")
        
        return nasdaq_100
    
    def get_nasdaq_composite(self) -> List[str]:
        """
        나스닥 종합 지수 주요 종목 (상위 시가총액)
        
        Returns:
            종목 코드 리스트
        """
        if 'NASDAQ' in self.cache:
            return self.cache['NASDAQ']
        
        print("[NASDAQ Composite] Loading...")
        
        # 나스닥 100 + 추가 중소형주
        nasdaq = self.get_nasdaq_100() + [
            # 중형주
            'DOCU', 'OKTA', 'NET', 'SNOW', 'PLTR', 'RBLX', 'U', 'COIN',
            'HOOD', 'RIVN', 'LCID', 'UPST', 'AFRM', 'SQ',
            
            # 소형주
            'FUBO', 'WISH', 'OPEN', 'CPNG', 'GRAB', 'SOFI'
        ]
        
        # 중복 제거 (순서 보존)
        nasdaq = list(dict.fromkeys(nasdaq))
        
        self.cache['NASDAQ'] = nasdaq
        print(f"[OK] {len(nasdaq)} symbols loaded")
        
        return nasdaq
    
    def get_russell_2000(self) -> List[str]:
        """
        러셀 2000 주요 종목 (소형주 샘플)
        """
        if 'RUSSELL2000' in self.cache:
            return self.cache['RUSSELL2000']
        
        print("[Russell 2000] Loading...")
        
        russell_2000 = [
            # Energy
            'RIG', 'SM', 'PTEN', 'NE', 'MTDR',
            # Financials
            'CBSH', 'WTFC', 'FFIN', 'UMBF', 'CATY',
            # Healthcare
            'PDCO', 'PTGX', 'KRYS', 'CRVL', 'AMED',
            # Technology
            'CWAN', 'AGYS', 'CALX', 'COHU', 'DIOD',
            # Consumer
            'CAKE', 'TXRH', 'WING', 'BLMN', 'DNUT',
            # Industrials
            'AGCO', 'ASTE', 'ATKR', 'AIT', 'AIMC',
            # Materials
            'CENX', 'ARCH', 'BTU', 'CEIX', 'HCC',
            # Real Estate
            'CUBE', 'ELS', 'SUI', 'REXR', 'STAG',
            # Utilities
            'AVA', 'NWE', 'NWN', 'SJW', 'YORW'
        ]
        
        self.cache['RUSSELL2000'] = russell_2000
        print(f"[OK] {len(russell_2000)} symbols loaded")
        print("[Note] Sample only, not all 2000 stocks")
        
        return russell_2000
    
    def get_sp500(self) -> List[str]:
        """
        S&P 500 주요 종목 (시가총액 상위 약 150개)
        """
        if 'SP500' in self.cache:
            return self.cache['SP500']
        
        print("[S&P 500] Loading...")
        
        sp500 = [
            # Mega Cap (Top 10)
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
            'AVGO', 'LLY',

            # Large Cap Tech
            'ORCL', 'ADBE', 'CRM', 'CSCO', 'ACN', 'NFLX', 'AMD', 'QCOM',
            'TXN', 'INTC', 'IBM', 'NOW', 'INTU', 'AMAT', 'ADI', 'LRCX',

            # Financials
            'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'SCHW',
            'AXP', 'MMC', 'CB', 'PGR', 'ICE', 'CME', 'AON', 'MET', 'AIG',
            'TFC', 'USB',

            # Healthcare
            'UNH', 'JNJ', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR',
            'BMY', 'AMGN', 'GILD', 'ISRG', 'SYK', 'ELV',
            'MDT', 'CI', 'REGN', 'VRTX', 'BSX',

            # Consumer Staples
            'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'CL', 'MDLZ',
            'GIS', 'KHC', 'K', 'HSY', 'STZ',

            # Consumer Discretionary
            'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'ROST',
            'BKNG', 'CMG', 'MAR', 'HLT', 'F', 'GM', 'ORLY', 'AZO',

            # Energy
            'XOM', 'CVX', 'COP', 'SLB', 'MPC', 'PSX', 'VLO', 'EOG',
            'OXY', 'HAL', 'DVN', 'FANG',

            # Industrials
            'BA', 'HON', 'UPS', 'CAT', 'RTX', 'DE', 'LMT', 'GE',
            'UNP', 'FDX', 'WM', 'ETN', 'ITW', 'EMR', 'NOC', 'GD',

            # Communication
            'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR', 'EA', 'TTWO',

            # Materials
            'LIN', 'APD', 'SHW', 'FCX', 'NEM', 'DOW', 'ECL', 'DD',

            # Real Estate
            'PLD', 'AMT', 'CCI', 'EQIX', 'SPG', 'O',

            # Utilities
            'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE',
        ]
        
        # 중복 제거 (순서 보존)
        sp500 = list(dict.fromkeys(sp500))
        
        self.cache['SP500'] = sp500
        print(f"[OK] {len(sp500)} symbols loaded")
        
        return sp500
    
    def get_universe(self, market: str) -> List[str]:
        """지정된 시장의 종목 리스트 반환"""
        market = market.upper()
        
        if market == 'NASDAQ100':
            return self.get_nasdaq_100()
        elif market == 'NASDAQ':
            return self.get_nasdaq_composite()
        elif market == 'RUSSELL2000' or market == 'RUSSELL':
            return self.get_russell_2000()
        elif market == 'SP500':
            return self.get_sp500()
        else:
            raise ValueError(f"Unsupported market: {market}")
    
    def get_market_stats(self, market: str) -> Dict:
        """시장 통계 정보"""
        symbols = self.get_universe(market)
        
        return {
            'market': market,
            'total_symbols': len(symbols),
            'sample_symbols': symbols[:5]
        }


# Helper functions for quick access
def load_nasdaq100():
    """NASDAQ-100 종목 리스트 반환"""
    universe = MarketUniverse()
    return universe.get_nasdaq_100()


def load_sp500():
    """S&P 500 종목 리스트 반환"""
    universe = MarketUniverse()
    return universe.get_sp500()


def load_nasdaq_composite():
    """NASDAQ 종합 지수 종목 리스트 반환"""
    universe = MarketUniverse()
    return universe.get_nasdaq_composite()


def load_russell2000():
    """Russell 2000 종목 리스트 반환"""
    universe = MarketUniverse()
    return universe.get_russell_2000()


def main():
    """테스트 실행"""
    universe = MarketUniverse()
    
    print("\n" + "="*70)
    print("Market Universe Loader - Test")
    print("="*70 + "\n")
    
    # 각 시장 테스트
    markets = ['NASDAQ100', 'NASDAQ', 'RUSSELL2000', 'SP500']
    
    for market in markets:
        print(f"\n{market}:")
        symbols = universe.get_universe(market)
        print(f"  Total: {len(symbols)} symbols")
        print(f"  Sample: {', '.join(symbols[:10])}")
        print()
    
    print("="*70)


if __name__ == "__main__":
    main()
