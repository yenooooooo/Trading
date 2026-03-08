/**
 * 전략 메타 정보 — UI 표시용 상수
 * - 전략별 아이콘, 설명, 기본값, 파라미터 라벨
 * - 시드 기반 권장 설정 계산
 */

import type { StrategyMeta, StrategyType, SeedRecommendation, FeeEstimate } from "@/types/strategy";

// --- 전략 메타 정보 ---

export const STRATEGY_META: Record<StrategyType, StrategyMeta> = {
  funding_rate: {
    type: "funding_rate",
    name: "펀딩비 역발상",
    description: "극단적 펀딩비에서 반대 포지션 진입. 과열된 롱/숏 포지션의 청산을 기대하는 역발상 전략.",
    icon: "TrendingDown",
    color: "text-blue-400",
    seedRange: "$50 ~ $400",
    frequency: "일 0~1회 (8시간 간격)",
    bestCondition: "펀딩비가 +0.05% 이상 또는 -0.05% 이하로 극단적일 때",
    recommendedTimeframes: ["1h", "4h"],
    defaultParams: {
      funding_threshold: 0.05,
      funding_extreme: 0.1,
      rsi_confirm_period: 14,
      rsi_overbought: 70,
      rsi_oversold: 30,
      volume_confirm: 1.5,
      min_expected_move: 0.3,
    },
    paramLabels: {
      funding_threshold: "펀딩비 임계값 (%)",
      funding_extreme: "극단 펀딩비 (%)",
      rsi_confirm_period: "RSI 기간",
      rsi_overbought: "RSI 과매수",
      rsi_oversold: "RSI 과매도",
      volume_confirm: "거래량 확인 배수",
      min_expected_move: "최소 예상 변동 (%)",
    },
    paramDescriptions: {
      funding_threshold: "이 값 이상이면 진입 신호 발생",
      funding_extreme: "극단 펀딩비 — 강한 신호",
      rsi_confirm_period: "RSI 보조 확인 기간",
      rsi_overbought: "RSI가 이 값 이상이면 과매수",
      rsi_oversold: "RSI가 이 값 이하이면 과매도",
      volume_confirm: "현재 거래량 / 평균 거래량 비율",
      min_expected_move: "수수료 대비 수익 최소 기대치",
    },
  },
  liquidation_bounce: {
    type: "liquidation_bounce",
    name: "청산 캐스케이드 반등",
    description: "급격한 가격 하락과 미결제약정(OI) 급감을 감지하여 청산 캐스케이드 종료 후 반등을 포착하는 전략.",
    icon: "Zap",
    color: "text-yellow-400",
    seedRange: "$100 ~ $400",
    frequency: "주 1~2회 (큰 움직임만)",
    bestCondition: "가격이 3% 이상 급락하고 OI가 5% 이상 급감할 때",
    recommendedTimeframes: ["5m", "15m", "1h"],
    defaultParams: {
      price_drop_pct: 3.0,
      oi_drop_pct: 5.0,
      rsi_bounce_level: 25,
      volume_spike: 2.0,
      atr_period: 14,
      sl_atr_mult: 1.5,
      tp_atr_mult: 3.0,
      min_expected_move: 0.5,
    },
    paramLabels: {
      price_drop_pct: "급락 감지 (%) ",
      oi_drop_pct: "OI 급감 (%) ",
      rsi_bounce_level: "RSI 반등 레벨",
      volume_spike: "거래량 급등 배수",
      atr_period: "ATR 기간",
      sl_atr_mult: "손절 ATR 배수",
      tp_atr_mult: "익절 ATR 배수",
      min_expected_move: "최소 예상 변동 (%)",
    },
    paramDescriptions: {
      price_drop_pct: "이 비율 이상 급락 시 청산 캐스케이드 감지",
      oi_drop_pct: "미결제약정이 이 비율 이상 감소 시 감지",
      rsi_bounce_level: "RSI가 이 값 이하에서 반등 시 진입",
      volume_spike: "평균 대비 거래량 급등 배수",
      atr_period: "ATR 계산 기간 (캔들 수)",
      sl_atr_mult: "손절 = ATR x 이 값",
      tp_atr_mult: "익절 = ATR x 이 값",
      min_expected_move: "수수료 대비 수익 최소 기대치",
    },
  },
  volatility_breakout: {
    type: "volatility_breakout",
    name: "변동성 돌파",
    description: "래리 윌리엄스 변동성 돌파에 미시구조 필터를 결합. 전일 변동폭의 k배 돌파 시 추세 방향으로 진입.",
    icon: "ArrowUpRight",
    color: "text-green-400",
    seedRange: "$50 ~ $400",
    frequency: "일 0~2회",
    bestCondition: "변동성이 축소된 후 한 방향으로 강하게 돌파할 때",
    recommendedTimeframes: ["1h", "4h", "1d"],
    defaultParams: {
      k_factor: 0.5,
      atr_period: 14,
      sl_atr_mult: 1.0,
      tp_atr_mult: 2.0,
      ema_trend_period: 20,
      volume_confirm: 1.3,
      min_expected_move: 0.3,
      funding_filter: 0.08,
    },
    paramLabels: {
      k_factor: "돌파 계수 (k)",
      atr_period: "ATR 기간",
      sl_atr_mult: "손절 ATR 배수",
      tp_atr_mult: "익절 ATR 배수",
      ema_trend_period: "추세 EMA 기간",
      volume_confirm: "거래량 확인 배수",
      min_expected_move: "최소 예상 변동 (%)",
      funding_filter: "펀딩비 역행 필터 (%)",
    },
    paramDescriptions: {
      k_factor: "전일 변동폭 x k 돌파 시 진입 (0.4~0.6 권장)",
      atr_period: "ATR 계산 기간 (캔들 수)",
      sl_atr_mult: "손절 = ATR x 이 값",
      tp_atr_mult: "익절 = ATR x 이 값",
      ema_trend_period: "EMA 추세 확인 기간",
      volume_confirm: "현재 거래량 / 평균 거래량 비율",
      min_expected_move: "수수료 대비 수익 최소 기대치",
      funding_filter: "펀딩비가 이 값 이상 역행 시 진입 차단",
    },
  },
};

// --- 전략 유형 목록 ---
export const STRATEGY_TYPES: StrategyType[] = [
  "funding_rate",
  "liquidation_bounce",
  "volatility_breakout",
];

// --- 시드 기반 권장 설정 ---
export function getSeedRecommendation(seedUsd: number): SeedRecommendation {
  if (seedUsd < 50) {
    return {
      leverage: 2,
      risk_percent: 0.05,
      max_positions: 1,
      max_daily_trades: 1,
      description: "극소액 — 최소 레버리지, 거래 최소화",
    };
  }
  if (seedUsd < 100) {
    return {
      leverage: 3,
      risk_percent: 0.05,
      max_positions: 1,
      max_daily_trades: 2,
      description: "$50~100 — 보수적 운용, 수수료 비중 주의",
    };
  }
  if (seedUsd < 200) {
    return {
      leverage: 3,
      risk_percent: 0.04,
      max_positions: 1,
      max_daily_trades: 2,
      description: "$100~200 — 안정적 운용, 레버리지 3x 권장",
    };
  }
  if (seedUsd < 400) {
    return {
      leverage: 3,
      risk_percent: 0.03,
      max_positions: 1,
      max_daily_trades: 3,
      description: "$200~400 — 적정 운용, 포지션 분산 가능",
    };
  }
  return {
    leverage: 5,
    risk_percent: 0.03,
    max_positions: 2,
    max_daily_trades: 3,
    description: "$400+ — 표준 운용, 레버리지 3~5x",
  };
}

// --- 수수료 추정 ---
const TAKER_FEE = 0.0004; // 0.04%

export function estimateFees(positionSizeUsd: number, leverage: number): FeeEstimate {
  const roundTripPct = TAKER_FEE * 2 * 100; // 왕복 수수료 %
  const roundTripUsd = positionSizeUsd * TAKER_FEE * 2;
  const minProfitableMove = roundTripPct * 2; // 수수료 x 2 이상 수익 필요

  return {
    round_trip_fee_pct: Number(roundTripPct.toFixed(4)),
    round_trip_fee_usd: Number(roundTripUsd.toFixed(2)),
    min_profitable_move: Number(minProfitableMove.toFixed(4)),
  };
}
