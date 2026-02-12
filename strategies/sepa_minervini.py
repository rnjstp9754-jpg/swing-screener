"""
SEPA (Specific Entry Point Analysis) Strategy
마크 미너비니의 트렌드 템플릿 + VCP 패턴 전략 (원본 준수 v2)

핵심 원칙:
1. 트렌드 템플릿 8개 조건 모두 충족 (Stage 2 확인)
2. VCP (Volatility Contraction Pattern): 2~6회 수축 + 거래량 건조
3. 피봇 돌파: 거래량 40~50%↑ 동반
4. 상대강도(RS): 시장 대비 강한 종목만 대상

참고: Mark Minervini - "Trade Like a Stock Market Wizard" / "Think & Trade Like a Champion"
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from .base_strategy import BaseStrategy


class SEPAStrategy(BaseStrategy):
    """마크 미너비니 SEPA 전략 - 원본 준수 v2"""

    def __init__(self, params: Dict = None):
        default_params = {
            # 이동평균선 기간
            'sma_short': 50,
            'sma_medium': 150,
            'sma_long': 200,

            # 트렌드 템플릿 조건
            'sma200_slope_days': 22,          # 200일선 상승 확인 기간 (~1개월)
            'new_high_threshold': 0.25,       # 52주 고가 대비 25% 이내
            'low_threshold': 0.30,            # 52주 저가 대비 최소 30% 상승
            'rs_min': 0,                      # 상대강도 최소값 (0 = 시장 대비 강함)

            # VCP 패턴 감지
            'vcp_max_contractions': 6,        # 최대 수축 횟수
            'vcp_lookback': 60,               # VCP 분석 기간 (일)
            'vcp_final_tightness': 0.10,      # 마지막 수축 최대 변동폭 (10%)
            'volume_dry_ratio': 0.60,         # 거래량 건조 기준 (50일 평균의 60%)

            # 돌파 조건
            'breakout_vol_surge': 1.40,       # 돌파 거래량 최소 1.4x (40%↑)
            'pivot_lookback': 15,             # 피봇 가격 계산 기간

            # 리스크 관리
            'stop_loss': 0.07,                # 손절 7% (미너비니 7-8% 룰)
            'risk_reward_ratio': 3,           # 손익비 3:1
            'take_profit': 0.21,              # 익절 21% (7% x 3)
            'breakeven_trigger': 0.10,        # 10% 수익 시 본전치기 활성화
            'trailing_stop_pct': 0.08,        # 트레일링 스톱 8%
        }
        if params:
            default_params.update(params)

        super().__init__("SEPA (Minervini v2)", default_params)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 및 필요한 지표 계산"""
        df = data.copy()

        # 이동평균선
        df['sma50'] = df['Close'].rolling(window=self.params['sma_short']).mean()
        df['sma150'] = df['Close'].rolling(window=self.params['sma_medium']).mean()
        df['sma200'] = df['Close'].rolling(window=self.params['sma_long']).mean()

        # 52주 고가 / 저가
        df['high_52w'] = df['High'].rolling(window=252, min_periods=200).max()
        df['low_52w'] = df['Low'].rolling(window=252, min_periods=200).min()

        # 평균 거래량 (50일)
        df['vol_avg_50'] = df['Volume'].rolling(window=50).mean()

        # 최근 피봇 포인트 (lookback일간 최고가)
        df['pivot_high'] = df['High'].rolling(window=self.params['pivot_lookback']).max()

        return df

    def check_trend_template(self, df: pd.DataFrame, idx: int) -> Tuple[bool, Dict]:
        """
        미너비니 트렌드 템플릿 - 8개 조건 전부 검증

        Returns:
            (통과 여부, 상세 결과 딕셔너리)
        """
        if idx < self.params['sma_long'] + self.params['sma200_slope_days']:
            return False, {}

        row = df.iloc[idx]

        if pd.isna(row['sma50']) or pd.isna(row['sma150']) or pd.isna(row['sma200']):
            return False, {}

        price = row['Close']
        sma50 = row['sma50']
        sma150 = row['sma150']
        sma200 = row['sma200']
        high_52w = row['high_52w']
        low_52w = row['low_52w']

        results = {}

        # ① 주가 > 150일선 & 200일선
        results['above_150_200'] = (price > sma150) and (price > sma200)

        # ② 150일선 > 200일선
        results['sma150_above_200'] = sma150 > sma200

        # ③ 200일선 최소 1개월 상승
        slope_days = self.params['sma200_slope_days']
        sma200_prev = df.iloc[idx - slope_days]['sma200']
        results['sma200_rising'] = pd.notna(sma200_prev) and (sma200 > sma200_prev)

        # ④ 50일선 > 150일선 & 200일선
        results['sma50_above_all'] = (sma50 > sma150) and (sma50 > sma200)

        # ⑤ 주가 > 50일선
        results['price_above_50'] = price > sma50

        # ⑥ 52주 저가 대비 30% 이상 상승
        if pd.notna(low_52w) and low_52w > 0:
            pct_above_low = (price - low_52w) / low_52w
            results['above_52w_low'] = pct_above_low >= self.params['low_threshold']
        else:
            results['above_52w_low'] = False

        # ⑦ 52주 고가 대비 25% 이내
        if pd.notna(high_52w) and high_52w > 0:
            pct_from_high = (high_52w - price) / high_52w
            results['near_52w_high'] = pct_from_high <= self.params['new_high_threshold']
        else:
            results['near_52w_high'] = False

        # ⑧ 상대강도 (RS) - IBD RS Rating 근사
        # IBD RS는 약 12개월 수익률 기준 → 200일 수익률로 대체
        if idx >= 200:
            price_200d_ago = df.iloc[idx - 200]['Close']
            if price_200d_ago > 0:
                rs_200d = (price / price_200d_ago - 1) * 100
                results['rs_strong'] = rs_200d > self.params['rs_min']
            else:
                results['rs_strong'] = False
        else:
            results['rs_strong'] = False

        # 모든 조건 충족 여부
        all_pass = all(results.values())

        return all_pass, results

    def detect_vcp(self, df: pd.DataFrame, idx: int) -> Tuple[float, bool, Dict]:
        """
        VCP (변동성 축소 패턴) 감지

        실제 미너비니 VCP:
        - 2~6회 수축 (각 수축의 하락폭이 절반씩 감소)
        - 마지막 구간에서 거래량 건조 (Dry-up)
        - 피봇 포인트 근처에서 타이트하게 횡보

        Returns:
            (pivot_price, is_vcp_ready, vcp_details)
        """
        lookback = self.params['vcp_lookback']

        if idx < lookback + 50:
            return 0.0, False, {}

        # 분석 기간 데이터
        analysis = df.iloc[idx - lookback:idx + 1]
        pivot_price = analysis['High'].max()

        # --- 1) 수축 패턴 감지 ---
        # lookback 기간을 3등분하여 각 구간의 변동성 측정
        third = lookback // 3
        seg1 = df.iloc[idx - lookback:idx - lookback + third]
        seg2 = df.iloc[idx - lookback + third:idx - lookback + 2 * third]
        seg3 = df.iloc[idx - lookback + 2 * third:idx + 1]

        vol1 = (seg1['High'].max() - seg1['Low'].min()) / seg1['Low'].min() if len(seg1) > 0 else 1
        vol2 = (seg2['High'].max() - seg2['Low'].min()) / seg2['Low'].min() if len(seg2) > 0 else 1
        vol3 = (seg3['High'].max() - seg3['Low'].min()) / seg3['Low'].min() if len(seg3) > 0 else 1

        # 변동성이 점진적으로 줄어들어야 함
        is_contracting = (vol1 > vol2 > vol3) or (vol2 > vol3)

        # 마지막 구간 변동폭이 충분히 타이트한지
        is_tight = vol3 <= self.params['vcp_final_tightness']

        # --- 2) 거래량 건조 (Dry-up) ---
        vol_avg_50 = df.iloc[idx]['vol_avg_50']
        recent_vol_5d = df.iloc[idx - 4:idx + 1]['Volume'].mean()

        is_vol_dry = False
        if pd.notna(vol_avg_50) and vol_avg_50 > 0:
            is_vol_dry = recent_vol_5d < (vol_avg_50 * self.params['volume_dry_ratio'])

        # --- 3) 피봇 근접성 ---
        curr_price = df.iloc[idx]['Close']
        pct_from_pivot = (pivot_price - curr_price) / pivot_price if pivot_price > 0 else 1
        is_near_pivot = pct_from_pivot <= 0.05  # 피봇 대비 5% 이내

        # VCP 준비 완료 조건
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

    def check_strike(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        SEPA STRIKE 신호 (격발)

        3단계 필터:
        1. 트렌드 템플릿 8개 조건 ALL PASS
        2. VCP 패턴 + 거래량 건조
        3. 피봇 돌파 + 거래량 급증 (40%↑)
        """
        # 1단계: 트렌드 템플릿
        template_pass, template_detail = self.check_trend_template(df, idx)
        if not template_pass:
            return None

        # 2단계: VCP 감지
        pivot_price, vcp_ready, vcp_detail = self.detect_vcp(df, idx)
        if pivot_price == 0.0:
            return None

        row = df.iloc[idx]
        curr_price = row['Close']
        curr_vol = row['Volume']
        vol_avg = row['vol_avg_50']

        if pd.isna(vol_avg) or vol_avg <= 0:
            return None

        vol_ratio = curr_vol / vol_avg

        # 3단계: 돌파 확인
        is_breakout = curr_price > pivot_price
        is_vol_surge = vol_ratio >= self.params['breakout_vol_surge']

        # 격발! (VCP + 돌파 + 거래량)
        if vcp_ready and is_breakout and is_vol_surge:
            stop_loss_price = curr_price * (1 - self.params['stop_loss'])
            take_profit_price = curr_price * (1 + self.params['take_profit'])

            confidence = self._calculate_confidence(df, idx, vcp_detail, vol_ratio)

            return {
                'date': row.name,
                'type': 'BUY',
                'price': curr_price,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'reason': f"SEPA STRIKE - Pivot({pivot_price:.0f}) + Vol({vol_ratio:.1f}x) + VCP",
                'confidence': confidence,
                'metrics': {
                    'pivot_price': pivot_price,
                    'volume_ratio': vol_ratio,
                    'distance_from_52w_high': (curr_price / row['high_52w'] - 1) * 100 if pd.notna(row['high_52w']) else 0,
                    'vcp_contractions': vcp_detail.get('contractions', []),
                    'sma_alignment': f"{row['sma50']:.0f} > {row['sma150']:.0f} > {row['sma200']:.0f}"
                }
            }

        # 볼륨 없는 돌파도 낮은 신뢰도로 기록 (스크리닝용)
        if vcp_ready and is_breakout and vol_ratio >= 1.0:
            confidence = self._calculate_confidence(df, idx, vcp_detail, vol_ratio) * 0.6

            return {
                'date': row.name,
                'type': 'BUY',
                'price': curr_price,
                'stop_loss': curr_price * (1 - self.params['stop_loss']),
                'take_profit': curr_price * (1 + self.params['take_profit']),
                'reason': f"SEPA Setup - Pivot({pivot_price:.0f}) + VCP (Vol 대기)",
                'confidence': confidence,
                'metrics': {
                    'pivot_price': pivot_price,
                    'volume_ratio': vol_ratio,
                    'distance_from_52w_high': (curr_price / row['high_52w'] - 1) * 100 if pd.notna(row['high_52w']) else 0,
                    'vcp_contractions': vcp_detail.get('contractions', []),
                    'sma_alignment': f"{row['sma50']:.0f} > {row['sma150']:.0f} > {row['sma200']:.0f}"
                }
            }

        return None

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """매수/매도 신호 생성"""
        df = self.calculate_indicators(data)

        signals = []
        position = None
        entry_price = 0
        max_price = 0  # 트레일링 스톱용

        min_idx = self.params['sma_long'] + self.params['sma200_slope_days'] + 10

        for i in range(min_idx, len(df)):
            row = df.iloc[i]

            # 매수 신호 체크
            if position is None:
                signal = self.check_strike(df, i)
                if signal:
                    signals.append(signal)
                    position = 'LONG'
                    entry_price = signal['price']
                    max_price = entry_price

            # 매도 신호 체크
            elif position == 'LONG':
                curr_price = row['Close']
                max_price = max(max_price, curr_price)
                profit_pct = (curr_price - entry_price) / entry_price

                # 1. 손절 (7%)
                if curr_price <= entry_price * (1 - self.params['stop_loss']):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"손절 ({profit_pct * 100:.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0

                # 2. 본전치기 (10% 수익 후 매수가로 되돌아올 때)
                elif profit_pct <= 0.005 and max_price >= entry_price * (1 + self.params['breakeven_trigger']):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"본전치기 - Free Roll ({profit_pct * 100:.1f}%)",
                        'confidence': 0.9
                    })
                    position = None
                    entry_price = 0

                # 3. 익절 (21%)
                elif curr_price >= entry_price * (1 + self.params['take_profit']):
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"익절 ({profit_pct * 100:.1f}%)",
                        'confidence': 1.0
                    })
                    position = None
                    entry_price = 0

                # 4. 트레일링 스톱 (고점 대비 8% 하락)
                elif max_price > entry_price * 1.15:  # 15% 이상 수익 후 적용
                    trail_stop = max_price * (1 - self.params['trailing_stop_pct'])
                    if curr_price <= trail_stop:
                        signals.append({
                            'date': row.name,
                            'type': 'SELL',
                            'price': curr_price,
                            'reason': f"트레일링 스톱 ({profit_pct * 100:.1f}%, 고점대비 {(curr_price/max_price-1)*100:.1f}%)",
                            'confidence': 0.85
                        })
                        position = None
                        entry_price = 0

                # 5. 트렌드 템플릿 이탈
                elif not self.check_trend_template(df, i)[0]:
                    signals.append({
                        'date': row.name,
                        'type': 'SELL',
                        'price': curr_price,
                        'reason': f"트렌드 템플릿 이탈 ({profit_pct * 100:.1f}%)",
                        'confidence': 0.8
                    })
                    position = None
                    entry_price = 0

        return signals

    def _calculate_confidence(self, df: pd.DataFrame, idx: int,
                              vcp_detail: Dict, vol_ratio: float) -> float:
        """
        신호 신뢰도 계산 (0~1)

        기준:
        - 52주 고가 근접도 (40%)
        - VCP 수축 품질 (30%)
        - 돌파 거래량 강도 (30%)
        """
        row = df.iloc[idx]

        # 1. 52주 고가 근접도
        if pd.notna(row['high_52w']) and row['high_52w'] > 0:
            high_prox = row['Close'] / row['high_52w']
        else:
            high_prox = 0.5

        # 2. VCP 수축 품질
        contractions = vcp_detail.get('contractions', [0.2, 0.1, 0.05])
        is_contracting = vcp_detail.get('is_contracting', False)
        is_tight = vcp_detail.get('is_tight', False)
        vcp_score = 0.3
        if is_contracting:
            vcp_score += 0.4
        if is_tight:
            vcp_score += 0.3

        # 3. 거래량 강도
        vol_score = min(1.0, (vol_ratio - 1.0) / 2.0)

        confidence = high_prox * 0.4 + vcp_score * 0.3 + vol_score * 0.3
        return max(0.0, min(1.0, confidence))
