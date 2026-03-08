"use client";

/**
 * 전략 상세 페이지
 * - 전략 정보, 예상 수수료, R:R, 파라미터 수정, 신호 체크
 * - 사용처: /dashboard/strategies/[id]
 */

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Play, Pause, RefreshCw, Trash2, Save,
  TrendingDown, Zap, ArrowUpRight, Activity, DollarSign,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { Strategy, SignalCheck, StrategyType } from "@/types/strategy";
import { STRATEGY_META, estimateFees } from "@/lib/strategy-meta";

// 전략 아이콘
const STRATEGY_ICONS: Record<string, React.ReactNode> = {
  funding_rate: <TrendingDown className="w-5 h-5 text-blue-400" />,
  liquidation_bounce: <Zap className="w-5 h-5 text-yellow-400" />,
  volatility_breakout: <ArrowUpRight className="w-5 h-5 text-green-400" />,
};

export default function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [signal, setSignal] = useState<SignalCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editParams, setEditParams] = useState<Record<string, number | string>>({});
  const [saving, setSaving] = useState(false);

  // 전략 로드
  useEffect(() => {
    api.get<Strategy>(`/api/strategies/${id}`)
      .then((res) => {
        setStrategy(res.data ?? null);
        if (res.data) setEditParams({ ...res.data.params });
      })
      .catch(() => router.push("/dashboard/strategies"))
      .finally(() => setLoading(false));
  }, [id, router]);

  // 메타 정보
  const meta = strategy
    ? STRATEGY_META[strategy.strategy_type as StrategyType] ?? null
    : null;

  // 수수료 추정 (포지션 크기 예시: 잔고 $200 × 레버리지 × 포지션 비율)
  const feeEstimate = useMemo(() => {
    if (!strategy) return null;
    const posSize = 200 * strategy.leverage * strategy.max_position_pct;
    return estimateFees(posSize, strategy.leverage);
  }, [strategy]);

  // 예상 R:R 계산
  const expectedRR = useMemo(() => {
    if (!strategy || !feeEstimate) return null;
    const minMove = Number(strategy.params.min_expected_move ?? 0.3);
    const tp = Number(strategy.params.tp_atr_mult ?? 2.0);
    const sl = Number(strategy.params.sl_atr_mult ?? 1.0);

    const grossRR = tp > 0 && sl > 0 ? tp / sl : null;
    const feeImpact = feeEstimate.round_trip_fee_pct;
    const netMinMove = minMove - feeImpact;

    return { grossRR, feeImpact, netMinMove, minMove };
  }, [strategy, feeEstimate]);

  // 신호 체크
  const checkSignal = async () => {
    setChecking(true);
    try {
      const res = await api.get<SignalCheck>(`/api/strategies/${id}/signal`);
      setSignal(res.data ?? null);
    } catch {
      setSignal(null);
    } finally {
      setChecking(false);
    }
  };

  // 시작/중지
  const toggleStatus = async () => {
    if (!strategy) return;
    const endpoint = strategy.is_active
      ? `/api/strategies/${id}/stop`
      : `/api/strategies/${id}/start`;
    const res = await api.post<Strategy>(endpoint);
    setStrategy(res.data ?? null);
  };

  // 삭제
  const handleDelete = async () => {
    if (!confirm("이 전략을 삭제하시겠습니까?")) return;
    await api.delete(`/api/strategies/${id}`);
    router.push("/dashboard/strategies");
  };

  // 파라미터 저장
  const handleSaveParams = async () => {
    setSaving(true);
    try {
      const res = await api.put<Strategy>(`/api/strategies/${id}`, {
        params: editParams,
      });
      setStrategy(res.data ?? null);
      setEditing(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  // 신호 색상
  const signalColor = (sig: string) => {
    if (sig === "long") return "text-green-400";
    if (sig === "short") return "text-red-400";
    if (sig === "close") return "text-yellow-400";
    return "text-zinc-400";
  };

  if (loading || !strategy) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-400">로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/strategies">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          {STRATEGY_ICONS[strategy.strategy_type] ?? (
            <Activity className="w-5 h-5 text-zinc-400" />
          )}
          <h1 className="text-2xl font-bold">{strategy.name}</h1>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              strategy.is_active
                ? "bg-green-500/20 text-green-400"
                : "bg-zinc-500/20 text-zinc-400"
            }`}
          >
            {strategy.is_active ? "실행 중" : "중지"}
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={toggleStatus}>
            {strategy.is_active ? (
              <><Pause className="w-4 h-4 mr-2" />중지</>
            ) : (
              <><Play className="w-4 h-4 mr-2" />시작</>
            )}
          </Button>
          <Button variant="ghost" onClick={handleDelete}>
            <Trash2 className="w-4 h-4 text-red-400" />
          </Button>
        </div>
      </div>

      {/* 전략 정보 */}
      <div className="border border-zinc-800 rounded-lg p-5 space-y-3">
        <h2 className="font-semibold">전략 정보</h2>
        {meta && (
          <p className="text-sm text-zinc-400">{meta.description}</p>
        )}
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-zinc-400">유형</span>
          <span>{meta?.name ?? strategy.strategy_type}</span>
          <span className="text-zinc-400">심볼</span>
          <span>{strategy.symbol}</span>
          <span className="text-zinc-400">타임프레임</span>
          <span>{strategy.interval}</span>
          <span className="text-zinc-400">레버리지</span>
          <span>x{strategy.leverage}</span>
          <span className="text-zinc-400">포지션 비율</span>
          <span>{(strategy.max_position_pct * 100).toFixed(0)}%</span>
          {meta && (
            <>
              <span className="text-zinc-400">권장 시드</span>
              <span>{meta.seedRange}</span>
              <span className="text-zinc-400">거래 빈도</span>
              <span>{meta.frequency}</span>
            </>
          )}
        </div>
      </div>

      {/* 예상 수수료 */}
      {feeEstimate && (
        <div className="border border-zinc-800 rounded-lg p-5 space-y-3">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-yellow-400" />
            <h2 className="font-semibold">예상 수수료</h2>
          </div>
          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <span className="text-zinc-400">왕복 수수료</span>
            <span>
              {feeEstimate.round_trip_fee_pct}%
              <span className="text-zinc-500 ml-2">
                (${feeEstimate.round_trip_fee_usd.toFixed(2)}/거래)
              </span>
            </span>
            <span className="text-zinc-400">최소 수익률</span>
            <span className="text-yellow-400">
              {feeEstimate.min_profitable_move}% 이상 필요
            </span>
          </div>
          {expectedRR && (
            <div className="bg-zinc-900/50 rounded p-3 space-y-1.5 text-sm mt-2">
              <div className="font-medium text-zinc-300">
                수수료 차감 후 예상 R:R
              </div>
              <div className="grid grid-cols-2 gap-y-1.5">
                {expectedRR.grossRR !== null && (
                  <>
                    <span className="text-zinc-400">TP:SL 비율</span>
                    <span>{expectedRR.grossRR.toFixed(1)} : 1</span>
                  </>
                )}
                <span className="text-zinc-400">예상 변동</span>
                <span>{expectedRR.minMove}%</span>
                <span className="text-zinc-400">수수료 차감</span>
                <span>-{expectedRR.feeImpact}%</span>
                <span className="text-zinc-400">순 예상 변동</span>
                <span className={expectedRR.netMinMove > 0 ? "text-green-400" : "text-red-400"}>
                  {expectedRR.netMinMove.toFixed(4)}%
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 파라미터 */}
      {Object.keys(strategy.params).length > 0 && (
        <div className="border border-zinc-800 rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">파라미터</h2>
            {!editing ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditParams({ ...strategy.params });
                  setEditing(true);
                }}
              >
                수정
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing(false)}
                >
                  취소
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveParams}
                  disabled={saving}
                  className="gap-1"
                >
                  <Save className="w-3 h-3" />
                  {saving ? "저장 중..." : "저장"}
                </Button>
              </div>
            )}
          </div>

          {editing ? (
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(editParams).map(([key, val]) => (
                <div key={key}>
                  <Label htmlFor={`param-${key}`} className="text-sm">
                    {meta?.paramLabels[key] ?? key}
                  </Label>
                  <Input
                    id={`param-${key}`}
                    type="number"
                    step="any"
                    value={val}
                    onChange={(e) =>
                      setEditParams({
                        ...editParams,
                        [key]: Number(e.target.value),
                      })
                    }
                  />
                  {meta?.paramDescriptions[key] && (
                    <p className="text-xs text-zinc-500 mt-1">
                      {meta.paramDescriptions[key]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              {Object.entries(strategy.params).map(([key, val]) => (
                <div key={key} className="contents">
                  <span className="text-zinc-400">
                    {meta?.paramLabels[key] ?? key}
                  </span>
                  <span>{String(val)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 실시간 신호 체크 */}
      <div className="border border-zinc-800 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">실시간 신호</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={checkSignal}
            disabled={checking}
            className="gap-2"
          >
            <RefreshCw className={`w-3 h-3 ${checking ? "animate-spin" : ""}`} />
            {checking ? "분석 중..." : "신호 체크"}
          </Button>
        </div>

        {signal ? (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-bold uppercase ${signalColor(signal.signal)}`}>
                {signal.signal}
              </span>
              <span className="text-sm text-zinc-400">
                강도: {(signal.strength * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-zinc-400">{signal.reason}</p>
          </div>
        ) : (
          <p className="text-sm text-zinc-500">
            &quot;신호 체크&quot; 버튼을 눌러 현재 시장 상태를 분석하세요
          </p>
        )}
      </div>
    </div>
  );
}
