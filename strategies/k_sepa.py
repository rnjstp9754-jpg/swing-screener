"""
K-Minervini Hunter Pro Strategy
한국 시장 전용 마크 미너비니 SEPA 엔진

특징:
- 240일선(1년선) 정배열 강화
- 한국형 수급 폭발 (3.5배 거래량)
- 변동성 수축(VCP) 및 거래 절벽 포착
- 한국 시장 최적화 수익 보존 엔진
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from .base_strategy import BaseStrategy


class KMinerviniProStrategy(BaseStrategy):
    """한국형 미너비니 프로 전략"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            # 이동평균선 (한국 시장 기준)
            'sma_short': 50,
            'sma_mid': 120,               # 반기선
            'sma_long': 240,              # 1년선 (핵심)
            'ema_fast': 10,               # 트레일링용
            
            # 트렌드 템플릿
            'sma_slope_days': 20,
            'new_high_threshold': 0.25,   # 52주 고점 -25% 이내
            'high_lookback': 252,
            
            # VCP 패턴 (강화)
            'vcp_threshold': 0.07,        # 7% 이내 수축
            'vcp_lookback': 10,
            'volume_dry_up': 0.4,         # 40% 절벽
            'volume_lookback': 50,
            
            # 피벗 돌파 (강화)
            'pivot_lookback': 10,
            'volume_surge': 3.5,          # 3.5배 폭증 (한국형)
            'volume_surge_window': 20,
            
            # 리스크 관리
            'stop_loss': 0.07,            # 손절 7%
            'take_profit': 0.25,          # 익절 25% (한국 기준)
            
            # 트레일링 스탑
            'profit_surge': 0.30,         # 30% 수익 (급등)
            'profit_safe': 0.10,          # 10% 수익 (본절 보호)
            'safe_zone': 0.02,            # 본절 +2%
        }
        if params:
            default_params.update(params)
        
        super().__init__("K-Minervini Pro", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """한국형 지표 계산"""
        df = data.copy()
        
        # 이동평균선
        df['sma50'] = df['Close'].rolling(window=self.params['sma_short']).mean()
        df['sma120'] = df['Close'].rolling(window=self.params['sma_mid']).mean()
        df['sma240'] = df['Close'].rolling(window=self.params['sma_long']).mean()
        
        # EMA (트레일링용)
        df['ema10'] = df['Close'].ewm(span=self.params['ema_fast'], adjust=False).mean()
        
        # 52주 고점
        df['high_52w'] = df['Close'].rolling(window=self.params['high_lookback']).max()
        
        # 평균 거래량
        df['volume_avg_50'] = df['Volume'].rolling(window=self.params['volume_lookback']).mean()
        df['volume_avg_20'] = df['Volume'].rolling(window=self.params['volume_surge_window']).mean()
        
        return df
    
    def check_k_trend_template(self, df: pd.DataFrame, idx: int) -> bool:
        """
        한국형 트렌드 템플릿 (240일선 정배열)
        
        조건:
        1. 이평선 정배열: 주가 > 50일 > 120일 > 240일
        2. 240일선 우상향 (기관 매집 확인)
        3. 52주 고점 대비 -25% 이내 (상단 매물 소화)
        """
        if idx < self.params['sma_long']:
            return False
        
        row = df.iloc[idx]
        
        if pd.isna(row['sma50']) or pd.isna(row['sma120']) or pd.isna(row['sma240']):
            return False
        
        # 1. 이평선 정배열 (240일선 강조)
        is_aligned = (
            row['Close'] > row['sma50'] > row['sma120'] > row['sma240']
        )
        
        # 2. 240일선 우상향 (기관 매집)
        slope_days = self.params['sma_slope_days']
        if idx < slope_days:
            return False
        
        is_sma240_up = row['sma240'] > df.iloc[idx - slope_days]['sma240']
        
        # 3. 신고가 근접성 (52주 고점 -25% 이내)
        if pd.isna(row['high_52w']):
            return False
        
        is_near_high = row['Close'] >= row['high_52w'] * (1 - self.params['new_high_threshold'])
        
        return is_aligned and is_sma240_up and is_near_high
    
    def detect_k_vcp(self, df: pd.DataFrame, idx: int) -> tuple:
        """
        한국형 VCP 및 거래 절벽 감지
        
        Returns:
            (pivot_price, is_vcp_ready)
        """
        vcp_lookback = self.params['vcp_lookback']
        
        if idx < vcp_lookback:
            return 0, False
        
        # 최근 10일 고가-저가 변동폭 수축
        recent_data = df.iloc[idx - vcp_lookback + 1:idx + 1]
        volatility = (recent_data['High'].max() - recent_data['Low'].min()) / recent_data['Low'].min()
        
        is_tight = volatility <= self.params['vcp_threshold']
        
        # 거래 절벽 (최근 3일 평균 < 50일 평균 * 40%)
        avg_vol_50 = df.iloc[idx - self.params['volume_lookback']:idx]['Volume'].mean()
        recent_vol_3d = df.iloc[idx - 2:idx + 1]['Volume'].mean()
        
        is_dry_up = recent_vol_3d < (avg_vol_50 * self.params['volume_dry_up'])
        
        # 피벗 가격
        pivot_price = df.iloc[idx - vcp_lookback:idx]['High'].max()
        
        is_vcp_ready = is_tight and is_dry_up
        
        return pivot_price, is_vcp_ready
    
    def check_k_strike(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        K-STRIKE 신호 (격발)
        
        조건:
        1. 트렌드 템플릿 만족
        2. VCP + 거래 절벽 준비 완료
        3. 피벗 돌파
        4. 거래량 3.5배 폭증 (한국형 수급)
        """
        # 트렌드 템플릿 미달 시 탈락
        if not self.check_k_trend_template(df, idx):
            return None
        
        pivot_price, vcp_ready = self.detect_k_vcp(df, idx)
        
        if pivot_price == 0:
            return None
        
        row = df.iloc[idx]
        
        # 거래량 확인
        avg_vol_20 = df.iloc[idx - self.params['volume_surge_window']:idx]['Volume'].mean()
        is_volume_surge = row['Volume'] > (avg_vol_20 * self.params['volume_surge'])
        
        # 피벗 돌파 확인
        is_pivot_break = row['Close'] > pivot_price
        
        # K-STRIKE!
        if vcp_ready and is_pivot_break and is_volume_surge:
            return {
                'date': row.name,
                'type': 'BUY',
                'price': row['Close'],
                'stop_loss': row['Close'] * (1 - self.params['stop_loss']),
                'take_profit': row['Close'] * (1 + self.params['take_profit']),
                'reason': f"[K-STRIKE] Pivot + Volume surge ({row['Volume']/avg_vol_20:.1f}x)",
                'confidence': self._calculate_confidence(vcp_ready, row['Volume']/avg_vol_20),
                'metrics': {
                    'pivot': pivot_price,
                    'volume_ratio': row['Volume'] / avg_vol_20,
                    'vcp_ready': vcp_ready,
                    'sma50': row['sma50'],
                    'sma120': row['sma120'],
                    'sma240': row['sma240']
                }
            }
        
        return None
    
    def k_exit_engine(
        self,
        df: pd.DataFrame,
        idx: int,
        entry_price: float
    ) -> Optional[Dict]:
        """
        한국 시장 최적화 수익 보존 엔진
        
        특징:
        - 30% 수익: EMA10 이탈 시 전량 매도 (급등주)
        - 10% 수익: 본절가(+2%) 방어선 구축
        - 7% 손절
        """
        row = df.iloc[idx]
        current_price = row['Close']
        
        # 수익률 계산
        profit_pct = (current_price - entry_price) / entry_price
        
        # 급등 후 수익 확정 (30% 이상)
        if profit_pct >= self.params['profit_surge']:
            if pd.notna(row['ema10']) and current_price < row['ema10']:
                return {
                    'date': row.name,
                    'type': 'SELL',
                    'price': current_price,
                    'reason': f"[K-EXIT] Surge peak - EMA10 break ({profit_pct*100:.1f}%)",
                    'confidence': 1.0,
                    'profit_pct': profit_pct
                }
        
        # 본절가 보호 (10% 수익 이상)
        elif profit_pct >= self.params['profit_safe']:
            safe_price = entry_price * (1 + self.params['safe_zone'])
            if current_price <= safe_price:
                return {
                    'date': row.name,
                    'type': 'SELL',
                    'price': current_price,
                    'reason': f"[K-SAFE] Protect profit - Below safe zone ({profit_pct*100:.1f}%)",
                    'confidence': 0.9,
                    'profit_pct': profit_pct
                }
        
        # 손절 (7%)
        else:
            stop_price = entry_price * (1 - self.params['stop_loss'])
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
        """매수/매도 신호 생성"""
        # 지표 계산
        df = self.calculate_indicators(data)
        
        signals = []
        position = None
        entry_price = 0
        
        min_idx = self.params['sma_long'] + self.params['vcp_lookback']
        
        for i in range(min_idx, len(df)):
            # 매수 신호 체크
            if position is None:
                signal = self.check_k_strike(df, i)
                if signal:
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
            
            # 매도 신호 체크 (한국형 수익 보존)
            elif position == 'LONG':
                exit_signal = self.k_exit_engine(df, i, entry_price)
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
        
        # 거래량 3.5배 기준
        vol_weight = min(1.0, (vol_ratio - 1) / 5)
        
        confidence = vcp_weight * 0.6 + vol_weight * 0.4
        
        return max(0.0, min(1.0, confidence))
