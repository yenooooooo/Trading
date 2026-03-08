"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Clock,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface PositionItem {
  symbol: string;
  side: "long" | "short";
  entry_price: number;
  mark_price: number;
  pnl_pct: number;
  hold_minutes: number;
}

interface PositionSummary {
  total_positions: number;
  long_count: number;
  short_count: number;
  total_unrealized_pnl_pct: number;
  positions: PositionItem[];
}

export default function PositionsPage() {
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPositions = useCallback(async () => {
    try {
      const res = await api.get<PositionSummary>("/api/positions/summary");
      setSummary(res.data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "포지션 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, [fetchPositions]);

  const positions = summary?.positions ?? [];

  const formatHoldTime = (minutes: number) => {
    const h = Math.floor(minutes / 60);
    const m = Math.floor(minutes % 60);
    if (h > 0) return `${h}시간 ${m}분`;
    return `${m}분`;
  };

  const formatPrice = (price: number) => {
    if (price >= 1000) return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    return `$${price.toFixed(4)}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">포지션 관리</h1>
        <Button variant="outline" size="sm" onClick={fetchPositions} disabled={loading}>
          <RefreshCw className={`mr-1 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          새로고침
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">활성 포지션</p>
              <p className="text-2xl font-bold font-mono">{summary?.total_positions ?? 0}</p>
            </div>
            <div className="rounded-md bg-primary/10 p-2">
              <Wallet className="h-5 w-5 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">롱 포지션</p>
              <p className="text-2xl font-bold font-mono text-green-500">{summary?.long_count ?? 0}</p>
            </div>
            <div className="rounded-md bg-green-500/10 p-2">
              <ArrowUpRight className="h-5 w-5 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">숏 포지션</p>
              <p className="text-2xl font-bold font-mono text-red-500">{summary?.short_count ?? 0}</p>
            </div>
            <div className="rounded-md bg-red-500/10 p-2">
              <ArrowDownRight className="h-5 w-5 text-red-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">총 미실현 PnL</p>
              <p className={`text-2xl font-bold font-mono ${
                (summary?.total_unrealized_pnl_pct ?? 0) >= 0 ? "text-green-500" : "text-red-500"
              }`}>
                {(summary?.total_unrealized_pnl_pct ?? 0) >= 0 ? "+" : ""}
                {(summary?.total_unrealized_pnl_pct ?? 0).toFixed(2)}%
              </p>
            </div>
            <div className="rounded-md bg-primary/10 p-2">
              {(summary?.total_unrealized_pnl_pct ?? 0) >= 0 ? (
                <TrendingUp className="h-5 w-5 text-green-500" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-500" />
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-red-500/50">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-red-500">
            <AlertCircle className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      {/* Position List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">보유 포지션</CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <Wallet className="h-12 w-12 text-zinc-600" />
              <p className="text-muted-foreground">현재 보유 중인 포지션이 없습니다</p>
              <p className="text-xs text-muted-foreground">
                트레이딩이 실행 중이면 펀딩비 정산 전 자동으로 포지션이 생성됩니다
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {positions.map((pos) => (
                <div
                  key={pos.symbol}
                  className="flex items-center justify-between rounded-lg border p-4 hover:border-zinc-600 transition-colors"
                >
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold">{pos.symbol}</span>
                      <Badge
                        variant={pos.side === "long" ? "default" : "destructive"}
                        className="text-xs"
                      >
                        {pos.side === "long" ? "LONG" : "SHORT"}
                      </Badge>
                    </div>
                    <div className="flex gap-6 text-sm text-muted-foreground">
                      <span>
                        진입가: <span className="font-mono text-foreground">{formatPrice(pos.entry_price)}</span>
                      </span>
                      <span>
                        현재가: <span className="font-mono text-foreground">{formatPrice(pos.mark_price)}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatHoldTime(pos.hold_minutes)}
                      </span>
                    </div>
                  </div>
                  <div className="text-right space-y-1">
                    <div
                      className={`text-xl font-mono font-bold ${
                        pos.pnl_pct >= 0 ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      {pos.pnl_pct >= 0 ? "+" : ""}
                      {pos.pnl_pct.toFixed(2)}%
                    </div>
                    <div className="text-xs text-muted-foreground">
                      미실현 PnL
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
