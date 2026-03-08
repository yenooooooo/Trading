"use client";

import { LineChart } from "lucide-react";

export default function TradingPage() {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4">
      <LineChart className="w-12 h-12 text-zinc-600" />
      <h1 className="text-xl font-semibold">트레이딩</h1>
      <p className="text-zinc-400 text-sm">준비 중입니다</p>
    </div>
  );
}
