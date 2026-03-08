/**
 * 메인 대시보드 페이지
 * - 실제 API 데이터 기반 핵심 지표, 자산 곡선, 포지션, 리스크
 * - 사용처: /dashboard (로그인 후 홈)
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Play,
  Square,
  AlertTriangle,
  Wifi,
  WifiOff,
  Clock,
  BarChart3,
  Target,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/dashboard/StatCard";
import { useTrading } from "@/hooks/useTrading";
import { useTickerStream } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";

// --- 타입 ---
interface TradeStats {
  todayPnl: number;
  weekPnl: number;
  todayTradeCount: number;
  totalRecentTrades: number;
  winCount: number;
  lossCount: number;
  winRate: number;
}

interface PositionSummary {
  totalPositions: number;
  longCount: number;
  shortCount: number;
  totalUnrealizedPnlPct: number;
  positions: Array<{
    symbol: string;
    side: string;
    entryPrice: number;
    markPrice: number;
    pnlPct: number;
    holdMinutes: number;
  }>;
}

interface RiskStatus {
  balance: number;
  overallRiskScore: number;
  dailyPnl: number;
  dailyUsedPct: number;
  dailyLossLimitPct: number;
  weeklyPnl: number;
  weeklyUsedPct: number;
  leverage: number;
  maxLeverage: number;
  consecutiveLosses: number;
  consecutiveLossStopAt: number;
  running: boolean;
  wsConnected: boolean;
}

interface RecentTrade {
  symbol?: string;
  side?: string;
  pnl?: number;
  pnlPct?: number;
  timestamp?: number;
  entryTime?: number;
  exitTime?: number;
  reason?: string;
}

// --- 펀딩비 카운트다운 ---
function getNextFundingTime(): Date {
  const now = new Date();
  const utcH = now.getUTCHours();
  const nextSlot = utcH < 8 ? 8 : utcH < 16 ? 16 : 24;
  const next = new Date(now);
  next.setUTCHours(nextSlot === 24 ? 0 : nextSlot, 0, 0, 0);
  if (nextSlot === 24) next.setUTCDate(next.getUTCDate() + 1);
  return next;
}

function useFundingCountdown() {
  const [remaining, setRemaining] = useState("");
  useEffect(() => {
    const tick = () => {
      const diff = getNextFundingTime().getTime() - Date.now();
      if (diff <= 0) { setRemaining("정산 중"); return; }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setRemaining(`${h}시간 ${m}분 ${s}초`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return remaining;
}

// --- 메인 ---
export default function DashboardPage() {
  const { status, loading, start, stop, emergencyStop } = useTrading();
  const { tickers } = useTickerStream(["BTCUSDT"]);
  const btcTicker = tickers["BTCUSDT"];
  const fundingCountdown = useFundingCountdown();

  // 추가 데이터
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [posSummary, setPosSummary] = useState<PositionSummary | null>(null);
  const [risk, setRisk] = useState<RiskStatus | null>(null);
  const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, posRes, riskRes, tradesRes] = await Promise.allSettled([
        api.get<TradeStats>("/api/trades/stats"),
        api.get<PositionSummary>("/api/positions/summary"),
        api.get<RiskStatus>("/api/risk/status"),
        api.get<RecentTrade[]>("/api/trades"),
      ]);
      if (statsRes.status === "fulfilled") setStats(statsRes.value.data);
      if (posRes.status === "fulfilled") setPosSummary(posRes.value.data);
      if (riskRes.status === "fulfilled") setRisk(riskRes.value.data);
      if (tradesRes.status === "fulfilled") {
        const trades = tradesRes.value.data ?? [];
        setRecentTrades(Array.isArray(trades) ? trades.slice(0, 5) : []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 10000);
    return () => clearInterval(id);
  }, [fetchData]);

  const isRunning = status?.running ?? false;
  const balance = risk?.balance ?? 0;
  const todayPnl = stats?.todayPnl ?? 0;
  const weekPnl = stats?.weekPnl ?? 0;
  const unrealizedPnl = posSummary?.totalUnrealizedPnlPct ?? 0;
  const positions = posSummary?.positions ?? status?.positions ?? [];

  return (
    <div className="space-y-6">
      {/* --- 트레이딩 제어 패널 --- */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={isRunning ? "default" : "secondary"}>
              {isRunning ? "실행 중" : "중지"}
            </Badge>
            {status && (
              <Badge variant="outline">
                {status.mode === "paper" ? "모의매매" : "실전매매"}
              </Badge>
            )}
            {(status?.wsConnected || risk?.wsConnected) ? (
              <span className="flex items-center gap-1 text-xs text-green-500">
                <Wifi className="h-3 w-3" /> 연결됨
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <WifiOff className="h-3 w-3" /> 미연결
              </span>
            )}
            {btcTicker && (
              <span className="font-mono text-sm">
                BTC ${btcTicker.price.toLocaleString()}
              </span>
            )}
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              다음 펀딩: {fundingCountdown}
            </span>
          </div>
          <div className="flex gap-2">
            {!isRunning ? (
              <Button size="sm" onClick={() => start()} disabled={loading}>
                <Play className="mr-1 h-4 w-4" /> 시작
              </Button>
            ) : (
              <Button size="sm" variant="outline" onClick={stop} disabled={loading}>
                <Square className="mr-1 h-4 w-4" /> 중지
              </Button>
            )}
            <Button
              size="sm"
              variant="destructive"
              onClick={emergencyStop}
              disabled={loading}
            >
              <AlertTriangle className="mr-1 h-4 w-4" /> 긴급정지
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* --- 핵심 지표 카드 4개 --- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="총 자산"
          value={balance > 0 ? `$${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
          change={status?.mode === "paper" ? "모의잔고" : "실전잔고"}
          changeType="neutral"
          icon={DollarSign}
        />
        <StatCard
          title="오늘 PnL"
          value={`${todayPnl >= 0 ? "+" : ""}$${Math.abs(todayPnl).toFixed(4)}`}
          change={`주간: ${weekPnl >= 0 ? "+" : ""}$${Math.abs(weekPnl).toFixed(4)}`}
          changeType={todayPnl >= 0 ? "profit" : "loss"}
          icon={todayPnl >= 0 ? TrendingUp : TrendingDown}
        />
        <StatCard
          title="미실현 PnL"
          value={`${unrealizedPnl >= 0 ? "+" : ""}${unrealizedPnl.toFixed(2)}%`}
          change={`포지션 ${posSummary?.totalPositions ?? 0}개`}
          changeType={unrealizedPnl >= 0 ? "profit" : unrealizedPnl < 0 ? "loss" : "neutral"}
          icon={unrealizedPnl >= 0 ? TrendingUp : TrendingDown}
        />
        <StatCard
          title="승률"
          value={stats ? `${stats.winRate.toFixed(1)}%` : "—"}
          change={stats ? `${stats.winCount}승 ${stats.lossCount}패 (${stats.totalRecentTrades}건)` : "데이터 없음"}
          changeType={stats && stats.winRate >= 50 ? "profit" : stats && stats.winRate > 0 ? "loss" : "neutral"}
          icon={Target}
        />
      </div>

      {/* --- 중단: 전략 성과 + 포지션 --- */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 전략 성과 & 최근 거래 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4" /> 전략 현황 & 최근 거래
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* 전략 요약 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <MiniStat label="전략" value={status?.symbols?.length ? status.symbols.map(s => s.split("/")[0]).join(", ") : "—"} />
              <MiniStat label="오늘 거래" value={`${stats?.todayTradeCount ?? 0}회`} />
              <MiniStat label="레버리지" value={risk ? `${risk.leverage}x / ${risk.maxLeverage}x` : "—"} />
              <MiniStat label="위험도" value={risk ? `${risk.overallRiskScore}점` : "—"} color={risk && risk.overallRiskScore > 60 ? "text-red-500" : risk && risk.overallRiskScore > 30 ? "text-yellow-500" : "text-green-500"} />
            </div>

            {/* 최근 거래 */}
            {recentTrades.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground mb-2">최근 거래</p>
                {recentTrades.map((t, i) => (
                  <div key={i} className="flex items-center justify-between text-sm border rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={t.side === "long" ? "default" : "destructive"} className="text-xs">
                        {t.side === "long" ? "롱" : t.side === "short" ? "숏" : t.side ?? "—"}
                      </Badge>
                      <span className="text-muted-foreground text-xs">
                        {t.symbol ?? "BTC/USDT"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {t.reason && <span className="text-xs text-muted-foreground max-w-[120px] truncate">{t.reason}</span>}
                      <span className={`font-mono text-sm font-semibold ${(t.pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
                        {(t.pnl ?? 0) >= 0 ? "+" : ""}{(t.pnl ?? 0).toFixed(4)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-32 items-center justify-center text-muted-foreground text-sm">
                {isRunning ? "모의매매 데이터 수집 중..." : "엔진이 중지 상태입니다"}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 활성 포지션 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" /> 활성 포지션
            </CardTitle>
          </CardHeader>
          <CardContent>
            {positions.length === 0 ? (
              <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
                포지션 없음
              </div>
            ) : (
              <div className="space-y-3">
                {positions.map((pos: any, i: number) => (
                  <div
                    key={pos.symbol ?? i}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{pos.symbol ?? "BTC/USDT"}</span>
                        <Badge
                          variant={pos.side === "long" ? "default" : "destructive"}
                          className="text-xs"
                        >
                          {pos.side === "long" ? "롱" : "숏"}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        진입: ${Number(pos.entryPrice ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="text-right">
                      <div
                        className={`font-mono text-sm font-semibold ${
                          (pos.pnlPct ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                        }`}
                      >
                        {(pos.pnlPct ?? 0) >= 0 ? "+" : ""}{(pos.pnlPct ?? 0).toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* --- 하단: 리스크 게이지 --- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> 리스크 현황
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <RiskMeter
              label="전체 위험도"
              value={risk?.overallRiskScore ?? 0}
              max={100}
              suffix="점"
            />
            <RiskMeter
              label="일일 손실"
              value={risk?.dailyUsedPct ?? 0}
              max={100}
              suffix="%"
            />
            <RiskMeter
              label="레버리지"
              value={risk?.leverage ?? 0}
              max={risk?.maxLeverage ?? 10}
              suffix="x"
            />
            <RiskMeter
              label="연속 손실"
              value={risk?.consecutiveLosses ?? 0}
              max={risk?.consecutiveLossStopAt ?? 5}
              suffix="회"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// --- 미니 통계 ---
function MiniStat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border p-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-sm font-semibold font-mono mt-0.5 ${color ?? ""}`}>{value}</p>
    </div>
  );
}

// --- 리스크 게이지 ---
function RiskMeter({
  label,
  value,
  max,
  suffix = "%",
}: {
  label: string;
  value: number;
  max: number;
  suffix?: string;
}) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const isWarning = percentage > 60;
  const isDanger = percentage > 80;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">
          {value}{suffix} / {max}{suffix}
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${
            isDanger
              ? "bg-red-500"
              : isWarning
                ? "bg-yellow-500"
                : "bg-green-500"
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
