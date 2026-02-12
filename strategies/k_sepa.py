"""
K-Minervini Pro Strategy (한국형 SEPA v2)
마크 미너비니 SEPA 원칙 기반 한국 시장 최적화

변경점 (원본 대비):
- 이평선: 50/120/240일 (한국 반기/1년선)
- 거래량 돌파: 1.5x (한국 시장 유동성 고려, 3.5x → 1.5x 완화)
- VCP: 동일 원칙, 기간 조정
- 트렌드 템플릿: 8개 조건 한국 시장용 조정
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from .base_strategy import BaseStrategy


class KMinerviniProStrategy(BaseStrategy):
    """한국형 미너비니 프로 전략 v2"""

    def __init__(self, params: Dict = None):
        default_params = {
            # 이동평균선 (한국 시장)
            'sma_short': 50,
            'sma_mid': 120,           # 반기선 (미국 150일 대응)
            'sma_long': 240,          # 1년선 (미국 200일 대응)
            'ema_fast': 10,           # 트레일링용

            # 트렌드 템플릿
            'sma_slope_days': 22,     # 240일선 상승 확인 (~1개월)
            'new_high_threshold': 0.25,
            'low_threshold': 0.25,    # 한국: 52주 저가 대비 25% 상승 (완화)
            'rs_min': 0,              # 상대강도 최소

            # VCP 패턴
            'vcp_lookback': 50,       # VCP 분석 기간
            'vcp_final_tightness': 0.12,  # 마지막 수축 12% (한국 변동성 반영)
            'volume_dry_ratio': 0.60, # 거래량 건조 기준

            # 돌파 조건  
            'breakout_vol_surge': 1.50,  # 1.5x (한국형: 3.5x에서 완화)
            'pivot_lookback': 15,

            # 리스크 관리
            'stop_loss': 0.07,
            'take_profit': 0.25,      # 한국: 25% (변동성 고려)
            'breakeven_trigger': 0.10,
            'trailing_stop_pct': 0.10,

            # 한국형 추가
            'profit_surge': 0.30,     # 30% 수익: 급등 매도
        }
        if params:
            default_params.update(params)

        super().__init__("K-Minervini Pro v2", default_params)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """한국형 지표 계산"""
        df = data.copy()

        df['sma50'] = df['Close'].rolling(window=self.params['sma_short']).mean()
        df['sma120'] = df['Close'].rolling(window=self.params['sma_mid']).mean()
        df['sma240'] = df['Close'].rolling(window=self.params['sma_long']).mean()
        df['ema10'] = df['Close'].ewm(span=self.params['ema_fast'], adjust=False).mean()

        df['high_52w'] = df['High'].rolling(window=252, min_periods=200).max()
        df['low_52w'] = df['Low'].rolling(window=252, min_periods=200).min()

        df['vol_avg_50'] = df['Volume'].rolling(window=50).mean()
        df['pivot_high'] = df['High'].rolling(window=self.params['pivot_lookback']).max()

        return df

    def check_k_trend_template(self, df: pd.DataFrame, idx: int) -> Tuple[bool, Dict]:
        """
        한국형 트렌드 템플릿 - 8개 조건 검증

        한국 시장 조정:
        - 50일 > 120일 > 240일 (미국: 50 > 150 > 200)
        - 240일선 1개월 상승 (미국: 200일선)
        """
        if idx < self.params['sma_long'] + self.params['sma_slope_days']:
            return False, {}

        row = df.iloc[idx]

        if pd.isna(row['sma50']) or pd.isna(row['sma120']) or pd.isna(row['sma240']):
            return False, {}

        price = row['Close']
        sma50 = row['sma50']
        sma120 = row['sma120']
        sma240 = row['sma240']
        high_52w = row['high_52w']
        low_52w = row['low_52w']

        results = {}

        # ① 주가 > 120일선 & 240일선
        results['above_mid_long'] = (price > sma120) and (price > sma240)

        # ② 120일선 > 240일선
        results['sma120_above_240'] = sma120 > sma240

        # ③ 240일선 상승 중 (1개월)
        slope_days = self.params['sma_slope_days']
        sma240_prev = df.iloc[idx - slope_days]['sma240']
        results['sma240_rising'] = pd.notna(sma240_prev) and (sma240 > sma240_prev)

        # ④ 50일선 > 120일선 & 240일선
        results['sma50_above_all'] = (sma50 > sma120) and (sma50 > sma240)

        # ⑤ 주가 > 50일선
        results['price_above_50'] = price > sma50

        # ⑥ 52주 저가 대비 25%+ 상승
        if pd.notna(low_52w) and low_52w > 0:
            pct_above_low = (price - low_52w) / low_52w
            results['above_52w_low'] = pct_above_low >= self.params['low_threshold']
        else:
            results['above_52w_low'] = False

        # ⑦ 52주 고가 25% 이내
        if pd.notna(high_52w) and high_52w > 0:
            pct_from_high = (high_52w - price) / high_52w
            results['near_52w_high'] = pct_from_high <= self.params['new_high_threshold']
        else:
            results['near_52w_high'] = False

        # ⑧ 상대강도 (RS) - 200일 수익률 기반
        if idx >= 200:
            price_200d_ago = df.iloc[idx - 200]['Close']
            if price_200d_ago > 0:
                rs_200d = (price / price_200d_ago - 1) * 100
                results['rs_strong'] = rs_200d > self.params['rs_min']
            else:
                results['rs_strong'] = False
        else:
            results['rs_strong'] = False

        all_pass = all(results.values())
        return all_pass, results

    def detect_k_vcp(self, df: pd.DataFrame, idx: int) -> Tuple[float, bool, Dict]:
        """한국형 VCP 감지"""
        lookback = self.params['vcp_lookback']

        if idx < lookback + 50:
            return 0.0, False, {}

        analysis = df.iloc[idx - lookback:idx + 1]
        pivot_price = analysis['High'].max()

        # 3구간 변동성 분석
        third = lookback // 3
        seg1 = df.iloc[idx - lookback:idx - lookback + third]
        seg2 = df.iloc[idx - lookback + third:idx - lookback + 2 * third]
        seg3 = df.iloc[idx - lookback + 2 * third:idx + 1]

        vol1 = (seg1['High'].max() - seg1['Low'].min()) / seg1['Low'].min() if len(seg1) > 0 else 1
        vol2 = (seg2['High'].max() - seg2['Low'].min()) / seg2['Low'].min() if len(seg2) > 0 else 1
        vol3 = (seg3['High'].max() - seg3['Low'].min()) / seg3['Low'].min() if len(seg3) > 0 else 1

        is_contracting = (vol1 > vol2 > vol3) or (vol2 > vol3)
        is_tight = vol3 <= self.params['vcp_final_tightness']

        # 거래량 건조
        vol_avg_50 = df.iloc[idx]['vol_avg_50']
        recent_vol_5d = df.iloc[idx - 4:idx + 1]['Volume'].mean()
        is_vol_dry = False
        if pd.notna(vol_avg_50) and vol_avg_50 > 0:
            is_vol_dry = recent_vol_5d < (vol_avg_50 * self.params['volume_dry_ratio'])

        # 피봇 근접
        curr_price = df.iloc[idx]['Close']
        pct_from_pivot = (pivot_price - curr_price) / pivot_price if pivot_price > 0 else 1
        is_near_pivot = pct_from_pivot <= 0.07  # 한국: 7% 이내 (변동성 감안)

        is_vcp_ready = (is_contracting or is_tight) and is_vol_dry and is_near_pivot

        vcp_details = {
            'contractions': [vol1, vol2, vol3],
            'is_contracting': is_contracting,
            'is_tight': is_tight,
            'is_vol_dry': is_vol_dry,
            'is_near_pivot': is_near_pivot,
            'vol_5d_ratio': recent_vol_5d / vol_avg_50 if vol_avg_50 > 0 else 0,
        }

        return pivot_price, is_vcp_ready, vcp_details

    def check_k_strike(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """K-STRIKE 신호"""
        template_pass, _ = self.check_k_trend_template(df, idx)
        if not template_pass:
            return None

        pivot_price, vcp_ready, vcp_detail = self.detect_k_vcp(df, idx)
        if pivot_price == 0.0:
            return None

        row = df.iloc[idx]
        curr_price = row['Close']
        curr_vol = row['Volume']
        vol_avg = row['vol_avg_50']

        if pd.isna(vol_avg) or vol_avg <= 0:
            return None

        vol_ratio = curr_vol / vol_avg
        is_breakout = curr_price > pivot_price
        is_vol_surge = vol_ratio >= self.params['breakout_vol_surge']

        if vcp_ready and is_breakout and is_vol_surge:
            confidence = self._calculate_confidence(vcp_detail, vol_ratio)
            return {
                'date': row.name,
                'type': 'BUY',
                'price': curr_price,
                'stop_loss': curr_price * (1 - self.params['stop_loss']),
                'take_profit': curr_price * (1 + self.params['take_profit']),
                'reason': f"K-STRIKE Pivot({pivot_price:.0f}) + Vol({vol_ratio:.1f}x) + VCP",
                'confidence': confidence,
                'metrics': {
                    'pivot_price': pivot_price,
                    'volume_ratio': vol_ratio,
                    'vcp_contractions': vcp_detail.get('contractions', []),
                    'sma_alignment': f"{row['sma50']:.0f} > {row['sma120']:.0f} > {row['sma240']:.0f}"
                }
            }

        # VCP 준비 + 돌파 (거래량 미흡)
        if vcp_ready and is_breakout and vol_ratio >= 1.0:
            confidence = self._calculate_confidence(vcp_detail, vol_ratio) * 0.5
            return {
                'date': row.name,
                'type': 'BUY',
                'price': curr_price,
                'stop_loss': curr_price * (1 - self.params['stop_loss']),
                'take_profit': curr_price * (1 + self.params['take_profit']),
                'reason': f"K-Setup Pivot({pivot_price:.0f}) + VCP (Vol 대기)",
                'confidence': confidence,
                'metrics': {
                    'pivot_price': pivot_price,
                    'volume_ratio': vol_ratio,
                    'vcp_contractions': vcp_detail.get('contractions', []),
                    'sma_alignment': f"{row['sma50']:.0f} > {row['sma120']:.0f} > {row['sma240']:.0f}"
                }
            }

        return None

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """매수/매도 신호 생성"""
        df = self.calculate_indicators(data)

        signals = []
        position = None
        entry_price = 0
        max_price = 0

        min_idx = self.params['sma_long'] + self.params['sma_slope_days'] + 10

        for i in range(min_idx, len(df)):
            if position is None:
                signal = self.check_k_strike(df, i)
                if signal:
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
                    max_price = entry_price

            elif position == 'LONG':
                row = df.iloc[i]
                curr_price = row['Close']
                max_price = max(max_price, curr_price)
                profit_pct = (curr_price - entry_price) / entry_price

                # 1. 손절 (7%)
                if curr_price <= entry_price * (1 - self.params['stop_loss']):
                    signals.append({
                        'date': row.name, 'type': 'SELL', 'price': curr_price,
                        'reason': f"손절 ({profit_pct * 100:.1f}%)", 'confidence': 1.0
                    })
                    position = None
                    entry_price = 0

                # 2. 급등 매도 (30%+ 후 EMA10 이탈)
                elif profit_pct >= self.params['profit_surge']:
                    if pd.notna(row['ema10']) and curr_price < row['ema10']:
                        signals.append({
                            'date': row.name, 'type': 'SELL', 'price': curr_price,
                            'reason': f"급등 매도 EMA10 이탈 ({profit_pct * 100:.1f}%)", 'confidence': 1.0
                        })
                        position = None
                        entry_price = 0

                # 3. 본전치기 (10% 수익 후 매수가 복귀)
                elif profit_pct <= 0.005 and max_price >= entry_price * (1 + self.params['breakeven_trigger']):
                    signals.append({
                        'date': row.name, 'type': 'SELL', 'price': curr_price,
                        'reason': f"본전치기 ({profit_pct * 100:.1f}%)", 'confidence': 0.9
                    })
                    position = None
                    entry_price = 0

                # 4. 익절 (25%)
                elif curr_price >= entry_price * (1 + self.params['take_profit']):
                    signals.append({
                        'date': row.name, 'type': 'SELL', 'price': curr_price,
                        'reason': f"익절 ({profit_pct * 100:.1f}%)", 'confidence': 1.0
                    })
                    position = None
                    entry_price = 0

                # 5. 트레일링 스톱
                elif max_price > entry_price * 1.15:
                    trail_stop = max_price * (1 - self.params['trailing_stop_pct'])
                    if curr_price <= trail_stop:
                        signals.append({
                            'date': row.name, 'type': 'SELL', 'price': curr_price,
                            'reason': f"트레일링 ({profit_pct * 100:.1f}%)", 'confidence': 0.85
                        })
                        position = None
                        entry_price = 0

        return signals

    def _calculate_confidence(self, vcp_detail: Dict, vol_ratio: float) -> float:
        """신호 신뢰도 계산"""
        is_contracting = vcp_detail.get('is_contracting', False)
        is_tight = vcp_detail.get('is_tight', False)

        vcp_score = 0.3
        if is_contracting:
            vcp_score += 0.4
        if is_tight:
            vcp_score += 0.3

        vol_score = min(1.0, (vol_ratio - 1.0) / 3.0)

        confidence = vcp_score * 0.6 + vol_score * 0.4
        return max(0.0, min(1.0, confidence))
