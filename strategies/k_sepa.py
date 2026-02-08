"""
K-SEPA Strategy (Korean Market Optimized SEPA)
한국 시장 최적화 마크 미너비니 전략

한국 시장 특성:
- 120일/240일선 중시 (반기/연간 결산 심리)
- 높은 거래량 폭증 요구 (3배 = 300%)
- VCP 거래량 절벽 (30% 이하로 수축)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from .base_strategy import BaseStrategy


class KSEPAStrategy(BaseStrategy):
    """한국형 SEPA 전략 (K-Edition)"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            # 이동평균선 (한국 시장 기준)
            'sma_short': 50,              # 50일선
            'sma_mid': 120,               # 120일선 (반기)
            'sma_long': 240,              # 240일선 (1년)
            
            # 트렌드 템플릿
            'sma_slope_days': 20,         # 장기선 기울기 판단 기간
            'new_high_threshold': 0.25,   # 신고가 -25% 이내
            'high_lookback': 252,         # 52주 = 252거래일
            
            # VCP 패턴
            'vcp_volatility_window': 30,  # 변동성 수축 판단 기간
            'vcp_recent_window': 10,      # 최근 구간
            'volume_dry_up': 0.3,         # 거래량 30% 이하로 감소
            'volume_lookback': 50,        # 평균 거래량 기간
            
            # 피벗 돌파
            'pivot_lookback': 10,         # 피벗 가격 탐지 기간
            'pivot_proximity': 0.97,      # 피벗 근접 (97%)
            'volume_surge': 3.0,          # 거래량 3배 폭증 (한국형)
            'volume_surge_window': 20,    # 거래량 평균 기간
            
            # 리스크 관리
            'stop_loss': 0.07,            # 손절 7%
            'take_profit': 0.21,          # 익절 21% (3:1 손익비)
        }
        if params:
            default_params.update(params)
        
        super().__init__("K-SEPA (Korean)", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """한국형 지표 계산"""
        df = data.copy()
        
        # 이동평균선
        df['sma50'] = df['Close'].rolling(window=self.params['sma_short']).mean()
        df['sma120'] = df['Close'].rolling(window=self.params['sma_mid']).mean()
        df['sma240'] = df['Close'].rolling(window=self.params['sma_long']).mean()
        
        # 52주 고점
        df['high_52w'] = df['Close'].rolling(window=self.params['high_lookback']).max()
        
        # 평균 거래량
        df['volume_avg_50'] = df['Volume'].rolling(window=self.params['volume_lookback']).mean()
        df['volume_avg_20'] = df['Volume'].rolling(window=self.params['volume_surge_window']).mean()
        
        return df
    
    def check_k_trend_template(self, df: pd.DataFrame, idx: int) -> bool:
        """
        1단계: 한국형 트렌드 템플릿 검증
        
        조건:
        1. 이평선 정배열: 주가 > 50일 > 120일 > 240일
        2. 240일선 우상향 (20일 전보다 높음)
        3. 52주 고점 대비 -25% 이내
        """
        if idx < self.params['sma_long']:
            return False
        
        row = df.iloc[idx]
        
        # NaN 체크
        if pd.isna(row['sma50']) or pd.isna(row['sma120']) or pd.isna(row['sma240']):
            return False
        
        # 1. 이평선 정배열
        is_aligned = (
            row['Close'] > row['sma50'] > row['sma120'] > row['sma240']
        )
        
        # 2. 240일선 우상향
        slope_days = self.params['sma_slope_days']
        if idx < slope_days:
            return False
        
        is_sma240_up = row['sma240'] > df.iloc[idx - slope_days]['sma240']
        
        # 3. 신고가 인근 (52주 고점 대비 -25% 이내)
        if pd.isna(row['high_52w']):
            return False
        
        is_near_high = row['Close'] >= row['high_52w'] * (1 - self.params['new_high_threshold'])
        
        return is_aligned and is_sma240_up and is_near_high
    
    def analyze_vcp_pattern(self, df: pd.DataFrame, idx: int) -> tuple:
        """
        2단계: VCP (변동성 수축) 및 거래량 절벽 분석
        
        Returns:
            (pivot_price, is_vcp_ready)
        """
        vcp_window = self.params['vcp_volatility_window']
        recent_window = self.params['vcp_recent_window']
        
        if idx < vcp_window:
            return 0, False
        
        # 최근 구간 vs 이전 구간 변동성 비교
        recent_data = df.iloc[idx - recent_window + 1:idx + 1]
        prev_data = df.iloc[idx - vcp_window + 1:idx - recent_window + 1]
        
        volatility_recent = (recent_data['High'].max() - recent_data['Low'].min()) / recent_data['Low'].min()
        volatility_prev = (prev_data['High'].max() - prev_data['Low'].min()) / prev_data['Low'].min()
        
        # 변동성 수축
        is_contracting = volatility_recent < volatility_prev
        
        # 거래량 절벽 (Volume Dry-up)
        avg_vol_50 = df.iloc[idx - self.params['volume_lookback']:idx]['Volume'].mean()
        last_vol_min = df.iloc[idx - 4:idx + 1]['Volume'].min()
        
        is_dry_up = last_vol_min < (avg_vol_50 * self.params['volume_dry_up'])
        
        # 피벗 가격 (최근 10일 고점)
        pivot_lookback = self.params['pivot_lookback']
        pivot_price = df.iloc[idx - pivot_lookback:idx]['High'].max()
        
        is_vcp_ready = is_contracting and is_dry_up
        
        return pivot_price, is_vcp_ready
    
    def check_k_strike(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        3단계: K-STRIKE (격발 신호)
        
        조건:
        1. 피벗 가격 돌파 (종가 기준)
        2. 거래량 300% 폭증 (한국형 수급)
        3. VCP 준비 완료
        """
        # 트렌드 템플릿 미달 시 탈락
        if not self.check_k_trend_template(df, idx):
            return None
        
        pivot_price, vcp_ready = self.analyze_vcp_pattern(df, idx)
        
        if pivot_price == 0:
            return None
        
        row = df.iloc[idx]
        avg_vol_20 = df.iloc[idx - self.params['volume_surge_window']:idx]['Volume'].mean()
        
        # 격발 조건
        is_pivot_break = row['Close'] > pivot_price
        is_volume_surge = row['Volume'] > (avg_vol_20 * self.params['volume_surge'])
        
        # K-STRIKE (격발)
        if is_pivot_break and is_volume_surge and vcp_ready:
            return {
                'date': row.name,
                'type': 'BUY',
                'price': row['Close'],
                'stop_loss': row['Close'] * (1 - self.params['stop_loss']),
                'take_profit': row['Close'] * (1 + self.params['take_profit']),
                'reason': f"[K-STRIKE] Pivot breakout + Volume surge ({row['Volume']/avg_vol_20:.1f}x)",
                'confidence': self._calculate_confidence(df, idx, vcp_ready, row['Volume']/avg_vol_20),
                'metrics': {
                    'pivot': pivot_price,
                    'volume_ratio': row['Volume'] / avg_vol_20,
                    'vcp_ready': vcp_ready,
                    'sma50': row['sma50'],
                    'sma120': row['sma120'],
                    'sma240': row['sma240']
                }
            }
        
        # VCP 대기 상태
        elif vcp_ready and row['Close'] >= pivot_price * self.params['pivot_proximity']:
            return {
                'date': row.name,
                'type': 'WATCH',
                'price': row['Close'],
                'reason': f"[K-VCP WATCH] Near pivot ({pivot_price:.0f})",
                'confidence': 0.5,
                'metrics': {
                    'pivot': pivot_price,
                    'proximity': row['Close'] / pivot_price
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
        
        min_idx = self.params['sma_long'] + self.params['vcp_volatility_window']
        
        for i in range(min_idx, len(df)):
            row = df.iloc[i]
            
            # 매수 신호 체크
            if position is None:
                signal = self.check_k_strike(df, i)
                if signal and signal['type'] == 'BUY':
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
            
            # 매도 신호 체크
            elif position == 'LONG':
                curr_price = row['Close']
                
                # 1. 손절 (7%)
                if curr_price <= entry_price * (1 - self.params['stop_loss']):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"Stop loss ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0
                
                # 2. 익절 (21%)
                elif curr_price >= entry_price * (1 + self.params['take_profit']):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"Take profit ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0
                
                # 3. 트렌드 붕괴 (50일선 하회)
                elif curr_price < row['sma50']:
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"Trend break (Below SMA50) ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 0.9
                    })
                    position = None
                    entry_price = 0
        
        return signals
    
    def _calculate_confidence(self, df: pd.DataFrame, idx: int, vcp_ready: bool, vol_ratio: float) -> float:
        """
        신호 신뢰도 계산 (0~1)
        
        기준:
        - VCP 준비 여부
        - 거래량 폭증 강도
        - 이평선 간격
        """
        row = df.iloc[idx]
        
        # VCP 가중치
        vcp_weight = 1.0 if vcp_ready else 0.5
        
        # 거래량 가중치 (3배 기준, 최대 1.0)
        vol_weight = min(1.0, (vol_ratio - 1) / 5)
        
        # 이평선 간격 가중치 (넓을수록 강함)
        if row['sma240'] > 0:
            sma_spacing = (row['sma50'] - row['sma240']) / row['sma240']
            spacing_weight = min(1.0, sma_spacing * 10)
        else:
            spacing_weight = 0.5
        
        # 종합 신뢰도
        confidence = vcp_weight * 0.4 + vol_weight * 0.4 + spacing_weight * 0.2
        
        return max(0.0, min(1.0, confidence))
