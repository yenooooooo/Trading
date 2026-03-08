"""
리스크 API 엔드포인트
- 현재 리스크 상태, 메트릭 조회, 설정 변경
- 사용처: 리스크 대시보드 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter()


@router.get("/status")
async def get_risk_status():
    """현재 리스크 상태"""
    return success_response({"message": "리스크 상태 (구현 예정)"})


@router.get("/metrics")
async def get_risk_metrics():
    """리스크 메트릭"""
    return success_response({"message": "리스크 메트릭 (구현 예정)"})


@router.put("/settings")
async def update_risk_settings():
    """리스크 설정 변경"""
    return success_response({"message": "리스크 설정 변경 (구현 예정)"})
