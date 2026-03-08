"""
거래 내역 API 엔드포인트
- 거래 내역 조회, 통계, 일별 PnL
- 사용처: 거래 내역 & 성과 분석 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response
from app.api.trading import _get_engine

router = APIRouter()


@router.get("")
async def list_trades():
    """거래 내역 (트레이딩 엔진에서 조회)"""
    engine = _get_engine()
    trades = engine._engine._recent_trades if engine._engine else []
    return success_response(trades)


@router.get("/stats")
async def get_trade_stats():
    """거래 통계"""
    engine = _get_engine()
    te = engine._engine

    today_trades = te._today_trades if te else []
    recent_trades = te._recent_trades if te else []

    wins = sum(1 for t in recent_trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in recent_trades if t.get("pnl", 0) <= 0)
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    return success_response({
        "today_pnl": round(te._today_pnl, 4) if te else 0,
        "week_pnl": round(te._week_pnl, 4) if te else 0,
        "today_trade_count": len(today_trades),
        "total_recent_trades": len(recent_trades),
        "win_count": wins,
        "loss_count": losses,
        "win_rate": round(win_rate, 1),
    })


@router.get("/daily")
async def get_daily_pnl():
    """일별 PnL"""
    engine = _get_engine()
    return success_response({
        "today_pnl": round(engine._engine._today_pnl, 4) if engine._engine else 0,
        "week_pnl": round(engine._engine._week_pnl, 4) if engine._engine else 0,
    })
