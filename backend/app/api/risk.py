"""
리스크 API 엔드포인트
- 현재 리스크 상태, 메트릭 조회
- 트레이딩 엔진의 실시간 데이터 기반
- 사용처: 리스크 대시보드 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response
from app.api.trading import _get_engine
from app.services.risk.risk_manager import RiskConfig

router = APIRouter()

# 기본 리스크 설정 (상수)
_config = RiskConfig()


@router.get("/status")
async def get_risk_status():
    """현재 리스크 상태 (실시간)"""
    engine = _get_engine()
    te = engine._engine
    status = engine.get_status()

    positions = status.get("positions", [])
    today_pnl = te._today_pnl if te else 0
    week_pnl = te._week_pnl if te else 0
    today_trades = te._today_trades if te else []
    recent_trades = te._recent_trades if te else []

    # 잔고
    balance = engine._paper_balance if engine._paper_mode else 0

    # 연속 손실 계산
    consecutive_losses = 0
    for trade in reversed(recent_trades):
        pnl = trade.get("pnl", 0) if isinstance(trade, dict) else 0
        if pnl < 0:
            consecutive_losses += 1
        else:
            break

    # 일일 손실 사용률 (%)
    daily_limit = balance * _config.daily_loss_limit
    daily_used_pct = (abs(today_pnl) / daily_limit * 100) if daily_limit > 0 and today_pnl < 0 else 0

    # 주간 손실 사용률 (%)
    weekly_limit = balance * _config.weekly_loss_limit
    weekly_used_pct = (abs(week_pnl) / weekly_limit * 100) if weekly_limit > 0 and week_pnl < 0 else 0

    # 포지션 노출도
    max_positions = (
        _config.max_positions_medium
        if balance > _config.position_threshold
        else _config.max_positions_small
    )

    # 연속 손실 상태
    if consecutive_losses >= _config.consecutive_loss_stop:
        loss_action = "stop"
    elif consecutive_losses >= _config.consecutive_loss_reduce:
        loss_action = "reduce"
    else:
        loss_action = "none"

    return success_response({
        # 잔고
        "balance": round(balance, 2),
        "mode": status.get("mode", "paper"),

        # 손실 한도
        "daily_pnl": round(today_pnl, 4),
        "daily_loss_limit_pct": _config.daily_loss_limit * 100,
        "daily_used_pct": round(daily_used_pct, 1),
        "daily_breached": daily_used_pct >= 100,

        "weekly_pnl": round(week_pnl, 4),
        "weekly_loss_limit_pct": _config.weekly_loss_limit * 100,
        "weekly_used_pct": round(weekly_used_pct, 1),
        "weekly_breached": weekly_used_pct >= 100,

        # 포지션
        "open_positions": len(positions),
        "max_positions": max_positions,
        "position_used_pct": round(len(positions) / max_positions * 100, 0) if max_positions > 0 else 0,

        # 거래 횟수
        "today_trade_count": len(today_trades),
        "max_daily_trades": _config.max_daily_trades,
        "trade_used_pct": round(len(today_trades) / _config.max_daily_trades * 100, 0),

        # 레버리지
        "leverage": status.get("leverage", 0),
        "max_leverage": _config.max_leverage,
        "leverage_used_pct": round(status.get("leverage", 0) / _config.max_leverage * 100, 0),

        # 연속 손실
        "consecutive_losses": consecutive_losses,
        "consecutive_loss_reduce_at": _config.consecutive_loss_reduce,
        "consecutive_loss_stop_at": _config.consecutive_loss_stop,
        "loss_action": loss_action,
        "reduce_factor": _config.reduce_factor,

        # 리스크 설정
        "max_risk_per_trade_pct": _config.max_risk_per_trade * 100,

        # 전체 위험도 (0~100)
        "overall_risk_score": _calc_overall_risk(
            daily_used_pct, weekly_used_pct, consecutive_losses,
            len(today_trades), _config.max_daily_trades,
        ),

        # 엔진 상태
        "running": status.get("running", False),
        "ws_connected": status.get("ws_connected", False),
    })


def _calc_overall_risk(
    daily_pct: float,
    weekly_pct: float,
    consec_losses: int,
    trade_count: int,
    max_trades: int,
) -> int:
    """전체 위험도 점수 (0~100)"""
    score = 0.0
    # 일일 손실 (가중치 35%)
    score += min(daily_pct, 100) * 0.35
    # 주간 손실 (가중치 25%)
    score += min(weekly_pct, 100) * 0.25
    # 연속 손실 (가중치 25%, 5연패=100)
    score += min(consec_losses / 5 * 100, 100) * 0.25
    # 거래 횟수 (가중치 15%)
    score += min(trade_count / max_trades * 100, 100) * 0.15
    return min(int(score), 100)
