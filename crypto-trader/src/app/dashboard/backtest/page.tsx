"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  FlaskConical,
  Play,
  Loader2,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  BarChart3,
  Target,
  Shield,
  DollarSign,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "";

// --- 타입 ---
interface BacktestTrade {
  id: number;
  side: string;
  entry_time: number;
  exit_time: number;
  entry_price: number;
  exit_price: number;
  size_usdt: number;
  pnl_net: number;
  fee_paid: number;
  return_pct: number;
  holding_bars: number;
  reason: string;
}

interface BacktestResult {
  symbol: string;
  timeframe: string;
  period: string;
  initial_balance: number;
  final_balance: number;
  total_return: number;
  total_return_after_fees: number;
  total_fees_paid: number;
  total_funding_paid: number;
  total_slippage_cost: number;
  fee_to_profit_ratio: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  max_drawdown_usd: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  avg_holding_bars: number;
  equity_curve: { timestamp: number; equity: number; balance: number }[];
  trades: BacktestTrade[];
  warnings: string[];
}

interface StrategyInfo {
  name: string;
  description: string;
  default_params: Record<string, number>;
}

// --- 심볼 옵션 ---
const SYMBOLS = [
  { label: "BTC/USDT", value: "BTC-USDT" },
  { label: "ETH/USDT", value: "ETH-USDT" },
  { label: "SOL/USDT", value: "SOL-USDT" },
  { label: "XRP/USDT", value: "XRP-USDT" },
];

const TIMEFRAMES = [
  { label: "5분", value: "5m" },
  { label: "15분", value: "15m" },
  { label: "1시간", value: "1h" },
  { label: "4시간", value: "4h" },
  { label: "1일", value: "1d" },
];

const CANDLE_OPTIONS = [
  { label: "200개", value: 200 },
  { label: "500개", value: 500 },
  { label: "1000개", value: 1000 },
  { label: "1500개", value: 1500 },
];

// --- 유틸 ---
function formatTime(ts: number) {
  return new Date(ts).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pnlColor(v: number) {
  return v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-zinc-400";
}

function pnlBg(v: number) {
  return v > 0
    ? "bg-emerald-500/10 border-emerald-500/20"
    : v < 0
      ? "bg-red-500/10 border-red-500/20"
      : "bg-zinc-800 border-zinc-700";
}

// --- 컴포넌트 ---
export default function BacktestPage() {
  // 전략 목록
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);

  // 파라미터
  const [strategy, setStrategy] = useState("funding_rate");
  const [symbol, setSymbol] = useState("BTC-USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [balance, setBalance] = useState(200);
  const [leverage, setLeverage] = useState(3);
  const [candleLimit, setCandleLimit] = useState(500);

  // 상태
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState("");

  // 차트
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);

  // 전략 목록 로드
  useEffect(() => {
    fetch(`${API}/api/backtest/strategies`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.data) setStrategies(d.data);
      })
      .catch(() => {});
  }, []);

  // 에쿼티 차트
  useEffect(() => {
    if (!result || !chartRef.current || result.equity_curve.length === 0) return;

    let cancelled = false;

    (async () => {
      const lc = await import("lightweight-charts");

      if (cancelled) return;

      // 기존 차트 제거
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }

      const chart = lc.createChart(chartRef.current!, {
        width: chartRef.current!.clientWidth,
        height: 300,
        layout: {
          background: { color: "#18181b" },
          textColor: "#a1a1aa",
        },
        grid: {
          vertLines: { color: "#27272a" },
          horzLines: { color: "#27272a" },
        },
        rightPriceScale: { borderColor: "#3f3f46" },
        timeScale: {
          borderColor: "#3f3f46",
          timeVisible: true,
        },
      });

      chartInstanceRef.current = chart;

      const series = chart.addSeries(lc.AreaSeries, {
        lineColor: "#10b981",
        topColor: "rgba(16, 185, 129, 0.3)",
        bottomColor: "rgba(16, 185, 129, 0.01)",
        lineWidth: 2,
      });

      const data = result.equity_curve.map((p) => ({
        time: (p.timestamp / 1000) as any,
        value: p.equity,
      }));

      series.setData(data);
      chart.timeScale().fitContent();

      // 리사이즈
      const ro = new ResizeObserver(() => {
        if (chartRef.current) {
          chart.applyOptions({ width: chartRef.current.clientWidth });
        }
      });
      ro.observe(chartRef.current!);

      return () => ro.disconnect();
    })();

    return () => {
      cancelled = true;
    };
  }, [result]);

  // 백테스트 실행
  const runBacktest = useCallback(async () => {
    setRunning(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch(`${API}/api/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy,
          symbol,
          timeframe,
          initial_balance: balance,
          leverage,
          candle_limit: candleLimit,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        setError(data.detail || data.error || "백테스트 실패");
        return;
      }

      setResult(data.data);
    } catch (e: any) {
      setError(e.message || "서버 연결 실패");
    } finally {
      setRunning(false);
    }
  }, [strategy, symbol, timeframe, balance, leverage, candleLimit]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <FlaskConical className="w-6 h-6 text-violet-400" />
        <h1 className="text-xl font-bold">백테스트</h1>
      </div>

      {/* 파라미터 입력 */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-zinc-300 mb-4">파라미터 설정</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {/* 전략 */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">전략</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {strategies.length > 0
                ? strategies.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.description || s.name}
                    </option>
                  ))
                : <option value="funding_rate">펀딩비 수확</option>
              }
            </select>
          </div>

          {/* 심볼 */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">심볼</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {SYMBOLS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* 타임프레임 */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">타임프레임</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {TIMEFRAMES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* 초기 잔고 */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">초기 잔고 ($)</label>
            <input
              type="number"
              value={balance}
              onChange={(e) => setBalance(Number(e.target.value))}
              min={10}
              max={10000}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>

          {/* 레버리지 */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">레버리지</label>
            <select
              value={leverage}
              onChange={(e) => setLeverage(Number(e.target.value))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {[1, 2, 3, 5, 10, 15, 20].map((l) => (
                <option key={l} value={l}>{l}x</option>
              ))}
            </select>
          </div>

          {/* 캔들 수 */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">캔들 수</label>
            <select
              value={candleLimit}
              onChange={(e) => setCandleLimit(Number(e.target.value))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {CANDLE_OPTIONS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 실행 버튼 */}
        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={runBacktest}
            disabled={running}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition"
          >
            {running ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {running ? "실행 중..." : "백테스트 실행"}
          </button>
          {error && (
            <span className="text-red-400 text-sm">{error}</span>
          )}
        </div>
      </div>

      {/* 결과 */}
      {result && (
        <>
          {/* 경고 */}
          {result.warnings.length > 0 && (
            <div className="space-y-2">
              {result.warnings.map((w, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-2.5 text-amber-400 text-sm"
                >
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  {w}
                </div>
              ))}
            </div>
          )}

          {/* 요약 카드 */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <MetricCard
              icon={<DollarSign className="w-4 h-4" />}
              label="최종 잔고"
              value={`$${result.final_balance.toFixed(2)}`}
              color={pnlColor(result.final_balance - result.initial_balance)}
            />
            <MetricCard
              icon={<TrendingUp className="w-4 h-4" />}
              label="순수익률"
              value={`${result.total_return_after_fees >= 0 ? "+" : ""}${result.total_return_after_fees.toFixed(2)}%`}
              color={pnlColor(result.total_return_after_fees)}
            />
            <MetricCard
              icon={<Target className="w-4 h-4" />}
              label="승률"
              value={`${result.win_rate.toFixed(1)}%`}
              sub={`${result.winning_trades}W / ${result.losing_trades}L`}
            />
            <MetricCard
              icon={<Shield className="w-4 h-4" />}
              label="MDD"
              value={`-${result.max_drawdown.toFixed(1)}%`}
              sub={`$${result.max_drawdown_usd.toFixed(2)}`}
              color="text-red-400"
            />
            <MetricCard
              icon={<BarChart3 className="w-4 h-4" />}
              label="샤프 비율"
              value={result.sharpe_ratio.toFixed(2)}
              color={result.sharpe_ratio >= 1 ? "text-emerald-400" : result.sharpe_ratio >= 0.5 ? "text-yellow-400" : "text-red-400"}
            />
            <MetricCard
              icon={<BarChart3 className="w-4 h-4" />}
              label="수익팩터"
              value={result.profit_factor === Infinity ? "∞" : result.profit_factor.toFixed(2)}
              color={result.profit_factor >= 1.5 ? "text-emerald-400" : result.profit_factor >= 1 ? "text-yellow-400" : "text-red-400"}
            />
          </div>

          {/* 상세 지표 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* 수익/비용 */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3">수익 & 비용</h3>
              <div className="space-y-2 text-sm">
                <DetailRow label="총수익률 (수수료 전)" value={`${result.total_return.toFixed(2)}%`} color={pnlColor(result.total_return)} />
                <DetailRow label="순수익률 (수수료 후)" value={`${result.total_return_after_fees.toFixed(2)}%`} color={pnlColor(result.total_return_after_fees)} />
                <DetailRow label="총 수수료" value={`$${result.total_fees_paid.toFixed(2)}`} color="text-red-400" />
                <DetailRow label="총 펀딩비" value={`$${result.total_funding_paid.toFixed(2)}`} />
                <DetailRow label="총 슬리피지" value={`$${result.total_slippage_cost.toFixed(2)}`} />
                <DetailRow label="수수료/수익 비율" value={`${result.fee_to_profit_ratio.toFixed(1)}%`} color={result.fee_to_profit_ratio > 50 ? "text-red-400" : "text-zinc-300"} />
              </div>
            </div>

            {/* 거래 통계 */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3">거래 통계</h3>
              <div className="space-y-2 text-sm">
                <DetailRow label="총 거래 수" value={`${result.total_trades}회`} />
                <DetailRow label="승/패" value={`${result.winning_trades}승 ${result.losing_trades}패`} />
                <DetailRow label="평균 수익 (승)" value={`$${result.avg_win.toFixed(2)}`} color="text-emerald-400" />
                <DetailRow label="평균 손실 (패)" value={`$${result.avg_loss.toFixed(2)}`} color="text-red-400" />
                <DetailRow label="평균 보유 기간" value={`${result.avg_holding_bars.toFixed(1)} 캔들`} />
                <DetailRow label="소르티노 비율" value={result.sortino_ratio.toFixed(2)} />
                <DetailRow label="기간" value={result.period} />
              </div>
            </div>
          </div>

          {/* 에쿼티 커브 */}
          {result.equity_curve.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3">자산 곡선</h3>
              <div ref={chartRef} className="w-full" />
            </div>
          )}

          {/* 거래 내역 */}
          {result.trades.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3">
                거래 내역 ({result.trades.length}건)
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-zinc-500 text-xs border-b border-zinc-800">
                      <th className="text-left py-2 px-2">#</th>
                      <th className="text-left py-2 px-2">방향</th>
                      <th className="text-left py-2 px-2">진입</th>
                      <th className="text-left py-2 px-2">청산</th>
                      <th className="text-right py-2 px-2">진입가</th>
                      <th className="text-right py-2 px-2">청산가</th>
                      <th className="text-right py-2 px-2">크기</th>
                      <th className="text-right py-2 px-2">손익</th>
                      <th className="text-right py-2 px-2">수익률</th>
                      <th className="text-right py-2 px-2">수수료</th>
                      <th className="text-left py-2 px-2">사유</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t) => (
                      <tr key={t.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                        <td className="py-2 px-2 text-zinc-500">{t.id}</td>
                        <td className="py-2 px-2">
                          <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                            t.side === "long"
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-red-500/10 text-red-400"
                          }`}>
                            {t.side === "long" ? "롱" : "숏"}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-zinc-400">{formatTime(t.entry_time)}</td>
                        <td className="py-2 px-2 text-zinc-400">{formatTime(t.exit_time)}</td>
                        <td className="py-2 px-2 text-right">{t.entry_price.toFixed(2)}</td>
                        <td className="py-2 px-2 text-right">{t.exit_price.toFixed(2)}</td>
                        <td className="py-2 px-2 text-right text-zinc-400">${t.size_usdt.toFixed(0)}</td>
                        <td className={`py-2 px-2 text-right font-medium ${pnlColor(t.pnl_net)}`}>
                          {t.pnl_net >= 0 ? "+" : ""}{t.pnl_net.toFixed(2)}
                        </td>
                        <td className={`py-2 px-2 text-right ${pnlColor(t.return_pct)}`}>
                          {t.return_pct >= 0 ? "+" : ""}{t.return_pct.toFixed(1)}%
                        </td>
                        <td className="py-2 px-2 text-right text-zinc-500">${t.fee_paid.toFixed(3)}</td>
                        <td className="py-2 px-2 text-zinc-500 text-xs max-w-[150px] truncate">{t.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* 빈 상태 */}
      {!result && !running && (
        <div className="flex flex-col items-center justify-center h-40 text-zinc-500 text-sm">
          파라미터를 설정하고 백테스트를 실행하세요
        </div>
      )}
    </div>
  );
}

// --- 서브 컴포넌트 ---

function MetricCard({
  icon,
  label,
  value,
  sub,
  color = "text-zinc-100",
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-3">
      <div className="flex items-center gap-1.5 text-zinc-500 text-xs mb-1">
        {icon}
        {label}
      </div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-zinc-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function DetailRow({
  label,
  value,
  color = "text-zinc-300",
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-zinc-500">{label}</span>
      <span className={color}>{value}</span>
    </div>
  );
}
