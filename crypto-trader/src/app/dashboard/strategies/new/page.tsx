"use client";

/**
 * 새 전략 생성 페이지
 * - 3개 전략 선택, 파라미터 입력 (React Hook Form + Zod)
 * - 시드 입력 → 권장 설정 자동 계산
 * - 사용처: /dashboard/strategies/new
 */

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ArrowLeft, TrendingDown, Zap, ArrowUpRight, Info } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { MAX_LEVERAGE } from "@/lib/constants";
import type { StrategyType, StrategyCreateRequest } from "@/types/strategy";
import {
  STRATEGY_META,
  STRATEGY_TYPES,
  getSeedRecommendation,
  estimateFees,
} from "@/lib/strategy-meta";

// --- 심볼 & 타임프레임 ---
const SYMBOLS = [
  "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT",
  "DOGE-USDT", "ADA-USDT", "AVAX-USDT", "LINK-USDT",
];

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"];

// --- Zod 스키마 ---
const formSchema = z.object({
  name: z.string().min(1, "전략 이름을 입력하세요"),
  strategy_type: z.string().min(1, "전략을 선택하세요"),
  symbol: z.string().min(1),
  interval: z.string().min(1),
  leverage: z.number().min(1).max(MAX_LEVERAGE, `최대 ${MAX_LEVERAGE}x`),
  max_position_pct: z.number().min(0.01).max(1),
});

type FormData = z.infer<typeof formSchema>;

// 전략 아이콘
const ICONS: Record<StrategyType, React.ReactNode> = {
  funding_rate: <TrendingDown className="w-6 h-6" />,
  liquidation_bounce: <Zap className="w-6 h-6" />,
  volatility_breakout: <ArrowUpRight className="w-6 h-6" />,
};

export default function NewStrategyPage() {
  const router = useRouter();
  const [selectedType, setSelectedType] = useState<StrategyType | null>(null);
  const [params, setParams] = useState<Record<string, number>>({});
  const [seedUsd, setSeedUsd] = useState<number>(200);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: "",
      strategy_type: "",
      symbol: "BTC-USDT",
      interval: "1h",
      leverage: 3,
      max_position_pct: 0.1,
    },
  });

  const leverage = watch("leverage");

  // 시드 기반 권장 설정
  const recommendation = useMemo(
    () => getSeedRecommendation(seedUsd),
    [seedUsd]
  );

  // 수수료 추정
  const feeEstimate = useMemo(() => {
    const posSize = seedUsd * (leverage || 3) * 0.1;
    return estimateFees(posSize, leverage || 3);
  }, [seedUsd, leverage]);

  // 전략 선택
  const selectStrategy = (type: StrategyType) => {
    const meta = STRATEGY_META[type];
    setSelectedType(type);
    setValue("strategy_type", type);
    setValue("name", meta.name);
    setValue("interval", meta.recommendedTimeframes[0] ?? "1h");
    setParams({ ...meta.defaultParams });
  };

  // 권장 설정 적용
  const applyRecommendation = () => {
    setValue("leverage", recommendation.leverage);
    setValue("max_position_pct", recommendation.risk_percent);
  };

  // 제출
  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      const body: StrategyCreateRequest = { ...data, params };
      await api.post("/api/strategies", body);
      router.push("/dashboard/strategies");
    } catch (e) {
      alert(e instanceof Error ? e.message : "전략 생성 실패");
    } finally {
      setSubmitting(false);
    }
  };

  const meta = selectedType ? STRATEGY_META[selectedType] : null;

  return (
    <div className="max-w-2xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Link href="/dashboard/strategies">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">새 전략 만들기</h1>
      </div>

      {/* 1단계: 전략 선택 */}
      <div className="space-y-3">
        <Label className="text-base font-semibold">전략 유형 선택</Label>
        <div className="grid gap-3">
          {STRATEGY_TYPES.map((type) => {
            const m = STRATEGY_META[type];
            const isSelected = selectedType === type;
            return (
              <button
                key={type}
                onClick={() => selectStrategy(type)}
                className={`text-left p-5 rounded-lg border transition-colors ${
                  isSelected
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className={m.color}>{ICONS[type]}</span>
                  <div className="flex-1">
                    <div className="font-semibold">{m.name}</div>
                    <p className="text-sm text-zinc-400 mt-1">{m.description}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mt-3 text-xs">
                  <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    시드 {m.seedRange}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    {m.frequency}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-zinc-800/50 text-zinc-400">
                    {m.bestCondition}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2단계: 설정 (전략 선택 후 표시) */}
      {selectedType && meta && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* 시드 금액 입력 */}
          <div className="border border-zinc-800 rounded-lg p-5 space-y-4">
            <Label className="text-base font-semibold">시드 금액</Label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="seed">투자 시드 ($)</Label>
                <Input
                  id="seed"
                  type="number"
                  min={10}
                  max={10000}
                  value={seedUsd}
                  onChange={(e) => setSeedUsd(Number(e.target.value) || 0)}
                  className="text-lg"
                />
              </div>
              <div className="flex items-end">
                <Button type="button" variant="outline" onClick={applyRecommendation}>
                  권장 설정 적용
                </Button>
              </div>
            </div>

            {/* 권장 설정 표시 */}
            <div className="bg-zinc-900/50 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-blue-400">
                <Info className="w-4 h-4" />
                ${seedUsd.toFixed(2)} 기준 권장 설정
              </div>
              <div className="grid grid-cols-2 gap-y-1.5 text-sm">
                <span className="text-zinc-400">권장 레버리지</span>
                <span>{recommendation.leverage}x</span>
                <span className="text-zinc-400">리스크 비율</span>
                <span>{(recommendation.risk_percent * 100).toFixed(0)}%</span>
                <span className="text-zinc-400">최대 동시 포지션</span>
                <span>{recommendation.max_positions}개</span>
                <span className="text-zinc-400">일일 최대 거래</span>
                <span>{recommendation.max_daily_trades}회</span>
                <span className="text-zinc-400">구간 설명</span>
                <span className="text-zinc-300">{recommendation.description}</span>
              </div>
            </div>

            {/* 예상 수수료 */}
            <div className="bg-zinc-900/50 rounded-lg p-4 space-y-2">
              <div className="text-sm font-medium text-zinc-300">예상 수수료 (포지션당)</div>
              <div className="grid grid-cols-2 gap-y-1.5 text-sm">
                <span className="text-zinc-400">왕복 수수료</span>
                <span>{feeEstimate.round_trip_fee_pct}% (${feeEstimate.round_trip_fee_usd.toFixed(2)})</span>
                <span className="text-zinc-400">최소 수익률</span>
                <span className="text-yellow-400">{feeEstimate.min_profitable_move}% 이상 필요</span>
              </div>
            </div>
          </div>

          {/* 기본 설정 */}
          <div className="border border-zinc-800 rounded-lg p-5 space-y-4">
            <Label className="text-base font-semibold">기본 설정</Label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">전략 이름</Label>
                <Input
                  id="name"
                  {...register("name")}
                  placeholder="전략 이름"
                />
                {errors.name && (
                  <p className="text-xs text-red-400 mt-1">{errors.name.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="symbol">심볼</Label>
                <select
                  id="symbol"
                  {...register("symbol")}
                  className="w-full h-10 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm"
                >
                  {SYMBOLS.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="interval">타임프레임</Label>
                <select
                  id="interval"
                  {...register("interval")}
                  className="w-full h-10 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm"
                >
                  {INTERVALS.map((i) => {
                    const isRecommended = meta.recommendedTimeframes.includes(i);
                    return (
                      <option key={i} value={i}>
                        {i}{isRecommended ? " (권장)" : ""}
                      </option>
                    );
                  })}
                </select>
              </div>
              <div>
                <Label htmlFor="leverage">
                  레버리지 (최대 {MAX_LEVERAGE}x)
                </Label>
                <Input
                  id="leverage"
                  type="number"
                  min={1}
                  max={MAX_LEVERAGE}
                  {...register("leverage", { valueAsNumber: true })}
                />
                {errors.leverage && (
                  <p className="text-xs text-red-400 mt-1">{errors.leverage.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="max_position_pct">포지션 비율 (%)</Label>
                <Input
                  id="max_position_pct"
                  type="number"
                  min={1}
                  max={100}
                  step={1}
                  value={watch("max_position_pct") * 100}
                  onChange={(e) =>
                    setValue("max_position_pct", Number(e.target.value) / 100)
                  }
                />
              </div>
            </div>
          </div>

          {/* 전략 파라미터 */}
          <div className="border border-zinc-800 rounded-lg p-5 space-y-4">
            <Label className="text-base font-semibold">전략 파라미터</Label>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(params).map(([key, val]) => (
                <div key={key}>
                  <Label htmlFor={key} className="text-sm">
                    {meta.paramLabels[key] ?? key}
                  </Label>
                  <Input
                    id={key}
                    type="number"
                    step="any"
                    value={val}
                    onChange={(e) =>
                      setParams({ ...params, [key]: Number(e.target.value) })
                    }
                  />
                  {meta.paramDescriptions[key] && (
                    <p className="text-xs text-zinc-500 mt-1">
                      {meta.paramDescriptions[key]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 생성 버튼 */}
          <Button
            type="submit"
            disabled={submitting}
            className="w-full"
            size="lg"
          >
            {submitting ? "생성 중..." : "전략 생성"}
          </Button>
        </form>
      )}
    </div>
  );
}
