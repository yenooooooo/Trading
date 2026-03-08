/**
 * 상단 헤더
 * - 페이지 제목, 알림, 사용자 메뉴
 * - 사용처: app/dashboard/layout.tsx
 */

"use client";

import { Bell, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-6">
      {/* --- 좌측: 빈 공간 (추후 검색바 등 추가) --- */}
      <div />

      {/* --- 우측: 알림 + 사용자 --- */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          {/* 알림 뱃지 (알림 있을 때만 표시) */}
          <span className="absolute -top-0.5 -right-0.5 h-3 w-3 rounded-full bg-red-500 text-[8px] text-white flex items-center justify-center">
            3
          </span>
        </Button>
        <Button variant="ghost" size="icon">
          <User className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
