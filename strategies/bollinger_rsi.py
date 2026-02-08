"""
Bollinger Bands + RSI Strategy

볼린저밴드 하단 터치 + RSI 과매도 조건에서 매수,
볼린저밴드 상단 터치 + RSI 과매수 조건에서 매도하는 전략
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from .base_strategy import BaseStrategy


class BollingerRSIStrategy(BaseStrategy):
    """볼린저밴드 + RSI 전략"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'stop_loss': 0.05,
            'take_profit': 0.15
        }
        if params:
            default_params.update(params)
        
        super().__init__("Bollinger+RSI", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """볼린저밴드와 RSI 계산"""
        df = data.copy()
        
        # 볼린저밴드
        bb_period = self.params['bb_period']
        bb_std = self.params['bb_std']
        
        df['BB_Middle'] = df['Close'].rolling(window=bb_period).mean()
        df['BB_Std'] = df['Close'].rolling(window=bb_period).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * df['BB_Std'])
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * df['BB_Std'])
        
        # RSI
        rsi_period = self.params['rsi_period']
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """매수/매도 신호 생성"""
        # 지표 계산
        df = self.calculate_indicators(data)
        
        signals = []
        position = None  # 현재 포지션 (None, 'LONG')
        
        for i in range(len(df)):
            if i < self.params['bb_period']:  # 충분한 데이터가 있을 때까지 대기
                continue
            
            row = df.iloc[i]
            prev_row = df.iloc[i-1] if i > 0 else None
            
            # 매수 신호
            if (position is None and 
                row['Close'] <= row['BB_Lower'] and 
                row['RSI'] <= self.params['rsi_oversold']):
                
                signals.append({
                    'date': row.name,
                    'type': 'BUY',
                    'price': row['Close'],
                    'reason': f"BB하단터치({row['Close']:.0f} <= {row['BB_Lower']:.0f}) + RSI과매도({row['RSI']:.1f})",
                    'confidence': self._calculate_confidence(row, 'BUY')
                })
                position = 'LONG'
            
            # 매도 신호
            elif (position == 'LONG' and 
                  (row['Close'] >= row['BB_Upper'] or 
                   row['RSI'] >= self.params['rsi_overbought'])):
                
                signals.append({
                    'date': row.name,
                    'type': 'SELL',
                    'price': row['Close'],
                    'reason': f"BB상단터치 또는 RSI과매수({row['RSI']:.1f})",
                    'confidence': self._calculate_confidence(row, 'SELL')
                })
                position = None
        
        return signals
    
    def _calculate_confidence(self, row: pd.Series, signal_type: str) -> float:
        """신호 신뢰도 계산 (0~1)"""
        if signal_type == 'BUY':
            # BB 하단에서 멀수록, RSI가 낮을수록 신뢰도 높음
            bb_distance = (row['BB_Lower'] - row['Close']) / row['Close']
            rsi_strength = (self.params['rsi_oversold'] - row['RSI']) / self.params['rsi_oversold']
            confidence = min(1.0, (bb_distance * 10 + rsi_strength) / 2)
        else:  # SELL
            bb_distance = (row['Close'] - row['BB_Upper']) / row['Close']
            rsi_strength = (row['RSI'] - self.params['rsi_overbought']) / (100 - self.params['rsi_overbought'])
            confidence = min(1.0, (bb_distance * 10 + rsi_strength) / 2)
        
        return max(0.0, confidence)
