"""
공통 API 응답 스키마
- 모든 API 응답은 이 포맷을 사용: { success, data, error, timestamp }
- 사용처: 모든 API 엔드포인트의 응답
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """표준 API 응답 포맷"""

    success: bool
    data: T | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginationMeta(BaseModel):
    """페이지네이션 메타 정보"""

    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션이 포함된 API 응답"""

    success: bool = True
    data: list[T] = []
    meta: PaginationMeta
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def success_response(data: Any = None) -> dict:
    """성공 응답 생성 헬퍼"""
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc),
    }


def error_response(message: str, status_code: int = 400) -> dict:
    """에러 응답 생성 헬퍼"""
    return {
        "success": False,
        "data": None,
        "error": message,
        "timestamp": datetime.now(timezone.utc),
    }
