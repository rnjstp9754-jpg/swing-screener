"""
Base Strategy Class

모든 스윙매매 전략의 베이스 클래스입니다.
새로운 전략을 만들 때 이 클래스를 상속받아 구현하세요.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd


class BaseStrategy(ABC):
    """전략 베이스 클래스"""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        Args:
            name: 전략 이름
            params: 전략 파라미터 딕셔너리
        """
        self.name = name
        self.params = params or {}
        self.signals = []
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        매수/매도 신호 생성
        
        Args:
            data: OHLCV 데이터프레임
                - Columns: Date, Open, High, Low, Close, Volume
        
        Returns:
            신호 리스트, 각 신호는 다음 형식:
            {
                'date': '2024-01-01',
                'type': 'BUY' or 'SELL',
                'price': 100000,
                'reason': '신호 발생 이유',
                'confidence': 0.8  # 신뢰도 (0~1)
            }
        """
        pass
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 계산 (선택사항)
        
        Args:
            data: OHLCV 데이터프레임
        
        Returns:
            지표가 추가된 데이터프레임
        """
        return data
    
    def validate_signal(self, signal: Dict, data: pd.DataFrame) -> bool:
        """
        신호 유효성 검증 (선택사항)
        
        Args:
            signal: 검증할 신호
            data: OHLCV 데이터
        
        Returns:
            유효하면 True, 아니면 False
        """
        return True
    
    def get_position_size(self, capital: float, price: float) -> int:
        """
        포지션 크기 계산 (선택사항)
        
        Args:
            capital: 현재 자본
            price: 현재 가격
        
        Returns:
            매수할 주식 수량
        """
        max_position = capital * self.params.get('max_position_size', 0.2)
        shares = int(max_position / price)
        return shares
    
    def get_stop_loss(self, entry_price: float) -> float:
        """
        손절가 계산
        
        Args:
            entry_price: 진입 가격
        
        Returns:
            손절 가격
        """
        stop_loss_pct = self.params.get('stop_loss', 0.05)
        return entry_price * (1 - stop_loss_pct)
    
    def get_take_profit(self, entry_price: float) -> float:
        """
        익절가 계산
        
        Args:
            entry_price: 진입 가격
        
        Returns:
            익절 가격
        """
        take_profit_pct = self.params.get('take_profit', 0.15)
        return entry_price * (1 + take_profit_pct)
    
    def __str__(self):
        return f"{self.name} Strategy"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
