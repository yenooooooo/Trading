/**
 * 시장 데이터 타입 정의
 * - 시세, OHLCV, 오더북 등 시장 관련 데이터 구조
 * - 사용처: trading 컴포넌트, hooks/useTickerStream 등
 */

// --- 실시간 시세 ---
export interface Ticker {
  symbol: string;
  price: number;
  change24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  timestamp: number;
}

// --- OHLCV 캔들 데이터 ---
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// --- 오더북 ---
export interface OrderBookEntry {
  price: number;
  size: number;
}

export interface OrderBook {
  symbol: string;
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  timestamp: number;
}

// --- 최근 체결 ---
export interface RecentTrade {
  id: string;
  price: number;
  amount: number;
  side: "buy" | "sell";
  timestamp: number;
}

// --- 타임프레임 ---
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

// --- 지원 거래소 ---
export type ExchangeId = "binance" | "bybit" | "okx" | "bitget";
