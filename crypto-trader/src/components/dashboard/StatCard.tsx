/**
 * 통계 카드 컴포넌트
 * - 총 자산, 일일 PnL, 미실현 PnL 등 핵심 지표 표시
 * - 사용처: dashboard/page.tsx (메인 대시보드 상단)
 */

"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { COLORS } from "@/lib/constants";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string;
  change?: string; // 변동률 (예: "+2.4%")
  changeType?: "profit" | "loss" | "neutral";
  icon: LucideIcon;
}

export function StatCard({
  title,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold font-mono">{value}</p>
          {change && (
            <p
              className={cn("text-xs font-mono", {
                "text-green-500": changeType === "profit",
                "text-red-500": changeType === "loss",
                "text-muted-foreground": changeType === "neutral",
              })}
            >
              {changeType === "profit" && "▲ "}
              {changeType === "loss" && "▼ "}
              {change}
            </p>
          )}
        </div>
        <div className="rounded-md bg-primary/10 p-2">
          <Icon className="h-5 w-5 text-primary" />
        </div>
      </CardContent>
    </Card>
  );
}
