/**
 * 메인 대시보드 페이지
 * - 핵심 지표 카드, 자산 곡선, 활성 포지션, 리스크 게이지
 * - 사용처: /dashboard (로그인 후 홈)
 */

"use client";

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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/dashboard/StatCard";
import { useTrading } from "@/hooks/useTrading";
import { useTickerStream } from "@/hooks/useWebSocket";

export default function DashboardPage() {
  const { status, loading, start, stop, emergencyStop } = useTrading();
  const { tickers } = useTickerStream(["BTCUSDT"]);
  const btcTicker = tickers["BTCUSDT"];

  const isRunning = status?.running ?? false;
  const todayPnl = status?.todayPnl ?? 0;
  const nextFunding = status?.nextFundingMinutes ?? 0;
  const positions = status?.positions ?? [];

  return (
    <div className="space-y-6">
      {/* --- 트레이딩 제어 패널 --- */}
      <Card>
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-4">
            <Badge variant={isRunning ? "default" : "secondary"}>
              {isRunning ? "실행 중" : "중지"}
            </Badge>
            {status && (
              <Badge variant="outline">
                {status.mode === "paper" ? "모의매매" : "실전매매"}
              </Badge>
            )}
            {status?.wsConnected ? (
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
              다음 펀딩: {Math.floor(nextFunding)}분
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

      {/* --- 상단: 핵심 지표 카드 4개 --- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="총 자산"
          value="$10,000.00"
          change="+$234.56"
          changeType="profit"
          icon={DollarSign}
        />
        <StatCard
          title="일일 PnL"
          value={`${todayPnl >= 0 ? "+" : ""}$${Math.abs(todayPnl).toFixed(2)}`}
          change={`${todayPnl >= 0 ? "+" : ""}${todayPnl.toFixed(2)}%`}
          changeType={todayPnl >= 0 ? "profit" : "loss"}
          icon={todayPnl >= 0 ? TrendingUp : TrendingDown}
        />
        <StatCard
          title="미실현 PnL"
          value="-$45.20"
          change="-0.45%"
          changeType="loss"
          icon={TrendingDown}
        />
        <StatCard
          title="활성 포지션"
          value={String(positions.length)}
          change={isRunning ? "실행 중" : "대기"}
          changeType="neutral"
          icon={Activity}
        />
      </div>

      {/* --- 중단: 차트 + 포지션 요약 --- */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 자산 곡선 차트 (2/3 너비) */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              자산 곡선 (Equity Curve)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center text-muted-foreground">
              차트 컴포넌트 (Phase 2에서 구현)
            </div>
          </CardContent>
        </Card>

        {/* 활성 포지션 요약 (1/3 너비) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              활성 포지션
            </CardTitle>
          </CardHeader>
          <CardContent>
            {positions.length === 0 ? (
              <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
                포지션 없음
              </div>
            ) : (
              <div className="space-y-3">
                {positions.map((pos) => (
                  <div
                    key={pos.symbol}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{pos.symbol}</span>
                        <Badge
                          variant={pos.side === "long" ? "default" : "destructive"}
                          className="text-xs"
                        >
                          {pos.side === "long" ? "롱" : "숏"}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        진입: ${pos.entryPrice.toLocaleString()} | 현재: ${pos.markPrice.toLocaleString()}
                      </div>
                    </div>
                    <div className="text-right">
                      <div
                        className={`font-mono text-sm font-semibold ${
                          pos.pnlPct >= 0 ? "text-green-500" : "text-red-500"
                        }`}
                      >
                        {pos.pnlPct >= 0 ? "+" : ""}{pos.pnlPct.toFixed(2)}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {Math.floor(pos.holdMinutes / 60)}시간 {Math.floor(pos.holdMinutes % 60)}분
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* --- 하단: 전략 성과 + 리스크 게이지 --- */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              전략별 성과
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
              전략 성과 차트 (Phase 2에서 구현)
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              리스크 현황
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <RiskMeter label="Portfolio Heat" value={45} max={80} />
              <RiskMeter label="Daily Loss" value={1.2} max={5} suffix="%" />
              <RiskMeter label="Max Drawdown" value={5.3} max={15} suffix="%" />
              <RiskMeter label="Leverage" value={3} max={10} suffix="x" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// --- 리스크 게이지 (인라인 컴포넌트, 간단하므로 분리 불필요) ---
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
  const percentage = Math.min((value / max) * 100, 100);
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
