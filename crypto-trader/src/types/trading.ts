/**
 * 트레이딩 타입 정의
 * - 주문, 포지션, 거래 관련 데이터 구조
 * - 사용처: trading 컴포넌트, positions 페이지, hooks
 */

import Decimal from "decimal.js";

// --- 포지션 ---
export interface Position {
  id: string;
  strategyId: string | null;
  exchange: string;
  symbol: string;
  side: "long" | "short";
  entryPrice: string; // Decimal 문자열 (부동소수점 방지)
  currentPrice: string;
  size: string;
  leverage: number;
  stopLoss: string | null;
  takeProfit: TakeProfit[] | null;
  unrealizedPnl: string;
  realizedPnl: string;
  status: "open" | "closed" | "liquidated";
  openedAt: string;
  closedAt: string | null;
  closeReason: CloseReason | null;
}

export interface TakeProfit {
  price: string;
  percentage: number; // 해당 TP에서 청산할 비율 (0~100)
}

export type CloseReason =
  | "take_profit"
  | "stop_loss"
  | "trailing_stop"
  | "manual"
  | "signal"
  | "risk_limit";

// --- 주문 ---
export interface Order {
  id: string;
  strategyId: string | null;
  positionId: string | null;
  exchange: string;
  exchangeOrderId: string | null;
  symbol: string;
  type: OrderType;
  side: "buy" | "sell";
  price: string | null;
  amount: string;
  filled: string;
  avgFillPrice: string | null;
  fee: string;
  status: OrderStatus;
  createdAt: string;
}

export type OrderType =
  | "market"
  | "limit"
  | "stop_market"
  | "stop_limit"
  | "trailing_stop";

export type OrderStatus =
  | "pending"
  | "open"
  | "partially_filled"
  | "filled"
  | "cancelled"
  | "rejected";

// --- 거래 체결 ---
export interface Trade {
  id: string;
  strategyId: string | null;
  symbol: string;
  side: "buy" | "sell";
  price: string;
  amount: string;
  fee: string;
  realizedPnl: string | null;
  executedAt: string;
}
