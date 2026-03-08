/**
 * API 클라이언트
 * - 백엔드 REST API 호출을 위한 래퍼 함수
 * - JWT 토큰 자동 첨부
 * - 사용처: hooks/ 디렉토리의 React Query 훅들
 */

import type { ApiResponse } from "@/types/api";

// --- API 기본 URL ---
// Vercel rewrites를 통해 /api/* → EC2로 프록시되므로 빈 문자열 사용
const API_BASE_URL = "";

// --- 토큰 관리 ---
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

// --- 공통 fetch 래퍼 ---
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // JWT 토큰 자동 첨부
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);
    const data: ApiResponse<T> = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `API 오류: ${response.status}`);
    }

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("알 수 없는 API 오류가 발생했습니다");
  }
}

// --- HTTP 메서드별 헬퍼 ---
export const api = {
  get: <T>(endpoint: string) => fetchApi<T>(endpoint),

  post: <T>(endpoint: string, body?: unknown) =>
    fetchApi<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown) =>
    fetchApi<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string) =>
    fetchApi<T>(endpoint, { method: "DELETE" }),
};
