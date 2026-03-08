"use client";

import { History } from "lucide-react";

export default function HistoryPage() {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4">
      <History className="w-12 h-12 text-zinc-600" />
      <h1 className="text-xl font-semibold">거래 내역</h1>
      <p className="text-zinc-400 text-sm">준비 중입니다</p>
    </div>
  );
}
