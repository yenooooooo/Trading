/**
 * WebSocket 훅
 * - 실시간 시세, 포지션, 매매 알림 스트림
 * - 자동 재연결, 상태 관리
 * - 사용처: 대시보드 실시간 업데이트
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// WebSocket은 백엔드 WS 엔드포인트 구현 후 활성화
// 현재는 REST 폴링으로 대체 (useTrading.ts)
const WS_BASE_URL = "";
const WS_ENABLED = !!WS_BASE_URL;

// ── 타입 ─────────────────────────────────

export interface TickerData {
  symbol: string;
  price: number;
  fundingRate: number;
  timestamp: number;
}

export interface PositionData {
  symbol: string;
  side: "long" | "short";
  entryPrice: number;
  markPrice: number;
  pnlPct: number;
  holdMinutes: number;
}

export interface TradeEvent {
  type: "open" | "close";
  symbol: string;
  side: string;
  price: number;
  reason: string;
  pnlPct?: number;
  timestamp: number;
}

export interface TradingStatus {
  running: boolean;
  mode: "paper" | "live";
  symbols: string[];
  nextFundingMinutes: number;
  positions: PositionData[];
  todayPnl: number;
  wsConnected: boolean;
}

// ── 기본 WebSocket 훅 ─────────────────────

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: unknown) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnects?: number;
}

export function useWebSocket({
  url,
  onMessage,
  reconnect = true,
  reconnectInterval = 3000,
  maxReconnects = 5,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (!url) return; // URL 없으면 연결 안 함
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectCount.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch {
        // non-JSON message
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (reconnect && reconnectCount.current < maxReconnects) {
        reconnectCount.current++;
        setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, onMessage, reconnect, reconnectInterval, maxReconnects]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { connected, send };
}

// ── 시세 스트림 훅 ─────────────────────────

export function useTickerStream(symbols: string[] = ["BTCUSDT"]) {
  const [tickers, setTickers] = useState<Record<string, TickerData>>({});

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as { type?: string; data?: TickerData };
    if (msg.type === "ticker" && msg.data) {
      setTickers((prev) => ({
        ...prev,
        [msg.data!.symbol]: msg.data!,
      }));
    }
  }, []);

  const streamParam = symbols.join(",");
  const { connected } = useWebSocket({
    url: WS_ENABLED ? `${WS_BASE_URL}/ticker?symbols=${streamParam}` : "",
    onMessage: handleMessage,
  });

  return { tickers, connected };
}

// ── 포지션 스트림 훅 ─────────────────────────

export function usePositionStream() {
  const [positions, setPositions] = useState<PositionData[]>([]);

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as { type?: string; data?: PositionData[] };
    if (msg.type === "positions" && msg.data) {
      setPositions(msg.data);
    }
  }, []);

  const { connected } = useWebSocket({
    url: WS_ENABLED ? `${WS_BASE_URL}/positions` : "",
    onMessage: handleMessage,
  });

  return { positions, connected };
}

// ── 매매 이벤트 스트림 훅 ─────────────────────

export function useTradeStream() {
  const [trades, setTrades] = useState<TradeEvent[]>([]);

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as { type?: string; data?: TradeEvent };
    if (msg.type === "trade" && msg.data) {
      setTrades((prev) => [msg.data!, ...prev].slice(0, 50));
    }
  }, []);

  const { connected } = useWebSocket({
    url: WS_ENABLED ? `${WS_BASE_URL}/trades` : "",
    onMessage: handleMessage,
  });

  return { trades, connected };
}
