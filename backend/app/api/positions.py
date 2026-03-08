"""
포지션 & 주문 API 엔드포인트
- 현재 포지션 조회, 수동 청산, 주문 생성/취소
- 사용처: 포지션 관리 페이지, 트레이딩 뷰
"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter()


@router.get("")
async def list_positions():
    """현재 포지션 목록"""
    return success_response({"positions": []})


@router.get("/{position_id}")
async def get_position(position_id: str):
    """포지션 상세"""
    return success_response({"message": f"포지션 {position_id} 상세 (구현 예정)"})


@router.post("/{position_id}/close")
async def close_position(position_id: str):
    """포지션 수동 청산"""
    return success_response({"message": f"포지션 {position_id} 청산 (구현 예정)"})
