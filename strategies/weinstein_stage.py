"""
Weinstein Stage Analysis Strategy
스탠 와인스타인의 4단계 사이클 분석

Stage 1: 바닥권 횡보 (Basing)
Stage 2: 상승 추세 (Advancing)
  - Stage 2A: 돌파 격발 (Breakout)
Stage 3: 천정권 횡보 (Topping)
Stage 4: 하락 추세 (Declining)

핵심 개념:
- 30주 이동평균선 기준
- 거래량 확인 (돌파 시 2배 폭증)
- 상대 강도(RS) 비교 (시장 대비 강도)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from .base_strategy import BaseStrategy


class WeinsteinStrategy(BaseStrategy):
    """스탠 와인스타인 스테이지 분석 전략"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'ma_period': 30,              # 30주 이동평균선 (와인스타인 기준)
            'ma_slope_period': 5,         # 이평선 기울기 판단 기간
            'volume_multiplier': 2.0,     # 거래량 폭증 배수
            'volume_lookback': 20,        # 평균 거래량 계산 기간
            'rs_period': 30,              # 상대강도 계산 기간
            'stop_loss': 0.08,            # 손절 8% (30주선 하회 시)
            'take_profit': 0.30,          # 익절 30% (Stage 2 목표)
            'use_weekly': True,           # 주봉 사용 여부
        }
        if params:
            default_params.update(params)
        
        super().__init__("Weinstein Stage", default_params)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """30주 이동평균선 및 필요 지표 계산"""
        df = data.copy()
        
        # 주봉 데이터로 변환 (일봉인 경우)
        if self.params['use_weekly'] and len(df) > 0:
            # 주봉으로 리샘플링
            df_weekly = df.resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            df = df_weekly
        
        # 30주(또는 30일) 이동평균선
        ma_period = self.params['ma_period']
        df['ma30'] = df['Close'].rolling(window=ma_period).mean()
        
        # 이평선 기울기 (최근 5주 vs 현재)
        slope_period = self.params['ma_slope_period']
        df['ma30_slope'] = df['ma30'] - df['ma30'].shift(slope_period)
        
        # 평균 거래량
        vol_lookback = self.params['volume_lookback']
        df['volume_avg'] = df['Volume'].rolling(window=vol_lookback).mean()
        
        # 상대 강도 계산을 위한 베이스라인
        rs_period = self.params['rs_period']
        df['price_change'] = df['Close'] / df['Close'].shift(rs_period)
        
        return df
    
    def calculate_relative_strength(
        self,
        stock_df: pd.DataFrame,
        index_df: pd.DataFrame,
        idx: int
    ) -> float:
        """
        상대 강도(RS) 계산
        
        RS = (종목의 상승률) / (지수의 상승률)
        RS > 1.0 이면 시장 대비 강함
        
        Args:
            stock_df: 종목 데이터
            index_df: 지수 데이터 (S&P500, KOSPI 등)
            idx: 현재 인덱스
        
        Returns:
            상대 강도 값
        """
        rs_period = self.params['rs_period']
        
        if idx < rs_period:
            return 1.0
        
        # 종목 성과
        stock_perf = stock_df.iloc[idx]['Close'] / stock_df.iloc[idx - rs_period]['Close']
        
        # 지수 성과 (간단히 종목 데이터 자체 사용, 실제로는 별도 지수 필요)
        # TODO: 실제 구현 시 S&P500, KOSPI 지수 데이터 연동
        index_perf = 1.0  # 임시로 1.0 사용
        
        if index_perf == 0:
            return stock_perf
        
        rs = stock_perf / index_perf
        return rs
    
    def detect_stage(self, df: pd.DataFrame, idx: int) -> str:
        """
        현재 스테이지 판별
        
        Returns:
            'STAGE_1', 'STAGE_2', 'STAGE_2A', 'STAGE_3', 'STAGE_4', 'UNKNOWN'
        """
        if idx < self.params['ma_period']:
            return 'UNKNOWN'
        
        row = df.iloc[idx]
        
        if pd.isna(row['ma30']) or pd.isna(row['ma30_slope']):
            return 'UNKNOWN'
        
        # 30주선 대비 위치
        is_above_ma = row['Close'] > row['ma30']
        
        # 30주선 기울기
        is_ma_rising = row['ma30_slope'] > 0
        
        # 거래량 폭증
        vol_multiplier = self.params['volume_multiplier']
        is_vol_burst = row['Volume'] > row['volume_avg'] * vol_multiplier
        
        # Stage 판별
        if is_above_ma and is_ma_rising:
            if is_vol_burst:
                return 'STAGE_2A'  # 격발 돌파
            return 'STAGE_2'  # 상승 추세
        elif is_above_ma and not is_ma_rising:
            return 'STAGE_3'  # 천정권 횡보
        elif not is_above_ma and not is_ma_rising:
            return 'STAGE_4'  # 하락 추세
        elif not is_above_ma and is_ma_rising:
            return 'STAGE_1'  # 바닥권 횡보 (회복 시작)
        
        return 'UNKNOWN'
    
    def check_stage_2_entry(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        Stage 2 진입 신호 확인
        
        조건:
        1. 30주선 위에 있음
        2. 30주선이 우상향
        3. 거래량 폭증 (2배 이상)
        4. 상대 강도가 강함 (RS > 1.0)
        
        Returns:
            신호 정보 또는 None
        """
        if idx < self.params['ma_period'] + self.params['ma_slope_period']:
            return None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1] if idx > 0 else None
        
        # Stage 감지
        current_stage = self.detect_stage(df, idx)
        prev_stage = self.detect_stage(df, idx - 1) if idx > 0 else 'UNKNOWN'
        
        # Stage 2 또는 Stage 2A인지 확인
        if current_stage not in ['STAGE_2', 'STAGE_2A']:
            return None
        
        # 30주선 위에 있고 우상향하는지 확인
        is_above_ma = row['Close'] > row['ma30']
        is_ma_rising = row['ma30_slope'] > 0
        
        # 거래량 확인
        vol_multiplier = self.params['volume_multiplier']
        is_vol_burst = row['Volume'] > row['volume_avg'] * vol_multiplier
        
        # 상대 강도 (임시로 자체 성과만 사용)
        rs = self.calculate_relative_strength(df, df, idx)
        is_rs_strong = rs > 1.0
        
        # Stage 1 -> Stage 2 전환 또는 Stage 2A 격발
        is_stage_transition = (
            (prev_stage == 'STAGE_1' and current_stage in ['STAGE_2', 'STAGE_2A']) or
            (prev_stage == 'STAGE_2' and current_stage == 'STAGE_2A')
        )
        
        # 매수 조건
        if is_above_ma and is_ma_rising and is_rs_strong:
            # Stage 2A (격발 돌파)는 우선 순위
            if is_vol_burst and current_stage == 'STAGE_2A':
                return {
                    'date': row.name,
                    'type': 'BUY',
                    'price': row['Close'],
                    'stop_loss': row['ma30'],  # 30주선이 손절선
                    'take_profit': row['Close'] * (1 + self.params['take_profit']),
                    'reason': f"[Stage 2A Breakout] MA30 breakout + Volume surge ({row['Volume']/row['volume_avg']:.1f}x)",
                    'confidence': self._calculate_confidence(df, idx, current_stage),
                    'metrics': {
                        'stage': current_stage,
                        'ma30': row['ma30'],
                        'ma30_slope': row['ma30_slope'],
                        'volume_ratio': row['Volume'] / row['volume_avg'],
                        'rs': rs
                    }
                }
            
            # Stage 2 (일반 상승)
            elif current_stage == 'STAGE_2' and is_stage_transition:
                return {
                    'date': row.name,
                    'type': 'BUY',
                    'price': row['Close'],
                    'stop_loss': row['ma30'],
                    'take_profit': row['Close'] * (1 + self.params['take_profit']),
                    'reason': f"[Stage 2 Entry] Above MA30({row['ma30']:.0f}) + Rising",
                    'confidence': self._calculate_confidence(df, idx, current_stage),
                    'metrics': {
                        'stage': current_stage,
                        'ma30': row['ma30'],
                        'ma30_slope': row['ma30_slope'],
                        'volume_ratio': row['Volume'] / row['volume_avg'],
                        'rs': rs
                    }
                }
        
        return None
    
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """매수/매도 신호 생성"""
        # 지표 계산 (주봉 변환 포함)
        df = self.calculate_indicators(data)
        
        signals = []
        position = None
        entry_price = 0
        entry_ma30 = 0
        
        min_idx = self.params['ma_period'] + self.params['ma_slope_period']
        
        for i in range(min_idx, len(df)):
            row = df.iloc[i]
            
            # 매수 신호 체크
            if position is None:
                signal = self.check_stage_2_entry(df, i)
                if signal:
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
                    entry_ma30 = row['ma30']
            
            # 매도 신호 체크
            elif position == 'LONG':
                curr_price = row['Close']
                curr_stage = self.detect_stage(df, i)
                
                # 1. 30주선 하회 (손절)
                if curr_price < row['ma30']:
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"30주선 하회 손절 ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0
                
                # 2. Stage 3 또는 Stage 4 진입 (추세 전환)
                elif curr_stage in ['STAGE_3', 'STAGE_4']:
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"{curr_stage} 진입 ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 0.9
                    })
                    position = None
                    entry_price = 0
                
                # 3. 익절가 도달
                elif curr_price >= entry_price * (1 + self.params['take_profit']):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"익절 ({((curr_price/entry_price - 1) * 100):.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0
        
        return signals
    
    def _calculate_confidence(self, df: pd.DataFrame, idx: int, stage: str) -> float:
        """
        신호 신뢰도 계산 (0~1)
        
        기준:
        - Stage 2A가 Stage 2보다 높음
        - 30주선 기울기가 급할수록 높음
        - 거래량 폭증이 클수록 높음
        """
        row = df.iloc[idx]
        
        # Stage 가중치
        stage_weight = 1.0 if stage == 'STAGE_2A' else 0.7
        
        # 이평선 기울기 강도
        if row['ma30'] > 0:
            slope_strength = min(1.0, abs(row['ma30_slope'] / row['ma30']) * 50)
        else:
            slope_strength = 0.0
        
        # 거래량 강도
        vol_strength = min(1.0, (row['Volume'] / row['volume_avg'] - 1) / 3)
        
        # 종합 신뢰도
        confidence = stage_weight * 0.5 + slope_strength * 0.3 + vol_strength * 0.2
        
        return max(0.0, min(1.0, confidence))
