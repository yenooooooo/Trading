"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  RefreshCw,
  AlertCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Activity,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { TIMEFRAMES, COLORS } from "@/lib/constants";

import type { IChartApi, CandlestickData, HistogramData, Time } from "lightweight-charts";

// ── 상수 ──────────────────────────────────────

const BINANCE_WS = "wss://fstream.binance.com/ws";

const SYMBOLS = [
  { value: "BTC-USDT", label: "BTC/USDT", ws: "btcusdt" },
  { value: "ETH-USDT", label: "ETH/USDT", ws: "ethusdt" },
  { value: "SOL-USDT", label: "SOL/USDT", ws: "solusdt" },
  { value: "XRP-USDT", label: "XRP/USDT", ws: "xrpusdt" },
];

// ── 타입 ──────────────────────────────────────

interface KlineData {
  timestamp: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

interface BinanceKlineMsg {
  e: string;
  k: {
    t: number;   // kline start time (ms)
    o: string;   // open
    h: string;   // high
    l: string;   // low
    c: string;   // close
    v: string;   // volume
    x: boolean;  // is closed?
    i: string;   // interval
  };
}

interface BinanceMiniTickerMsg {
  e: string;
  s: string;
  c: string;   // close (current price)
  o: string;   // open (24h)
  h: string;   // high (24h)
  l: string;   // low (24h)
  v: string;   // base volume (24h)
  q: string;   // quote volume (24h)
}

// ── 컴포넌트 ──────────────────────────────────

export default function TradingPage() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const candleSeriesRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const volumeSeriesRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [symbol, setSymbol] = useState("BTC-USDT");
  const [interval, setInterval_] = useState("1h");
  const [price, setPrice] = useState(0);
  const [change24h, setChange24h] = useState(0);
  const [high24h, setHigh24h] = useState(0);
  const [low24h, setLow24h] = useState(0);
  const [volume24h, setVolume24h] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartReady, setChartReady] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  const currentSymbol = SYMBOLS.find((s) => s.value === symbol)!;

  // ── 1. Chart 초기화 ──────────────────────────

  useEffect(() => {
    let chart: IChartApi | null = null;

    const initChart = async () => {
      if (!chartContainerRef.current) return;

      const { createChart, ColorType, CandlestickSeries, HistogramSeries } =
        await import("lightweight-charts");

      chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#94A3B8",
          fontSize: 12,
        },
        grid: {
          vertLines: { color: "rgba(148, 163, 184, 0.06)" },
          horzLines: { color: "rgba(148, 163, 184, 0.06)" },
        },
        crosshair: {
          mode: 0,
          vertLine: { color: "rgba(148, 163, 184, 0.3)", width: 1, style: 2 },
          horzLine: { color: "rgba(148, 163, 184, 0.3)", width: 1, style: 2 },
        },
        rightPriceScale: {
          borderColor: "rgba(148, 163, 184, 0.1)",
          scaleMargins: { top: 0.1, bottom: 0.25 },
        },
        timeScale: {
          borderColor: "rgba(148, 163, 184, 0.1)",
          timeVisible: true,
          secondsVisible: false,
        },
        handleScroll: { vertTouchDrag: false },
      });

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: COLORS.profit,
        downColor: COLORS.loss,
        borderUpColor: COLORS.profit,
        borderDownColor: COLORS.loss,
        wickUpColor: COLORS.profit,
        wickDownColor: COLORS.loss,
      });

      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#26a69a",
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;
      volumeSeriesRef.current = volumeSeries;
      setChartReady(true);

      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          chart?.applyOptions({ width, height });
        }
      });
      resizeObserver.observe(chartContainerRef.current);

      return () => resizeObserver.disconnect();
    };

    initChart();

    return () => {
      chart?.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      setChartReady(false);
    };
  }, []);

  // ── 2. 히스토리 로드 (REST) ──────────────────

  const loadHistory = useCallback(async () => {
    if (!chartReady) return;

    setLoading(true);
    setError(null);

    try {
      const res = await api.get<KlineData[]>(
        `/api/market/klines/${symbol}?interval=${interval}&limit=200`
      );
      const klines = res.data ?? [];

      const candleData: CandlestickData[] = klines.map((k) => ({
        time: (k.timestamp / 1000) as Time,
        open: parseFloat(k.open),
        high: parseFloat(k.high),
        low: parseFloat(k.low),
        close: parseFloat(k.close),
      }));

      const volumeData: HistogramData[] = klines.map((k) => {
        const o = parseFloat(k.open);
        const c = parseFloat(k.close);
        return {
          time: (k.timestamp / 1000) as Time,
          value: parseFloat(k.volume),
          color: c >= o ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)",
        };
      });

      candleSeriesRef.current?.setData(candleData);
      volumeSeriesRef.current?.setData(volumeData);
      chartRef.current?.timeScale().fitContent();
    } catch (e) {
      setError(e instanceof Error ? e.message : "차트 데이터 로드 실패");
    } finally {
      setLoading(false);
    }
  }, [symbol, interval, chartReady]);

  // ── 3. 바이낸스 WebSocket 연결 ──────────────

  useEffect(() => {
    if (!chartReady) return;

    // 히스토리 먼저 로드
    loadHistory();

    // WebSocket 스트림: kline + miniTicker
    const wsPair = currentSymbol.ws;
    const wsUrl = `${BINANCE_WS}/${wsPair}@kline_${interval}/${wsPair}@miniTicker`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.e === "kline") {
          const k = (msg as BinanceKlineMsg).k;
          const o = parseFloat(k.o);
          const c = parseFloat(k.c);

          // 캔들 실시간 업데이트
          candleSeriesRef.current?.update({
            time: (k.t / 1000) as Time,
            open: o,
            high: parseFloat(k.h),
            low: parseFloat(k.l),
            close: c,
          });

          // 볼륨 실시간 업데이트
          volumeSeriesRef.current?.update({
            time: (k.t / 1000) as Time,
            value: parseFloat(k.v),
            color: c >= o ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)",
          });
        }

        if (msg.e === "24hrMiniTicker") {
          const t = msg as BinanceMiniTickerMsg;
          const currentPrice = parseFloat(t.c);
          const openPrice = parseFloat(t.o);

          setPrice(currentPrice);
          setChange24h(((currentPrice - openPrice) / openPrice) * 100);
          setHigh24h(parseFloat(t.h));
          setLow24h(parseFloat(t.l));
          setVolume24h(parseFloat(t.q));
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = () => {
      ws.close();
    };

    return () => {
      ws.close();
      wsRef.current = null;
      setWsConnected(false);
    };
  }, [symbol, interval, chartReady, currentSymbol.ws, loadHistory]);

  // ── 렌더 ──────────────────────────────────

  const isUp = change24h >= 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">트레이딩</h1>
          {wsConnected ? (
            <span className="flex items-center gap-1 text-xs text-green-500">
              <Wifi className="h-3 w-3" /> 실시간
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <WifiOff className="h-3 w-3" /> 연결 중...
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={loadHistory} disabled={loading}>
          <RefreshCw className={`mr-1 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          새로고침
        </Button>
      </div>

      {/* Symbol Selector + Ticker Info */}
      <Card>
        <CardContent className="flex flex-wrap items-center gap-4 py-3">
          {/* Symbol tabs */}
          <div className="flex gap-1">
            {SYMBOLS.map((s) => (
              <Button
                key={s.value}
                variant={symbol === s.value ? "default" : "ghost"}
                size="sm"
                onClick={() => setSymbol(s.value)}
              >
                {s.label}
              </Button>
            ))}
          </div>

          <div className="h-6 w-px bg-border" />

          {/* Ticker info */}
          {price > 0 && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xl font-mono font-bold">
                  ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <Badge variant={isUp ? "default" : "destructive"} className="text-xs">
                  {isUp ? (
                    <TrendingUp className="mr-1 h-3 w-3" />
                  ) : (
                    <TrendingDown className="mr-1 h-3 w-3" />
                  )}
                  {isUp ? "+" : ""}{change24h.toFixed(2)}%
                </Badge>
              </div>
              {volume24h > 0 && (
                <span className="text-xs text-muted-foreground">
                  Vol: ${(volume24h / 1e9).toFixed(2)}B
                </span>
              )}
              {high24h > 0 && low24h > 0 && (
                <span className="text-xs text-muted-foreground">
                  H: ${high24h.toLocaleString()} / L: ${low24h.toLocaleString()}
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Card className="border-red-500/50">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-red-500">
            <AlertCircle className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      {/* Chart */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" />
              {currentSymbol.label} 캔들 차트
            </CardTitle>
            {/* Timeframe selector */}
            <div className="flex gap-1">
              {TIMEFRAMES.map((tf) => (
                <Button
                  key={tf.value}
                  variant={interval === tf.value ? "secondary" : "ghost"}
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => setInterval_(tf.value)}
                >
                  {tf.label}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div
            ref={chartContainerRef}
            className="w-full"
            style={{ height: "500px" }}
          />
        </CardContent>
      </Card>

      {/* Market Info */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">펀딩비 정보</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">다음 정산</span>
                <span className="font-mono flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  매 8시간 (00/08/16 UTC)
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">전략</span>
                <span>펀딩비 역방향 매매</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">진입 타이밍</span>
                <span>정산 1시간 전</span>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">리스크 한도</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">최대 레버리지</span>
                <span className="font-mono">5x</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">포지션 리스크</span>
                <span className="font-mono">3~5%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">일일 최대 손실</span>
                <span className="font-mono">8%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">일일 최대 거래</span>
                <span className="font-mono">3회</span>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">거래소 정보</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">거래소</span>
                <span>Binance Futures</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">마켓</span>
                <span>USDT-M 무기한</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">수수료</span>
                <span className="font-mono">0.04% (Taker)</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
