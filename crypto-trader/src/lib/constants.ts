/**
 * 앱 전역 상수 정의
 * - 트레이딩 관련 상수, UI 상수
 * - 사용처: 전체 앱에서 import하여 사용
 */

// --- 소액 계좌 트레이딩 상수 ---
export const MAX_LEVERAGE = 5;  // 하드 리밋 (소액 전용)
export const RECOMMENDED_LEVERAGE = 3; // 권장 레버리지
export const MAX_RISK_PER_TRADE = 0.05; // 단일 포지션 최대 리스크 5%
export const MIN_RISK_PER_TRADE = 0.03; // 단일 포지션 최소 리스크 3%
export const DAILY_LOSS_LIMIT = 0.08; // 일일 최대 손실 8%
export const WEEKLY_LOSS_LIMIT = 0.15; // 주간 최대 손실 15%
export const MAX_DAILY_TRADES = 3; // 일일 최대 거래 횟수
export const MIN_TRADE_USDT = 5; // 바이낸스 최소 주문 금액
export const TAKER_FEE_PCT = 0.04; // 테이커 수수료 0.04%

// --- 타임프레임 옵션 ---
export const TIMEFRAMES = [
  { value: "1m", label: "1분" },
  { value: "5m", label: "5분" },
  { value: "15m", label: "15분" },
  { value: "1h", label: "1시간" },
  { value: "4h", label: "4시간" },
  { value: "1d", label: "1일" },
] as const;

// --- 색상 상수 ---
export const COLORS = {
  profit: "#22C55E",  // 수익 (Green)
  loss: "#EF4444",    // 손실 (Red)
  neutral: "#94A3B8", // 중립 (Slate)
  warning: "#F59E0B", // 경고 (Amber)
} as const;

// --- 거래소 목록 ---
export const EXCHANGES = [
  { id: "binance", name: "Binance Futures", supported: true },
  { id: "bybit", name: "Bybit", supported: false },
  { id: "okx", name: "OKX", supported: false },
  { id: "bitget", name: "Bitget", supported: false },
] as const;

// --- WebSocket ---
export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
export const WS_RECONNECT_INTERVAL = 3000; // 재연결 간격 (ms)
export const WS_MAX_RECONNECT_ATTEMPTS = 10;

// --- API ---
export const API_STALE_TIME = {
  realtime: 0,          // 실시간 데이터 (항상 fresh)
  short: 30 * 1000,     // 30초 (포지션, 주문)
  medium: 5 * 60 * 1000, // 5분 (전략 설정, 사용자 정보)
  long: 30 * 60 * 1000, // 30분 (거래소 목록 등 정적 데이터)
} as const;
