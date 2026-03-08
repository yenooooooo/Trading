"use client";

import { useEffect, useState, useCallback } from "react";
import {
  History,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Target,
  RefreshCw,
  AlertCircle,
  Calendar,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface TradeStats {
  today_pnl: number;
  week_pnl: number;
  today_trade_count: number;
  total_recent_trades: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
}

interface TradeRecord {
  pnl: number;
  symbol?: string;
  side?: string;
  timestamp?: string;
}

export default function HistoryPage() {
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, tradesRes] = await Promise.all([
        api.get<TradeStats>("/api/trades/stats"),
        api.get<TradeRecord[]>("/api/trades"),
      ]);
      setStats(statsRes.data);
      setTrades(Array.isArray(tradesRes.data) ? tradesRes.data : []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "데이터 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const totalTrades = (stats?.win_count ?? 0) + (stats?.loss_count ?? 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">거래 내역</h1>
        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`mr-1 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          새로고침
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">오늘 PnL</p>
              <p className={`text-2xl font-bold font-mono ${
                (stats?.today_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
              }`}>
                {(stats?.today_pnl ?? 0) >= 0 ? "+" : ""}
                {(stats?.today_pnl ?? 0).toFixed(2)}%
              </p>
            </div>
            <div className="rounded-md bg-primary/10 p-2">
              <Calendar className="h-5 w-5 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">이번 주 PnL</p>
              <p className={`text-2xl font-bold font-mono ${
                (stats?.week_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
              }`}>
                {(stats?.week_pnl ?? 0) >= 0 ? "+" : ""}
                {(stats?.week_pnl ?? 0).toFixed(2)}%
              </p>
            </div>
            <div className="rounded-md bg-primary/10 p-2">
              <BarChart3 className="h-5 w-5 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">승률</p>
              <p className="text-2xl font-bold font-mono">
                {(stats?.win_rate ?? 0).toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground">
                {stats?.win_count ?? 0}승 {stats?.loss_count ?? 0}패
              </p>
            </div>
            <div className="rounded-md bg-primary/10 p-2">
              <Target className="h-5 w-5 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">오늘 거래 수</p>
              <p className="text-2xl font-bold font-mono">{stats?.today_trade_count ?? 0}</p>
              <p className="text-xs text-muted-foreground">
                최대 3회/일
              </p>
            </div>
            <div className="rounded-md bg-primary/10 p-2">
              <History className="h-5 w-5 text-primary" />
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

      {/* PnL Overview */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">수익/손실 분포</CardTitle>
          </CardHeader>
          <CardContent>
            {totalTrades === 0 ? (
              <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
                거래 데이터가 없습니다
              </div>
            ) : (
              <div className="space-y-4">
                {/* Win/Loss bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-green-500">승리 {stats?.win_count ?? 0}건</span>
                    <span className="text-red-500">패배 {stats?.loss_count ?? 0}건</span>
                  </div>
                  <div className="flex h-4 rounded-full overflow-hidden bg-muted">
                    <div
                      className="bg-green-500 transition-all"
                      style={{ width: `${(stats?.win_rate ?? 0)}%` }}
                    />
                    <div
                      className="bg-red-500 transition-all"
                      style={{ width: `${100 - (stats?.win_rate ?? 0)}%` }}
                    />
                  </div>
                </div>

                {/* Summary */}
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="rounded-lg border p-3 space-y-1">
                    <p className="text-xs text-muted-foreground">일일 PnL</p>
                    <p className={`text-lg font-mono font-semibold ${
                      (stats?.today_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {(stats?.today_pnl ?? 0) >= 0 ? "+" : ""}{(stats?.today_pnl ?? 0).toFixed(4)}%
                    </p>
                  </div>
                  <div className="rounded-lg border p-3 space-y-1">
                    <p className="text-xs text-muted-foreground">주간 PnL</p>
                    <p className={`text-lg font-mono font-semibold ${
                      (stats?.week_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {(stats?.week_pnl ?? 0) >= 0 ? "+" : ""}{(stats?.week_pnl ?? 0).toFixed(4)}%
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">일별 PnL 추이</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
              거래 데이터가 쌓이면 일별 PnL 차트가 표시됩니다
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Trades */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">최근 거래</CardTitle>
        </CardHeader>
        <CardContent>
          {trades.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <History className="h-12 w-12 text-zinc-600" />
              <p className="text-muted-foreground">거래 내역이 없습니다</p>
              <p className="text-xs text-muted-foreground">
                모의매매가 실행되면 거래 내역이 여기에 표시됩니다
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {trades.map((trade, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    {(trade.pnl ?? 0) >= 0 ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                    <div>
                      <span className="font-medium text-sm">
                        {trade.symbol ?? "N/A"}
                      </span>
                      {trade.side && (
                        <Badge
                          variant={trade.side === "long" ? "default" : "destructive"}
                          className="text-xs ml-2"
                        >
                          {trade.side}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div
                    className={`font-mono text-sm font-semibold ${
                      (trade.pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                    }`}
                  >
                    {(trade.pnl ?? 0) >= 0 ? "+" : ""}{(trade.pnl ?? 0).toFixed(2)}%
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
