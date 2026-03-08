"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Settings,
  Key,
  Bell,
  Shield,
  Save,
  TestTube,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Eye,
  EyeOff,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";

interface SettingsData {
  exchange: {
    binance_api_key: string;
    binance_secret_key: string;
    has_api_key: boolean;
  };
  telegram: {
    bot_token: string;
    chat_id: string;
    enabled: boolean;
  };
  trading: {
    mode: string;
    cors_origins: string[];
    debug: boolean;
    backend_url: string;
  };
}

type TestStatus = "idle" | "testing" | "success" | "error";

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form state
  const [binanceApiKey, setBinanceApiKey] = useState("");
  const [binanceSecretKey, setBinanceSecretKey] = useState("");
  const [telegramBotToken, setTelegramBotToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [tradingMode, setTradingMode] = useState<"paper" | "live">("paper");

  // Visibility toggles
  const [showApiKey, setShowApiKey] = useState(false);
  const [showSecretKey, setShowSecretKey] = useState(false);
  const [showBotToken, setShowBotToken] = useState(false);

  // Test status
  const [telegramTest, setTelegramTest] = useState<TestStatus>("idle");
  const [exchangeTest, setExchangeTest] = useState<TestStatus>("idle");
  const [telegramTestMsg, setTelegramTestMsg] = useState("");
  const [exchangeTestMsg, setExchangeTestMsg] = useState("");

  // Mode change confirmation
  const [showModeConfirm, setShowModeConfirm] = useState(false);

  const fetchSettings = useCallback(async () => {
    try {
      const res = await api.get<SettingsData>("/api/settings");
      if (res.data) {
        setSettings(res.data);
        setTelegramChatId(res.data.telegram.chat_id || "");
        setTradingMode(res.data.trading.mode as "paper" | "live");
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "설정 불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const clearMessages = () => {
    setError(null);
    setSuccessMsg(null);
  };

  // ── Save handlers ──

  const saveExchangeKeys = async () => {
    if (!binanceApiKey && !binanceSecretKey) {
      setError("변경할 API 키를 입력해주세요");
      return;
    }
    clearMessages();
    setSaving(true);
    try {
      const body: Record<string, string> = {};
      if (binanceApiKey) body.binance_api_key = binanceApiKey;
      if (binanceSecretKey) body.binance_secret_key = binanceSecretKey;
      await api.put("/api/settings", body);
      setSuccessMsg("거래소 API 키가 저장되었습니다");
      setBinanceApiKey("");
      setBinanceSecretKey("");
      await fetchSettings();
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const saveTelegramSettings = async () => {
    if (!telegramBotToken && !telegramChatId) {
      setError("변경할 텔레그램 설정을 입력해주세요");
      return;
    }
    clearMessages();
    setSaving(true);
    try {
      const body: Record<string, string> = {};
      if (telegramBotToken) body.telegram_bot_token = telegramBotToken;
      if (telegramChatId) body.telegram_chat_id = telegramChatId;
      await api.put("/api/settings", body);
      setSuccessMsg("텔레그램 설정이 저장되었습니다");
      setTelegramBotToken("");
      await fetchSettings();
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleModeChange = async () => {
    const newMode = tradingMode === "paper" ? "live" : "paper";

    if (newMode === "live") {
      setShowModeConfirm(true);
      return;
    }

    await switchMode(newMode);
  };

  const switchMode = async (mode: "paper" | "live") => {
    clearMessages();
    setSaving(true);
    setShowModeConfirm(false);
    try {
      await api.put("/api/settings", { trading_mode: mode });
      setTradingMode(mode);
      setSuccessMsg(`트레이딩 모드가 ${mode === "live" ? "실전매매" : "모의매매"}로 변경되었습니다`);
      await fetchSettings();
    } catch (e) {
      setError(e instanceof Error ? e.message : "모드 변경 실패");
    } finally {
      setSaving(false);
    }
  };

  // ── Test handlers ──

  const testTelegram = async () => {
    setTelegramTest("testing");
    setTelegramTestMsg("");
    try {
      const res = await api.post<{ message: string }>("/api/settings/test-telegram");
      setTelegramTest("success");
      setTelegramTestMsg(res.data?.message ?? "테스트 성공");
    } catch (e) {
      setTelegramTest("error");
      setTelegramTestMsg(e instanceof Error ? e.message : "테스트 실패");
    }
  };

  const testExchange = async () => {
    setExchangeTest("testing");
    setExchangeTestMsg("");
    try {
      const res = await api.post<{ balance?: { total: string; available: string } }>(
        "/api/settings/test-exchange"
      );
      setExchangeTest("success");
      const bal = res.data?.balance;
      setExchangeTestMsg(
        bal ? `연결 성공! 잔고: $${parseFloat(bal.total).toFixed(2)} (가용: $${parseFloat(bal.available).toFixed(2)})` : "연결 성공"
      );
    } catch (e) {
      setExchangeTest("error");
      setExchangeTestMsg(e instanceof Error ? e.message : "연결 실패");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">설정</h1>
        <Button variant="outline" size="sm" onClick={fetchSettings}>
          <RefreshCw className="mr-1 h-4 w-4" />
          새로고침
        </Button>
      </div>

      {/* Global messages */}
      {successMsg && (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-green-500">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            {successMsg}
          </CardContent>
        </Card>
      )}
      {error && (
        <Card className="border-red-500/50 bg-red-500/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-red-500">
            <XCircle className="h-4 w-4 shrink-0" />
            {error}
          </CardContent>
        </Card>
      )}

      {/* ── 1. Trading Mode ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Shield className="h-4 w-4" />
            트레이딩 모드
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="font-medium">
                현재 모드:{" "}
                <Badge variant={tradingMode === "live" ? "destructive" : "secondary"}>
                  {tradingMode === "live" ? "실전매매" : "모의매매"}
                </Badge>
              </p>
              <p className="text-sm text-muted-foreground">
                {tradingMode === "paper"
                  ? "가상 자금으로 매매합니다. 실제 주문은 실행되지 않습니다."
                  : "실제 자금으로 매매합니다. 주문이 거래소에 실행됩니다."}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Paper</span>
              <Switch
                checked={tradingMode === "live"}
                onCheckedChange={handleModeChange}
                disabled={saving}
              />
              <span className="text-sm text-muted-foreground">Live</span>
            </div>
          </div>

          {/* Live mode confirmation */}
          {showModeConfirm && (
            <div className="rounded-lg border border-red-500/50 bg-red-500/5 p-4 space-y-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <p className="font-semibold text-red-500">실전매매 모드 전환 경고</p>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>- 실제 자금으로 거래가 실행됩니다</li>
                    <li>- 바이낸스 API 키가 올바르게 설정되어 있는지 확인하세요</li>
                    <li>- 모드 전환 후 트레이딩을 재시작해야 적용됩니다</li>
                  </ul>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => switchMode("live")}
                  disabled={saving}
                >
                  {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                  실전매매로 전환
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowModeConfirm(false)}
                >
                  취소
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 2. Exchange API Keys ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Key className="h-4 w-4" />
            거래소 API 키 (Binance Futures)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current status */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">상태:</span>
            {settings?.exchange.has_api_key ? (
              <Badge variant="outline" className="text-green-500 border-green-500/50">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                설정됨
              </Badge>
            ) : (
              <Badge variant="outline" className="text-red-500 border-red-500/50">
                <XCircle className="mr-1 h-3 w-3" />
                미설정
              </Badge>
            )}
            {settings?.exchange.has_api_key && (
              <span className="text-xs text-muted-foreground font-mono">
                ({settings.exchange.binance_api_key})
              </span>
            )}
          </div>

          <Separator />

          {/* API Key input */}
          <div className="space-y-2">
            <Label htmlFor="api-key">API Key</Label>
            <div className="relative">
              <Input
                id="api-key"
                type={showApiKey ? "text" : "password"}
                placeholder="새 API Key 입력 (변경 시에만)"
                value={binanceApiKey}
                onChange={(e) => setBinanceApiKey(e.target.value)}
                className="pr-10 font-mono text-sm"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="secret-key">Secret Key</Label>
            <div className="relative">
              <Input
                id="secret-key"
                type={showSecretKey ? "text" : "password"}
                placeholder="새 Secret Key 입력 (변경 시에만)"
                value={binanceSecretKey}
                onChange={(e) => setBinanceSecretKey(e.target.value)}
                className="pr-10 font-mono text-sm"
              />
              <button
                type="button"
                onClick={() => setShowSecretKey(!showSecretKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showSecretKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={saveExchangeKeys} disabled={saving || (!binanceApiKey && !binanceSecretKey)}>
              {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
              저장
            </Button>
            <Button
              variant="outline"
              onClick={testExchange}
              disabled={exchangeTest === "testing"}
            >
              {exchangeTest === "testing" ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <TestTube className="mr-1 h-4 w-4" />
              )}
              연결 테스트
            </Button>
          </div>

          {/* Exchange test result */}
          {exchangeTest !== "idle" && exchangeTest !== "testing" && (
            <div className={`flex items-center gap-2 text-sm rounded-lg border p-3 ${
              exchangeTest === "success"
                ? "border-green-500/50 bg-green-500/5 text-green-500"
                : "border-red-500/50 bg-red-500/5 text-red-500"
            }`}>
              {exchangeTest === "success" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0" />
              )}
              {exchangeTestMsg}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 3. Telegram Settings ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Bell className="h-4 w-4" />
            텔레그램 알림
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current status */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">상태:</span>
            {settings?.telegram.enabled ? (
              <Badge variant="outline" className="text-green-500 border-green-500/50">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                활성
              </Badge>
            ) : (
              <Badge variant="outline" className="text-red-500 border-red-500/50">
                <XCircle className="mr-1 h-3 w-3" />
                비활성
              </Badge>
            )}
          </div>

          <Separator />

          <div className="space-y-2">
            <Label htmlFor="bot-token">Bot Token</Label>
            <div className="relative">
              <Input
                id="bot-token"
                type={showBotToken ? "text" : "password"}
                placeholder="새 Bot Token 입력 (변경 시에만)"
                value={telegramBotToken}
                onChange={(e) => setTelegramBotToken(e.target.value)}
                className="pr-10 font-mono text-sm"
              />
              <button
                type="button"
                onClick={() => setShowBotToken(!showBotToken)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showBotToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="chat-id">Chat ID</Label>
            <Input
              id="chat-id"
              placeholder="텔레그램 Chat ID"
              value={telegramChatId}
              onChange={(e) => setTelegramChatId(e.target.value)}
              className="font-mono text-sm"
            />
            {settings?.telegram.chat_id && (
              <p className="text-xs text-muted-foreground">
                현재 설정: {settings.telegram.chat_id}
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Button onClick={saveTelegramSettings} disabled={saving || (!telegramBotToken && !telegramChatId)}>
              {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
              저장
            </Button>
            <Button
              variant="outline"
              onClick={testTelegram}
              disabled={telegramTest === "testing"}
            >
              {telegramTest === "testing" ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <TestTube className="mr-1 h-4 w-4" />
              )}
              테스트 메시지 전송
            </Button>
          </div>

          {/* Telegram test result */}
          {telegramTest !== "idle" && telegramTest !== "testing" && (
            <div className={`flex items-center gap-2 text-sm rounded-lg border p-3 ${
              telegramTest === "success"
                ? "border-green-500/50 bg-green-500/5 text-green-500"
                : "border-red-500/50 bg-red-500/5 text-red-500"
            }`}>
              {telegramTest === "success" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0" />
              )}
              {telegramTestMsg}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 4. System Info ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Settings className="h-4 w-4" />
            시스템 정보
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">백엔드 URL</span>
              <span className="font-mono">{settings?.trading.backend_url ?? "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">CORS Origins</span>
              <span className="font-mono text-xs">{settings?.trading.cors_origins?.join(", ") ?? "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">디버그 모드</span>
              <Badge variant={settings?.trading.debug ? "secondary" : "outline"}>
                {settings?.trading.debug ? "ON" : "OFF"}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">거래소</span>
              <span>Binance Futures (USDT-M)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">전략</span>
              <span>Funding Rate Reversal</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
