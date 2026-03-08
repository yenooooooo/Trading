"""
포지션 & 주문 API 엔드포인트
- 현재 포지션 조회, 수동 청산
- 사용처: 포지션 관리 페이지, 트레이딩 뷰
"""

from fastapi import APIRouter

from app.schemas.common import success_response
from app.api.trading import _get_engine

router = APIRouter()


@router.get("")
async def list_positions():
    """현재 포지션 목록 (트레이딩 엔진에서 조회)"""
    engine = _get_engine()
    status = engine.get_status()
    return success_response(status.get("positions", []))


@router.get("/summary")
async def get_position_summary():
    """포지션 요약 (총 미실현 PnL 등)"""
    engine = _get_engine()
    status = engine.get_status()
    positions = status.get("positions", [])

    total_unrealized_pnl = sum(p.get("pnl_pct", 0) for p in positions)
    long_count = sum(1 for p in positions if p.get("side") == "long")
    short_count = sum(1 for p in positions if p.get("side") == "short")

    return success_response({
        "total_positions": len(positions),
        "long_count": long_count,
        "short_count": short_count,
        "total_unrealized_pnl_pct": round(total_unrealized_pnl, 2),
        "positions": positions,
    })


@router.post("/{symbol}/close")
async def close_position(symbol: str):
    """포지션 수동 청산"""
    return success_response({"message": f"포지션 {symbol} 청산 (구현 예정)"})
