"""
SEPA (Specific Entry Point Analysis) Strategy
마크 미너비니의 트렌드 템플릿 + VCP 패턴 전략

핵심 개념:
1. 트렌드 템플릿: 이동평균선 정배열 + 200일선 우상향 + 신고가 근접
2. VCP (Volatility Contraction Pattern): 변동성 수축 패턴
3. 피벗 돌파: 거래량 폭증과 함께 고점 돌파
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from .base_strategy import BaseStrategy


class SEPAStrategy(BaseStrategy):
    """마크 미너비니 SEPA 전략"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'risk_reward_ratio': 3,
            'stop_loss': 0.07,      # 손절 7% (미너비니 7-8% 룰)
            'take_profit': 0.21,    # 익절 21% (3:1 손익비)
            'sma_periods': {
                'short': 50,
                'medium': 150,
                'long': 200
            },
            'new_high_threshold': 0.25,  # 신고가 대비 -25% 이내
            'volume_surge': 1.5,          # 거래량 50% 폭증
            'volume_dry_up': 0.6,         # 거래량 40% 감소
            'pivot_lookback': 10,         # 피벗 탐지 기간
        }
        if params:
            default_params.update(params)
        
        super().__init__("SEPA (Minervini)", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 및 필요한 지표 계산"""
        df = data.copy()
        
        # 이동평균선
        df['sma50'] = df['Close'].rolling(window=self.params['sma_periods']['short']).mean()
        df['sma150'] = df['Close'].rolling(window=self.params['sma_periods']['medium']).mean()
        df['sma200'] = df['Close'].rolling(window=self.params['sma_periods']['long']).mean()
        
        # 52주 신고가
        df['high_52w'] = df['Close'].rolling(window=252).max()
        
        # 평균 거래량 (50일)
        df['volume_avg_50'] = df['Volume'].rolling(window=50).mean()
        
        # 최근 고점 (피벗 포인트)
        df['recent_high'] = df['High'].rolling(window=self.params['pivot_lookback']).max()
        
        return df
    
    def check_trend_template(self, df: pd.DataFrame, idx: int) -> bool:
        """
        1단계: 트렌드 템플릿 검증
        
        조건:
        - 50일 > 150일 > 200일 이동평균선 (정배열)
        - 200일선이 우상향 (20일 전보다 높음)
        - 현재가가 52주 신고가 대비 -25% 이내
        """
        if idx < 200:  # 충분한 데이터 확보
            return False
        
        row = df.iloc[idx]
        
        # 이동평균선 정배열 확인
        if pd.isna(row['sma50']) or pd.isna(row['sma150']) or pd.isna(row['sma200']):
            return False
        
        if not (row['sma50'] > row['sma150'] > row['sma200']):
            return False
        
        # 200일선 우상향 확인 (20일 전보다 높아야 함)
        if idx >= 20:
            sma200_prev = df.iloc[idx - 20]['sma200']
            if not (row['sma200'] > sma200_prev):
                return False
        
        # 신고가 근접성 확인
        if pd.isna(row['high_52w']):
            return False
        
        threshold = row['high_52w'] * (1 - self.params['new_high_threshold'])
        if row['Close'] < threshold:
            return False
        
        return True
    
    def detect_vcp_pivot(self, df: pd.DataFrame, idx: int) -> Tuple[float, bool]:
        """
        2단계: VCP (Volatility Contraction Pattern) 및 피벗 탐지
        
        VCP 조건:
        - 최근 5~10일간 거래량이 평균 대비 40% 이상 감소 (거래량 증발)
        - 가격 변동성 수축
        
        Returns:
            (피벗_가격, 거래량_증발_여부)
        """
        if idx < 50:
            return 0.0, False
        
        # 최근 5일 평균 거래량 vs 50일 평균 거래량
        recent_vol_avg = df['Volume'].iloc[idx-5:idx+1].mean()
        baseline_vol_avg = df.iloc[idx]['volume_avg_50']
        
        # 거래량 증발 확인 (40% 이상 감소)
        vol_dry_up = recent_vol_avg < baseline_vol_avg * self.params['volume_dry_up']
        
        # 피벗 포인트 (최근 10일간의 최고가)
        pivot_price = df.iloc[idx]['recent_high']
        
        return pivot_price, vol_dry_up
    
    def check_strike(self, df: pd.DataFrame, idx: int) -> Dict:
        """
        3단계: 최종 격발 신호 (STRIKE)
        
        조건:
        - 트렌드 템플릿 통과
        - 피벗 포인트 돌파
        - 거래량 50% 폭증
        - 선행 거래량 증발
        
        Returns:
            신호 정보 또는 None
        """
        # 트렌드 템플릿 검증
        if not self.check_trend_template(df, idx):
            return None
        
        # VCP 및 피벗 탐지
        pivot_price, vol_dry_up = self.detect_vcp_pivot(df, idx)
        
        if pivot_price == 0.0:
            return None
        
        row = df.iloc[idx]
        curr_price = row['Close']
        curr_vol = row['Volume']
        avg_vol = row['volume_avg_50']
        
        # 격발 조건 체크
        # 1. 피벗 돌파
        pivot_breakout = curr_price > pivot_price
        
        # 2. 거래량 폭증 (50% 이상)
        volume_surge = curr_vol > avg_vol * self.params['volume_surge']
        
        # 3. 선행 거래량 증발 (VCP 패턴)
        if pivot_breakout and volume_surge and vol_dry_up:
            stop_loss_price = curr_price * (1 - self.params['stop_loss'])
            take_profit_price = curr_price * (1 + self.params['take_profit'])
            
            return {
                'date': row.name,
                'type': 'BUY',
                'price': curr_price,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'reason': f"🚀 SEPA STRIKE - 피벗돌파({pivot_price:.0f}) + 거래량폭증({curr_vol/avg_vol:.1f}x) + VCP",
                'confidence': self._calculate_confidence(df, idx),
                'metrics': {
                    'pivot_price': pivot_price,
                    'volume_ratio': curr_vol / avg_vol,
                    'distance_from_52w_high': (curr_price / row['high_52w'] - 1) * 100,
                    'sma_alignment': f"{row['sma50']:.0f} > {row['sma150']:.0f} > {row['sma200']:.0f}"
                }
            }
        
        return None
    
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """매수/매도 신호 생성"""
        # 지표 계산
        df = self.calculate_indicators(data)
        
        signals = []
        position = None
        entry_price = 0
        
        for i in range(200, len(df)):  # 200일 이후부터 시작 (이동평균선 확보)
            row = df.iloc[i]
            
            # 매수 신호 체크
            if position is None:
                signal = self.check_strike(df, i)
                if signal:
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
            
            # 매도 신호 체크 (손절 또는 익절)
            elif position == 'LONG':
                curr_price = row['Close']
                stop_loss = entry_price * (1 - self.params['stop_loss'])
                take_profit = entry_price * (1 + self.params['take_profit'])
                
                # 손절
                if curr_price <= stop_loss:
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"손절 ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0
                
                # 익절
                elif curr_price >= take_profit:
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"익절 ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0
                
                # 트렌드 템플릿 깨짐 (이동평균선 역배열)
                elif not self.check_trend_template(df, i):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"트렌드 템플릿 이탈 ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 0.8
                    })
                    position = None
                    entry_price = 0
        
        return signals
    
    def _calculate_confidence(self, df: pd.DataFrame, idx: int) -> float:
        """
        신호 신뢰도 계산 (0~1)
        
        기준:
        - 신고가에 가까울수록 높음
        - 이동평균선 간격이 넓을수록 높음
        - 거래량 폭증이 클수록 높음
        """
        row = df.iloc[idx]
        
        # 신고가 근접도 (0~1)
        high_proximity = row['Close'] / row['high_52w']
        
        # 이동평균선 정렬 강도 (간격)
        ma_spread = (row['sma50'] - row['sma200']) / row['sma200']
        ma_strength = min(1.0, ma_spread * 10)
        
        # 거래량 배수
        vol_strength = min(1.0, (row['Volume'] / row['volume_avg_50'] - 1) / 2)
        
        # 종합 신뢰도
        confidence = (high_proximity * 0.4 + ma_strength * 0.3 + vol_strength * 0.3)
        
        return max(0.0, min(1.0, confidence))
