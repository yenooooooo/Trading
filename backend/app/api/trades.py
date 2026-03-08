"""
거래 내역 API 엔드포인트
- 거래 내역 조회, 통계, 일별 PnL
- 사용처: 거래 내역 & 성과 분석 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter()


@router.get("")
async def list_trades():
    """거래 내역 (페이지네이션)"""
    return success_response({"trades": []})


@router.get("/stats")
async def get_trade_stats():
    """거래 통계"""
    return success_response({"message": "거래 통계 (구현 예정)"})


@router.get("/daily")
async def get_daily_pnl():
    """일별 PnL"""
    return success_response({"message": "일별 PnL (구현 예정)"})
