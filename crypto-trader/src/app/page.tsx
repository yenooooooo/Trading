/**
 * 랜딩 페이지 (미로그인 시)
 * - 로그인 후 /dashboard로 리다이렉트
 * - 사용처: / (루트 경로)
 */

import Link from "next/link";
import { Bot, Shield, BarChart3, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4">
      {/* --- 히어로 섹션 --- */}
      <div className="text-center space-y-6 max-w-2xl">
        <div className="flex justify-center">
          <Bot className="h-16 w-16 text-primary" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight">
          CryptoTrader
        </h1>
        <p className="text-lg text-muted-foreground">
          암호화폐 선물 자동매매 시스템
        </p>

        {/* --- 핵심 기능 카드 --- */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
          <FeatureCard
            icon={Zap}
            title="자동매매"
            description="10+ 내장 전략으로 24/7 자동 매매"
          />
          <FeatureCard
            icon={Shield}
            title="리스크 관리"
            description="다중 리스크 체크로 자산 보호"
          />
          <FeatureCard
            icon={BarChart3}
            title="백테스트"
            description="과거 데이터로 전략 검증"
          />
        </div>

        {/* --- CTA 버튼 --- */}
        <div className="flex justify-center gap-4 mt-8">
          <Link href="/dashboard">
            <Button size="lg">대시보드 시작</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-border p-4 text-left space-y-2">
      <Icon className="h-8 w-8 text-primary" />
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
