"""
Aggressive SEPA 2026 Strategy
2026년형 고변동성 장세 최적화 전략

특징:
- Minervini SEPA (진입) + Weinstein Stage 2 (추세)
- 가변형 트레일링 스탑 (수익 구간별 차등 적용)
- 2025-26 변동성 반영
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from .base_strategy import BaseStrategy


class AggressiveSEPAStrategy(BaseStrategy):
    """2026년형 공격적 SEPA 전략"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            # 이동평균선
            'sma_short': 50,
            'sma_mid': 150,
            'sma_long': 200,
            'ema_fast': 10,               # 트레일링용 EMA
            'ema_slow': 20,               # 트레일링용 EMA
            
            # 트렌드 템플릿
            'sma_slope_days': 20,
            
            # VCP 패턴 (완화)
            'vcp_threshold': 0.08,        # 8% 이내 수축
            'vcp_lookback': 10,           # 최근 10일
            'volume_dry_up': 0.5,         # 거래량 50% 감소
            'volume_lookback': 50,
            
            # 피벗 돌파 (완화)
            'pivot_lookback': 10,
            'volume_surge': 1.5,          # 1.5배 = 150% 폭증
            'volume_surge_window': 50,
            
            # 리스크 관리
            'initial_stop_loss': 0.08,    # 초기 손절 8%
            
            # 트레일링 스탑 (수익 구간별)
            'profit_tier1': 0.15,         # 15% 수익 (Tier 1)
            'profit_tier2': 0.50,         # 50% 수익 (Tier 2: 슈퍼퍼포머)
        }
        if params:
            default_params.update(params)
        
        super().__init__("Aggressive SEPA 2026", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """지표 계산"""
        df = data.copy()
        
        # 이동평균선
        df['sma50'] = df['Close'].rolling(window=self.params['sma_short']).mean()
        df['sma150'] = df['Close'].rolling(window=self.params['sma_mid']).mean()
        df['sma200'] = df['Close'].rolling(window=self.params['sma_long']).mean()
        
        # EMA (트레일링용)
        df['ema10'] = df['Close'].ewm(span=self.params['ema_fast'], adjust=False).mean()
        df['ema20'] = df['Close'].ewm(span=self.params['ema_slow'], adjust=False).mean()
        
        # 평균 거래량
        df['volume_avg'] = df['Volume'].rolling(window=self.params['volume_lookback']).mean()
        
        return df
    
    def check_trend_template(self, df: pd.DataFrame, idx: int) -> bool:
        """
        트렌드 템플릿 검증 (Minervini + Weinstein)
        
        조건:
        1. 이평선 정배열: 50 > 150 > 200
        2. 200일선 우상향
        3. Stage 2: 주가 > 150일선
        """
        if idx < self.params['sma_long']:
            return False
        
        row = df.iloc[idx]
        
        if pd.isna(row['sma50']) or pd.isna(row['sma150']) or pd.isna(row['sma200']):
            return False
        
        # 1. 이평선 정배열
        is_aligned = row['sma50'] > row['sma150'] > row['sma200']
        
        # 2. 200일선 우상향
        slope_days = self.params['sma_slope_days']
        if idx < slope_days:
            return False
        
        is_sma200_up = row['sma200'] > df.iloc[idx - slope_days]['sma200']
        
        # 3. Stage 2 (주가 > 150일선)
        is_stage2 = row['Close'] > row['sma150']
        
        return is_aligned and is_sma200_up and is_stage2
    
    def detect_vcp(self, df: pd.DataFrame, idx: int) -> bool:
        """
        VCP 수축 및 거래량 절벽 감지
        
        Returns:
            VCP 패턴 준비 여부
        """
        vcp_lookback = self.params['vcp_lookback']
        
        if idx < vcp_lookback + 1:
            return False
        
        # 최근 10일 변동성 (타이트함)
        recent_data = df.iloc[idx - vcp_lookback + 1:idx + 1]
        volatility = (recent_data['High'].max() - recent_data['Low'].min()) / recent_data['Low'].min()
        
        is_tight = volatility <= self.params['vcp_threshold']
        
        # 거래량 절벽 (최근 3일 평균 < 50일 평균의 50%)
        recent_vol = df.iloc[idx - 2:idx + 1]['Volume'].mean()
        avg_vol = df.iloc[idx - self.params['volume_lookback']:idx]['Volume'].mean()
        
        is_vol_dry = recent_vol < avg_vol * self.params['volume_dry_up']
        
        return is_tight and is_vol_dry
    
    def check_strike_signal(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        STRIKE 신호 (격발)
        
        조건:
        1. 트렌드 템플릿 만족
        2. VCP 준비 완료
        3. 피벗 돌파
        4. 거래량 폭증 (1.5배)
        """
        # 트렌드 템플릿 미달 시 탈락
        if not self.check_trend_template(df, idx):
            return None
        
        # VCP 체크
        vcp_ready = self.detect_vcp(df, idx)
        
        # 피벗 가격
        pivot_lookback = self.params['pivot_lookback']
        if idx < pivot_lookback:
            return None
        
        pivot_price = df.iloc[idx - pivot_lookback:idx]['High'].max()
        
        row = df.iloc[idx]
        
        # 거래량 확인
        avg_vol = df.iloc[idx - self.params['volume_surge_window']:idx]['Volume'].mean()
        is_volume_surge = row['Volume'] > avg_vol * self.params['volume_surge']
        
        # 피벗 돌파 확인
        is_pivot_break = row['Close'] > pivot_price
        
        # STRIKE!
        if vcp_ready and is_pivot_break and is_volume_surge:
            return {
                'date': row.name,
                'type': 'BUY',
                'price': row['Close'],
                'stop_loss': row['Close'] * (1 - self.params['initial_stop_loss']),
                'reason': f"[STRIKE] Pivot break + Volume surge ({row['Volume']/avg_vol:.1f}x)",
                'confidence': self._calculate_confidence(vcp_ready, row['Volume']/avg_vol),
                'metrics': {
                    'pivot': pivot_price,
                    'volume_ratio': row['Volume'] / avg_vol,
                    'vcp_ready': vcp_ready,
                    'sma50': row['sma50'],
                    'sma150': row['sma150'],
                    'sma200': row['sma200']
                }
            }
        
        return None
    
    def manage_exit_logic(
        self,
        df: pd.DataFrame,
        idx: int,
        entry_price: float
    ) -> Optional[Dict]:
        """
        트레일링 스탑 (수익 구간별 차등 적용)
        
        구간:
        - Tier 2 (50%+): EMA10 이탈 시 매도 (슈퍼퍼포머)
        - Tier 1 (15~50%): EMA20 이탈 시 매도 (가속)
        - 초기 (0~15%): 고정 손절 8%
        """
        row = df.iloc[idx]
        current_price = row['Close']
        
        # 수익률 계산
        profit_pct = (current_price - entry_price) / entry_price
        
        # Tier 2: 슈퍼퍼포머 (50% 이상)
        if profit_pct >= self.params['profit_tier2']:
            if pd.notna(row['ema10']) and current_price < row['ema10']:
                return {
                    'date': row.name,
                    'type': 'SELL',
                    'price': current_price,
                    'reason': f"[STRONG SELL] EMA10 break - Lock profit ({profit_pct*100:.1f}%)",
                    'confidence': 1.0,
                    'profit_pct': profit_pct
                }
        
        # Tier 1: 가속 구간 (15~50%)
        elif profit_pct >= self.params['profit_tier1']:
            if pd.notna(row['ema20']) and current_price < row['ema20']:
                return {
                    'date': row.name,
                    'type': 'SELL',
                    'price': current_price,
                    'reason': f"[SELL] EMA20 break - Trend end ({profit_pct*100:.1f}%)",
                    'confidence': 0.9,
                    'profit_pct': profit_pct
                }
        
        # 초기 구간: 고정 손절
        else:
            stop_price = entry_price * (1 - self.params['initial_stop_loss'])
            if current_price <= stop_price:
                return {
                    'date': row.name,
                    'type': 'SELL',
                    'price': current_price,
                    'reason': f"[STOP LOSS] Initial risk defense ({profit_pct*100:.1f}%)",
                    'confidence': 1.0,
                    'profit_pct': profit_pct
                }
        
        # 보유 유지
        return None
    
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """매수/매도 신호 생성 (트레일링 스탑 포함)"""
        # 지표 계산
        df = self.calculate_indicators(data)
        
        signals = []
        position = None
        entry_price = 0
        
        min_idx = self.params['sma_long'] + self.params['vcp_lookback']
        
        for i in range(min_idx, len(df)):
            # 매수 신호 체크
            if position is None:
                signal = self.check_strike_signal(df, i)
                if signal:
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
            
            # 매도 신호 체크 (트레일링 스탑)
            elif position == 'LONG':
                exit_signal = self.manage_exit_logic(df, i, entry_price)
                if exit_signal:
                    signals.append(exit_signal)
                    position = None
                    entry_price = 0
        
        return signals
    
    def _calculate_confidence(self, vcp_ready: bool, vol_ratio: float) -> float:
        """
        신호 신뢰도 계산
        
        기준:
        - VCP 준비 여부
        - 거래량 폭증 강도
        """
        vcp_weight = 1.0 if vcp_ready else 0.5
        vol_weight = min(1.0, (vol_ratio - 1) / 3)
        
        confidence = vcp_weight * 0.6 + vol_weight * 0.4
        
        return max(0.0, min(1.0, confidence))
