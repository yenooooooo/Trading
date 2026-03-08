"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  TrendingDown,
  Activity,
  Clock,
  RefreshCw,
  AlertCircle,
  Shield,
  Flame,
  Ban,
  Gauge,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface RiskStatus {
  balance: number;
  mode: string;
  daily_pnl: number;
  daily_loss_limit_pct: number;
  daily_used_pct: number;
  daily_breached: boolean;
  weekly_pnl: number;
  weekly_loss_limit_pct: number;
  weekly_used_pct: number;
  weekly_breached: boolean;
  open_positions: number;
  max_positions: number;
  position_used_pct: number;
  today_trade_count: number;
  max_daily_trades: number;
  trade_used_pct: number;
  leverage: number;
  max_leverage: number;
  leverage_used_pct: number;
  consecutive_losses: number;
  consecutive_loss_reduce_at: number;
  consecutive_loss_stop_at: number;
  loss_action: "none" | "reduce" | "stop";
  reduce_factor: number;
  max_risk_per_trade_pct: number;
  overall_risk_score: number;
  running: boolean;
  ws_connected: boolean;
}

function RiskGauge({
  label,
  value,
  max,
  suffix = "%",
  icon: Icon,
  description,
  breached,
}: {
  label: string;
  value: number;
  max: number;
  suffix?: string;
  icon: React.ElementType;
  description?: string;
  breached?: boolean;
}) {
  const pct = Math.min((value / max) * 100, 100);
  const isDanger = pct > 80 || breached;
  const isWarning = pct > 50;

  return (
    <Card className={breached ? "border-red-500/50 bg-red-500/5" : ""}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={`h-4 w-4 ${isDanger ? "text-red-500" : isWarning ? "text-yellow-500" : "text-green-500"}`} />
            <span className="text-sm font-medium">{label}</span>
          </div>
          {breached && (
            <Badge variant="destructive" className="text-xs">
              한도 초과
            </Badge>
          )}
        </div>
        <div className="flex items-end justify-between">
          <span className={`text-2xl font-mono font-bold ${isDanger ? "text-red-500" : isWarning ? "text-yellow-500" : "text-green-500"}`}>
            {value.toFixed(1)}{suffix}
          </span>
          <span className="text-xs text-muted-foreground">
            / {max}{suffix}
          </span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isDanger ? "bg-red-500" : isWarning ? "bg-yellow-500" : "bg-green-500"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

function OverallRiskMeter({ score }: { score: number }) {
  const getColor = (s: number) => {
    if (s >= 80) return { color: "text-red-500", bg: "bg-red-500", label: "위험" };
    if (s >= 60) return { color: "text-orange-500", bg: "bg-orange-500", label: "주의" };
    if (s >= 40) return { color: "text-yellow-500", bg: "bg-yellow-500", label: "보통" };
    if (s >= 20) return { color: "text-green-500", bg: "bg-green-500", label: "안전" };
    return { color: "text-green-400", bg: "bg-green-400", label: "매우 안전" };
  };

  const { color, bg, label } = getColor(score);

  return (
    <Card>
      <CardContent className="p-6 flex flex-col items-center space-y-4">
        <div className="relative w-32 h-32">
          {/* Circular gauge background */}
          <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
            <circle
              cx="60" cy="60" r="50"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              className="text-muted"
            />
            <circle
              cx="60" cy="60" r="50"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              strokeDasharray={`${score * 3.14} 314`}
              strokeLinecap="round"
              className={color}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-mono font-bold ${color}`}>{score}</span>
            <span className="text-xs text-muted-foreground">/ 100</span>
          </div>
        </div>
        <div className="text-center space-y-1">
          <Badge className={`${bg} text-white`}>{label}</Badge>
          <p className="text-sm font-medium">전체 위험도</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function RiskPage() {
  const [risk, setRisk] = useState<RiskStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRisk = useCallback(async () => {
    try {
      const res = await api.get<RiskStatus>("/api/risk/status");
      setRisk(res.data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "리스크 데이터 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRisk();
    const id = setInterval(fetchRisk, 5000);
    return () => clearInterval(id);
  }, [fetchRisk]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">리스크 대시보드</h1>
        <div className="flex items-center gap-2">
          <Badge variant={risk?.running ? "default" : "secondary"}>
            {risk?.running ? "실행 중" : "대기"}
          </Badge>
          <Badge variant="outline">
            {risk?.mode === "paper" ? "모의매매" : "실전매매"}
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchRisk}>
            <RefreshCw className="mr-1 h-4 w-4" />
            새로고침
          </Button>
        </div>
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

      {/* Alerts */}
      {risk?.daily_breached && (
        <Card className="border-red-500 bg-red-500/10">
          <CardContent className="flex items-center gap-3 py-3">
            <Ban className="h-5 w-5 text-red-500 shrink-0" />
            <div>
              <p className="font-semibold text-red-500">일일 손실 한도 초과</p>
              <p className="text-sm text-muted-foreground">금일 추가 매매가 차단됩니다. 내일 자동 리셋됩니다.</p>
            </div>
          </CardContent>
        </Card>
      )}
      {risk?.weekly_breached && (
        <Card className="border-red-500 bg-red-500/10">
          <CardContent className="flex items-center gap-3 py-3">
            <Ban className="h-5 w-5 text-red-500 shrink-0" />
            <div>
              <p className="font-semibold text-red-500">주간 손실 한도 초과</p>
              <p className="text-sm text-muted-foreground">이번 주 추가 매매가 차단됩니다. 월요일 자동 리셋됩니다.</p>
            </div>
          </CardContent>
        </Card>
      )}
      {risk?.loss_action === "stop" && (
        <Card className="border-red-500 bg-red-500/10">
          <CardContent className="flex items-center gap-3 py-3">
            <Ban className="h-5 w-5 text-red-500 shrink-0" />
            <div>
              <p className="font-semibold text-red-500">{risk.consecutive_losses}연패 — 매매 중단</p>
              <p className="text-sm text-muted-foreground">연속 {risk.consecutive_loss_stop_at}회 손실로 당일 매매가 중단되었습니다.</p>
            </div>
          </CardContent>
        </Card>
      )}
      {risk?.loss_action === "reduce" && (
        <Card className="border-yellow-500 bg-yellow-500/10">
          <CardContent className="flex items-center gap-3 py-3">
            <AlertTriangle className="h-5 w-5 text-yellow-500 shrink-0" />
            <div>
              <p className="font-semibold text-yellow-500">{risk.consecutive_losses}연패 — 포지션 축소</p>
              <p className="text-sm text-muted-foreground">포지션 크기가 {(risk.reduce_factor * 100)}%로 축소됩니다.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top row: Overall Risk + Balance */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <OverallRiskMeter score={risk?.overall_risk_score ?? 0} />

        <Card>
          <CardContent className="p-4 space-y-2">
            <p className="text-xs text-muted-foreground">잔고</p>
            <p className="text-2xl font-mono font-bold">
              ${(risk?.balance ?? 0).toFixed(2)}
            </p>
            <div className="space-y-1 pt-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">일일 PnL</span>
                <span className={`font-mono ${(risk?.daily_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
                  {(risk?.daily_pnl ?? 0) >= 0 ? "+" : ""}{(risk?.daily_pnl ?? 0).toFixed(4)}%
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">주간 PnL</span>
                <span className={`font-mono ${(risk?.weekly_pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
                  {(risk?.weekly_pnl ?? 0) >= 0 ? "+" : ""}{(risk?.weekly_pnl ?? 0).toFixed(4)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 space-y-2">
            <p className="text-xs text-muted-foreground">연속 손실 카운터</p>
            <div className="flex items-end gap-2">
              <span className={`text-4xl font-mono font-bold ${
                (risk?.consecutive_losses ?? 0) >= (risk?.consecutive_loss_stop_at ?? 5)
                  ? "text-red-500"
                  : (risk?.consecutive_losses ?? 0) >= (risk?.consecutive_loss_reduce_at ?? 3)
                    ? "text-yellow-500"
                    : "text-green-500"
              }`}>
                {risk?.consecutive_losses ?? 0}
              </span>
              <span className="text-sm text-muted-foreground mb-1">연패</span>
            </div>
            <div className="flex gap-1 pt-2">
              {Array.from({ length: risk?.consecutive_loss_stop_at ?? 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`h-2 flex-1 rounded-full ${
                    i < (risk?.consecutive_losses ?? 0)
                      ? i >= (risk?.consecutive_loss_reduce_at ?? 3) - 1
                        ? "bg-red-500"
                        : "bg-yellow-500"
                      : "bg-muted"
                  }`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-muted-foreground pt-1">
              <span>{risk?.consecutive_loss_reduce_at}연패: 50% 축소</span>
              <span>{risk?.consecutive_loss_stop_at}연패: 중단</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 space-y-2">
            <p className="text-xs text-muted-foreground">오늘 거래</p>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-mono font-bold">
                {risk?.today_trade_count ?? 0}
              </span>
              <span className="text-sm text-muted-foreground mb-1">
                / {risk?.max_daily_trades ?? 3}회
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden mt-2">
              <div
                className={`h-full rounded-full transition-all ${
                  (risk?.trade_used_pct ?? 0) >= 100 ? "bg-red-500" : "bg-blue-500"
                }`}
                style={{ width: `${risk?.trade_used_pct ?? 0}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risk Gauges */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <RiskGauge
          label="일일 손실 한도"
          value={risk?.daily_used_pct ?? 0}
          max={100}
          icon={TrendingDown}
          description={`한도: 잔고의 ${risk?.daily_loss_limit_pct ?? 8}% | 현재 PnL: ${(risk?.daily_pnl ?? 0).toFixed(4)}%`}
          breached={risk?.daily_breached}
        />
        <RiskGauge
          label="주간 손실 한도"
          value={risk?.weekly_used_pct ?? 0}
          max={100}
          icon={Flame}
          description={`한도: 잔고의 ${risk?.weekly_loss_limit_pct ?? 15}% | 현재 PnL: ${(risk?.weekly_pnl ?? 0).toFixed(4)}%`}
          breached={risk?.weekly_breached}
        />
        <RiskGauge
          label="레버리지"
          value={risk?.leverage ?? 0}
          max={risk?.max_leverage ?? 5}
          suffix="x"
          icon={Gauge}
          description={`최대 ${risk?.max_leverage ?? 5}x (하드 리밋)`}
        />
        <RiskGauge
          label="포지션 노출도"
          value={risk?.open_positions ?? 0}
          max={risk?.max_positions ?? 2}
          suffix="개"
          icon={Activity}
          description={`잔고 $${(risk?.balance ?? 0).toFixed(0)} 기준 최대 ${risk?.max_positions ?? 2}개`}
        />
        <RiskGauge
          label="거래 빈도"
          value={risk?.today_trade_count ?? 0}
          max={risk?.max_daily_trades ?? 3}
          suffix="회"
          icon={Clock}
          description="일일 최대 거래 횟수"
        />
        <RiskGauge
          label="단일 포지션 리스크"
          value={risk?.max_risk_per_trade_pct ?? 5}
          max={10}
          icon={Shield}
          description={`잔고의 ${risk?.max_risk_per_trade_pct ?? 5}%까지 허용`}
        />
      </div>

      {/* Risk Rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" />
            리스크 관리 규칙
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <h3 className="font-medium text-muted-foreground">손실 한도</h3>
              <ul className="space-y-1.5">
                <li className="flex justify-between">
                  <span>일일 최대 손실</span>
                  <span className="font-mono">{risk?.daily_loss_limit_pct ?? 8}%</span>
                </li>
                <li className="flex justify-between">
                  <span>주간 최대 손실</span>
                  <span className="font-mono">{risk?.weekly_loss_limit_pct ?? 15}%</span>
                </li>
                <li className="flex justify-between">
                  <span>단일 포지션 리스크</span>
                  <span className="font-mono">3~5%</span>
                </li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-medium text-muted-foreground">거래 제한</h3>
              <ul className="space-y-1.5">
                <li className="flex justify-between">
                  <span>최대 레버리지</span>
                  <span className="font-mono">{risk?.max_leverage ?? 5}x</span>
                </li>
                <li className="flex justify-between">
                  <span>일일 최대 거래</span>
                  <span className="font-mono">{risk?.max_daily_trades ?? 3}회</span>
                </li>
                <li className="flex justify-between">
                  <span>최대 동시 포지션</span>
                  <span className="font-mono">{risk?.max_positions ?? 2}개</span>
                </li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-medium text-muted-foreground">연속 손실 대응</h3>
              <ul className="space-y-1.5">
                <li className="flex justify-between">
                  <span>{risk?.consecutive_loss_reduce_at ?? 3}연패</span>
                  <span className="font-mono">포지션 50% 축소</span>
                </li>
                <li className="flex justify-between">
                  <span>{risk?.consecutive_loss_stop_at ?? 5}연패</span>
                  <span className="font-mono text-red-500">당일 매매 중단</span>
                </li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-medium text-muted-foreground">수익성 필터</h3>
              <ul className="space-y-1.5">
                <li className="flex justify-between">
                  <span>최소 수익 요건</span>
                  <span className="font-mono">왕복 수수료 x2</span>
                </li>
                <li className="flex justify-between">
                  <span>테이커 수수료</span>
                  <span className="font-mono">0.04%</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
