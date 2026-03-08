/**
 * 트레이딩 제어 훅
 * - 시작/중지/긴급정지/상태조회
 * - 사용처: 대시보드 트레이딩 제어 패널
 */

"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import type { TradingStatus } from "./useWebSocket";

export function useTrading(pollInterval = 5000) {
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get<TradingStatus>("/api/trading/status");
      setStatus(res.data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "상태 조회 실패");
    }
  }, []);

  const start = useCallback(async (symbols?: string[]) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<TradingStatus>("/api/trading/start", { symbols });
      setStatus(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "시작 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  const stop = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await api.post("/api/trading/stop");
      await fetchStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "중지 실패");
    } finally {
      setLoading(false);
    }
  }, [fetchStatus]);

  const emergencyStop = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await api.post("/api/trading/emergency-stop");
      await fetchStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "긴급 정지 실패");
    } finally {
      setLoading(false);
    }
  }, [fetchStatus]);

  // 주기적 상태 폴링
  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, pollInterval);
    return () => clearInterval(intervalRef.current);
  }, [fetchStatus, pollInterval]);

  return { status, loading, error, start, stop, emergencyStop, refresh: fetchStatus };
}
