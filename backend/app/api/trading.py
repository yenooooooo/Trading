"""
실시간 트레이딩 API 엔드포인트
- POST /start: 트레이딩 시작
- POST /stop: 트레이딩 중지
- POST /emergency-stop: 긴급 정지 (포지션 전체 청산)
- GET /status: 현재 상태 조회
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.trading.live_trading import LiveTradingEngine
from app.schemas.common import success_response

router = APIRouter()

# 싱글톤 엔진 인스턴스
_engine: LiveTradingEngine | None = None


def _get_engine() -> LiveTradingEngine:
    global _engine
    if _engine is None:
        _engine = LiveTradingEngine()
    return _engine


class StartRequest(BaseModel):
    symbols: list[str] | None = None  # e.g. ["BTC/USDT:USDT"]


@router.post("/start")
async def start_trading(body: StartRequest | None = None):
    """트레이딩 시작"""
    engine = _get_engine()

    if engine.get_status()["running"]:
        raise HTTPException(status_code=409, detail="이미 실행 중입니다")

    symbols = body.symbols if body and body.symbols else None
    await engine.start(symbols=symbols)

    return success_response(engine.get_status())


@router.post("/stop")
async def stop_trading():
    """트레이딩 중지"""
    engine = _get_engine()

    if not engine.get_status()["running"]:
        raise HTTPException(status_code=409, detail="실행 중이 아닙니다")

    await engine.stop()
    return success_response({"stopped": True})


@router.post("/emergency-stop")
async def emergency_stop():
    """긴급 정지: 모든 포지션 청산 후 종료"""
    engine = _get_engine()
    await engine.emergency_stop()
    return success_response({"emergency_stopped": True})


@router.get("/status")
async def get_status():
    """현재 트레이딩 상태 조회"""
    engine = _get_engine()
    return success_response(engine.get_status())
