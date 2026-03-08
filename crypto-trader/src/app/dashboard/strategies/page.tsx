"use client";

/**
 * 전략 목록 페이지
 * - 새 3개 전략 아이콘/설명/권장 시드 표시
 * - 사용처: /dashboard/strategies
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus, Play, Pause, Trash2, Activity,
  TrendingDown, Zap, ArrowUpRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Strategy } from "@/types/strategy";
import type { StrategyType } from "@/types/strategy";
import { STRATEGY_META } from "@/lib/strategy-meta";

// 전략 아이콘 매핑
const STRATEGY_ICONS: Record<string, React.ReactNode> = {
  funding_rate: <TrendingDown className="w-5 h-5 text-blue-400" />,
  liquidation_bounce: <Zap className="w-5 h-5 text-yellow-400" />,
  volatility_breakout: <ArrowUpRight className="w-5 h-5 text-green-400" />,
};

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStrategies = async () => {
    try {
      const res = await api.get<Strategy[]>("/api/strategies");
      setStrategies(res.data ?? []);
    } catch {
      setStrategies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const toggleStrategy = async (id: string, isActive: boolean) => {
    const endpoint = isActive
      ? `/api/strategies/${id}/stop`
      : `/api/strategies/${id}/start`;
    await api.post(endpoint);
    fetchStrategies();
  };

  const deleteStrategy = async (id: string) => {
    if (!confirm("이 전략을 삭제하시겠습니까?")) return;
    await api.delete(`/api/strategies/${id}`);
    fetchStrategies();
  };

  const statusColor = (status: string) => {
    if (status === "active") return "bg-green-500/20 text-green-400";
    if (status === "paused") return "bg-yellow-500/20 text-yellow-400";
    return "bg-zinc-500/20 text-zinc-400";
  };

  const getMeta = (type: string) =>
    STRATEGY_META[type as StrategyType] ?? null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-400">전략 로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">전략 관리</h1>
        <Link href="/dashboard/strategies/new">
          <Button className="gap-2">
            <Plus className="w-4 h-4" />
            새 전략
          </Button>
        </Link>
      </div>

      {/* 전략 목록 */}
      {strategies.length === 0 ? (
        <div className="space-y-6">
          {/* 빈 상태 */}
          <div className="border border-zinc-800 rounded-lg p-12 text-center">
            <Activity className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400 mb-4">등록된 전략이 없습니다</p>
            <Link href="/dashboard/strategies/new">
              <Button variant="outline">첫 전략 만들기</Button>
            </Link>
          </div>

          {/* 전략 소개 카드 */}
          <div>
            <h2 className="text-lg font-semibold mb-3">사용 가능한 전략</h2>
            <div className="grid gap-4 md:grid-cols-3">
              {(["funding_rate", "liquidation_bounce", "volatility_breakout"] as StrategyType[]).map(
                (type) => {
                  const meta = STRATEGY_META[type];
                  return (
                    <div
                      key={type}
                      className="border border-zinc-800 rounded-lg p-5 space-y-3"
                    >
                      <div className="flex items-center gap-2">
                        {STRATEGY_ICONS[type]}
                        <span className="font-semibold">{meta.name}</span>
                      </div>
                      <p className="text-sm text-zinc-400 leading-relaxed">
                        {meta.description}
                      </p>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                          시드 {meta.seedRange}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                          {meta.frequency}
                        </span>
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-4">
          {strategies.map((s) => {
            const meta = getMeta(s.strategy_type);
            return (
              <div
                key={s.id}
                className="border border-zinc-800 rounded-lg p-5 hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  {/* 전략 정보 */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      {STRATEGY_ICONS[s.strategy_type] ?? (
                        <Activity className="w-5 h-5 text-zinc-400" />
                      )}
                      <Link
                        href={`/dashboard/strategies/${s.id}`}
                        className="text-lg font-semibold hover:text-blue-400 transition-colors"
                      >
                        {s.name}
                      </Link>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${statusColor(s.status)}`}
                      >
                        {s.status === "active" ? "실행 중" : "중지"}
                      </span>
                    </div>
                    <div className="flex gap-4 text-sm text-zinc-400">
                      <span>{meta?.name ?? s.strategy_type}</span>
                      <span>{s.symbol}</span>
                      <span>{s.interval}</span>
                      <span>x{s.leverage}</span>
                      {meta && (
                        <span className="text-zinc-500">
                          시드 {meta.seedRange}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 액션 버튼 */}
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => toggleStrategy(s.id, s.is_active)}
                      title={s.is_active ? "중지" : "시작"}
                    >
                      {s.is_active ? (
                        <Pause className="w-4 h-4 text-yellow-400" />
                      ) : (
                        <Play className="w-4 h-4 text-green-400" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteStrategy(s.id)}
                      title="삭제"
                    >
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
