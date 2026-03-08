"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Bell,
  BellRing,
  Send,
  MessageSquare,
  ShieldAlert,
  TrendingDown,
  AlertTriangle,
  FileText,
  ToggleLeft,
  ToggleRight,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

// --- 타입 ---
interface AlertRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  category: string;
}

interface AlertHistory {
  timestamp: string;
  type: string;
  title: string;
  message: string;
  sentVia: string;
}

interface AlertStatus {
  activeRules: number;
  totalRules: number;
  todaySent: number;
  telegramConnected: boolean;
  telegramBotTokenMasked: string;
  telegramChatId: string;
}

// 카테고리 아이콘 매핑
const CATEGORY_ICON: Record<string, React.ReactNode> = {
  trading: <TrendingDown className="h-4 w-4 text-blue-400" />,
  risk: <ShieldAlert className="h-4 w-4 text-amber-400" />,
  system: <AlertTriangle className="h-4 w-4 text-red-400" />,
  report: <FileText className="h-4 w-4 text-green-400" />,
};

const CATEGORY_LABEL: Record<string, string> = {
  trading: "매매",
  risk: "리스크",
  system: "시스템",
  report: "리포트",
};

export default function AlertsPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [status, setStatus] = useState<AlertStatus | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [rulesRes, historyRes, statusRes] = await Promise.allSettled([
        api.get<AlertRule[]>("/api/alerts/rules"),
        api.get<AlertHistory[]>("/api/alerts/history"),
        api.get<AlertStatus>("/api/alerts/status"),
      ]);
      if (rulesRes.status === "fulfilled") setRules(rulesRes.value.data ?? []);
      if (historyRes.status === "fulfilled") setHistory(historyRes.value.data ?? []);
      if (statusRes.status === "fulfilled") setStatus(statusRes.value.data ?? null);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 15000);
    return () => clearInterval(id);
  }, [fetchData]);

  // 규칙 토글
  const toggleRule = async (ruleId: string, enabled: boolean) => {
    setToggling(ruleId);
    try {
      await api.put(`/api/alerts/rules/${ruleId}`, { enabled });
      setRules((prev) =>
        prev.map((r) => (r.id === ruleId ? { ...r, enabled } : r))
      );
    } catch {}
    setToggling(null);
  };

  // 테스트 메시지
  const sendTestMessage = async () => {
    setTestSending(true);
    setTestResult(null);
    try {
      const res = await api.post<{ success: boolean }>("/api/settings/test-telegram");
      setTestResult({ ok: true, msg: "테스트 메시지 전송 완료" });
    } catch (e: any) {
      setTestResult({ ok: false, msg: e.message || "전송 실패" });
    }
    setTestSending(false);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Bell className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-bold">알림</h1>
      </div>

      {/* 상단 카드 3개 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <BellRing className="h-3.5 w-3.5" /> 활성 규칙
            </div>
            <p className="text-2xl font-bold font-mono">
              {status?.activeRules ?? 0}
              <span className="text-sm text-muted-foreground font-normal">
                {" "}/ {status?.totalRules ?? 0}
              </span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Send className="h-3.5 w-3.5" /> 오늘 발송
            </div>
            <p className="text-2xl font-bold font-mono">
              {status?.todaySent ?? 0}
              <span className="text-sm text-muted-foreground font-normal"> 건</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <MessageSquare className="h-3.5 w-3.5" /> 텔레그램
            </div>
            <div className="flex items-center gap-2">
              {status?.telegramConnected ? (
                <Badge variant="default" className="bg-green-600">연결됨</Badge>
              ) : (
                <Badge variant="secondary">미연결</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 알림 규칙 */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">알림 규칙</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {CATEGORY_ICON[rule.category] ?? <Bell className="h-4 w-4" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{rule.name}</span>
                        <Badge variant="outline" className="text-[10px] px-1.5">
                          {CATEGORY_LABEL[rule.category] ?? rule.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {rule.description}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleRule(rule.id, !rule.enabled)}
                    disabled={toggling === rule.id}
                    className="shrink-0 ml-3"
                  >
                    {toggling === rule.id ? (
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    ) : rule.enabled ? (
                      <ToggleRight className="h-7 w-7 text-green-500" />
                    ) : (
                      <ToggleLeft className="h-7 w-7 text-muted-foreground" />
                    )}
                  </button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* 알림 히스토리 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">알림 히스토리</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-muted-foreground text-sm">
                  <Bell className="h-8 w-8 mb-2 opacity-30" />
                  아직 발송된 알림이 없습니다
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map((h, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-lg border p-3 text-sm"
                    >
                      <div className="mt-0.5">
                        {CATEGORY_ICON[h.type] ?? <Bell className="h-4 w-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{h.title}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(h.timestamp).toLocaleString("ko-KR")}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {h.message}
                        </p>
                      </div>
                      <Badge variant="outline" className="text-[10px] shrink-0">
                        {h.sentVia}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 텔레그램 설정 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <MessageSquare className="h-4 w-4" /> 텔레그램 연동
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground mb-1">봇 토큰</p>
              <p className="font-mono text-sm">
                {status?.telegramBotTokenMasked ?? "미설정"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Chat ID</p>
              <p className="font-mono text-sm">
                {status?.telegramChatId ?? "미설정"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">상태</p>
              {status?.telegramConnected ? (
                <div className="flex items-center gap-1.5 text-green-500 text-sm">
                  <CheckCircle2 className="h-4 w-4" /> 연결됨
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-muted-foreground text-sm">
                  <XCircle className="h-4 w-4" /> 미연결
                  <span className="text-xs">— 설정 페이지에서 설정</span>
                </div>
              )}
            </div>

            <Button
              size="sm"
              variant="outline"
              className="w-full"
              onClick={sendTestMessage}
              disabled={testSending || !status?.telegramConnected}
            >
              {testSending ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-1 h-4 w-4" />
              )}
              테스트 메시지 발송
            </Button>

            {testResult && (
              <p className={`text-xs ${testResult.ok ? "text-green-500" : "text-red-500"}`}>
                {testResult.msg}
              </p>
            )}

            <p className="text-[11px] text-muted-foreground">
              텔레그램 봇 토큰과 Chat ID는{" "}
              <a href="/dashboard/settings" className="text-primary hover:underline">
                설정 페이지
              </a>
              에서 변경할 수 있습니다.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
