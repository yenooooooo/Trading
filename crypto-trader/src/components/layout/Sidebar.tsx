/**
 * 사이드바 내비게이션
 * - 대시보드 좌측 메뉴
 * - 사용처: app/dashboard/layout.tsx
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  LineChart,
  Bot,
  FlaskConical,
  Wallet,
  History,
  ShieldAlert,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

// --- 메뉴 항목 정의 ---
const menuItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "대시보드" },
  { href: "/dashboard/trading", icon: LineChart, label: "트레이딩" },
  { href: "/dashboard/strategies", icon: Bot, label: "전략 관리" },
  { href: "/dashboard/backtest", icon: FlaskConical, label: "백테스트" },
  { href: "/dashboard/positions", icon: Wallet, label: "포지션" },
  { href: "/dashboard/history", icon: History, label: "거래 내역" },
  { href: "/dashboard/risk", icon: ShieldAlert, label: "리스크" },
  { href: "/dashboard/settings", icon: Settings, label: "설정" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 flex-col border-r border-border bg-card">
      {/* --- 로고 영역 --- */}
      <div className="flex h-14 items-center border-b border-border px-4">
        <Link href="/dashboard" className="flex items-center gap-2">
          <Bot className="h-6 w-6 text-primary" />
          <span className="text-lg font-bold">CryptoTrader</span>
        </Link>
      </div>

      {/* --- 메뉴 목록 --- */}
      <nav className="flex-1 space-y-1 p-3">
        {menuItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* --- 하단 상태 표시 --- */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-green-500" />
          시스템 정상
        </div>
      </div>
    </aside>
  );
}
