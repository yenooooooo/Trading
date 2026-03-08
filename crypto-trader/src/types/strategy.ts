/**
 * 전략 관련 타입 정의
 * - 사용처: 전략 관리 페이지, API 호출
 */

// --- 전략 응답 ---
export interface Strategy {
  id: string;
  name: string;
  strategy_type: StrategyType;
  symbol: string;
  interval: string;
  leverage: number;
  max_position_pct: number;
  params: Record<string, number | string>;
  status: "active" | "paused" | "stopped";
  is_active: boolean;
}

// --- 전략 유형 ---
export type StrategyType =
  | "funding_rate"
  | "liquidation_bounce"
  | "volatility_breakout";

// --- 전략별 파라미터 ---

export interface FundingRateParams {
  funding_threshold: number;    // 펀딩비 임계값 (%) — 기본 0.05
  funding_extreme: number;      // 극단 펀딩비 (%) — 기본 0.1
  rsi_confirm_period: number;   // RSI 확인 기간 — 기본 14
  rsi_overbought: number;       // RSI 과매수 — 기본 70
  rsi_oversold: number;         // RSI 과매도 — 기본 30
  volume_confirm: number;       // 거래량 확인 배수 — 기본 1.5
  min_expected_move: number;    // 최소 예상 변동 (%) — 기본 0.3
}

export interface LiquidationBounceParams {
  price_drop_pct: number;       // 급락 감지 임계 (%) — 기본 3.0
  oi_drop_pct: number;          // OI 급감 임계 (%) — 기본 5.0
  rsi_bounce_level: number;     // RSI 반등 레벨 — 기본 25
  volume_spike: number;         // 거래량 급등 배수 — 기본 2.0
  atr_period: number;           // ATR 기간 — 기본 14
  sl_atr_mult: number;          // 손절 ATR 배수 — 기본 1.5
  tp_atr_mult: number;          // 익절 ATR 배수 — 기본 3.0
  min_expected_move: number;    // 최소 예상 변동 (%) — 기본 0.5
}

export interface VolatilityBreakoutParams {
  k_factor: number;             // 돌파 계수 (0.4~0.6) — 기본 0.5
  atr_period: number;           // ATR 기간 — 기본 14
  sl_atr_mult: number;          // 손절 ATR 배수 — 기본 1.0
  tp_atr_mult: number;          // 익절 ATR 배수 — 기본 2.0
  ema_trend_period: number;     // 추세 확인 EMA — 기본 20
  volume_confirm: number;       // 거래량 확인 배수 — 기본 1.3
  min_expected_move: number;    // 최소 예상 변동 (%) — 기본 0.3
  funding_filter: number;       // 펀딩비 역행 필터 (%) — 기본 0.08
}

// --- 전략 메타 정보 (UI용) ---
export interface StrategyMeta {
  type: StrategyType;
  name: string;
  description: string;
  icon: string;
  color: string;
  seedRange: string;
  frequency: string;
  bestCondition: string;
  defaultParams: Record<string, number>;
  paramLabels: Record<string, string>;
  paramDescriptions: Record<string, string>;
  recommendedTimeframes: string[];
}

// --- 내장 전략 정보 ---
export interface BuiltinStrategy {
  name: string;
  description: string;
  default_params: Record<string, number | string>;
}

// --- 전략 생성 요청 ---
export interface StrategyCreateRequest {
  name: string;
  strategy_type: string;
  symbol: string;
  interval: string;
  leverage: number;
  max_position_pct: number;
  params?: Record<string, number | string>;
}

// --- 신호 체크 응답 ---
export interface SignalCheck {
  signal: "long" | "short" | "close" | "hold";
  symbol: string;
  strength: number;
  reason: string;
}

// --- 시드 기반 권장 설정 ---
export interface SeedRecommendation {
  leverage: number;
  risk_percent: number;
  max_positions: number;
  max_daily_trades: number;
  description: string;
}

// --- 수수료 정보 ---
export interface FeeEstimate {
  round_trip_fee_pct: number;
  round_trip_fee_usd: number;
  min_profitable_move: number;
}
