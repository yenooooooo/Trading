/**
 * 대시보드 레이아웃
 * - 사이드바 + 헤더 + 메인 콘텐츠 구조
 * - 사용처: /dashboard 하위 모든 페이지에 적용
 */

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* --- 사이드바 (고정) --- */}
      <Sidebar />

      {/* --- 메인 영역 --- */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
