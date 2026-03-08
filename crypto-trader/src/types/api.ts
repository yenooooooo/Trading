/**
 * API 공통 타입 정의
 * - 모든 API 응답의 표준 포맷
 * - 사용처: hooks/, lib/api.ts 등 API 호출 전반
 */

// --- 표준 API 응답 ---
export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
}

// --- 페이지네이션 ---
export interface PaginationMeta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface PaginatedResponse<T = unknown> {
  success: boolean;
  data: T[];
  meta: PaginationMeta;
  error: string | null;
  timestamp: string;
}
