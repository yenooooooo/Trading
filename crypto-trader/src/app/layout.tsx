/**
 * 루트 레이아웃
 * - 전역 폰트, 테마, Provider 설정
 * - 사용처: 모든 페이지의 최상위 레이아웃
 */

import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

// --- 폰트 설정 ---
// 텍스트: Inter, 숫자/코드: JetBrains Mono (트레이딩 표준)
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CryptoTrader — 암호화폐 선물 자동매매",
  description: "암호화폐 선물 자동매매 시스템 대시보드",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
