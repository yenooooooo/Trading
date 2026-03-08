"""
전략 API 엔드포인트
- 내장 전략 목록, 전략 CRUD, 신호 체크
- 전략은 DB에 저장하여 사용자별 관리
- 사용처: 전략 관리 페이지
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_connector
from app.models.user import User
from app.models.strategy import Strategy
from app.schemas.common import success_response
from app.schemas.strategy import StrategyCreate, StrategyUpdate
from app.services.strategy.registry import (
    list_strategies as list_builtin,
    get_strategy,
)
from app.services.data.market_data import MarketDataService

router = APIRouter()


# --- 내장 전략 목록 ---

@router.get("/builtin")
async def list_builtin_strategies():
    """사용 가능한 내장 전략 목록"""
    return success_response(list_builtin())


# --- 사용자 전략 CRUD ---

@router.get("")
async def list_strategies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """내 전략 목록 조회"""
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == user.id)
    )
    strategies = result.scalars().all()

    return success_response([
        _to_response(s) for s in strategies
    ])


@router.post("")
async def create_strategy(
    body: StrategyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """새 전략 생성"""
    # 내장 전략 존재 확인
    try:
        get_strategy(body.strategy_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"알 수 없는 전략: {body.strategy_type}")

    if not (1 <= body.leverage <= 20):
        raise HTTPException(status_code=400, detail="레버리지는 1~20 사이")

    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name=body.name,
        type=body.strategy_type,
        symbol=body.symbol.replace("-", "/") + ":USDT",
        timeframe=body.interval,
        leverage=body.leverage,
        parameters=body.params or {},
        risk_settings={"max_position_pct": body.max_position_pct},
        status="paused",
    )
    db.add(strategy)
    await db.commit()

    return success_response(_to_response(strategy))


@router.get("/{strategy_id}")
async def get_strategy_detail(
    strategy_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """전략 상세 조회"""
    strategy = await _get_user_strategy(db, user.id, strategy_id)
    return success_response(_to_response(strategy))


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    body: StrategyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """전략 수정"""
    strategy = await _get_user_strategy(db, user.id, strategy_id)

    if body.name is not None:
        strategy.name = body.name
    if body.interval is not None:
        strategy.timeframe = body.interval
    if body.leverage is not None:
        if not (1 <= body.leverage <= 20):
            raise HTTPException(status_code=400, detail="레버리지는 1~20 사이")
        strategy.leverage = body.leverage
    if body.max_position_pct is not None:
        strategy.max_position_pct = body.max_position_pct
    if body.params is not None:
        strategy.parameters = body.params

    await db.commit()
    return success_response(_to_response(strategy))


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """전략 삭제"""
    strategy = await _get_user_strategy(db, user.id, strategy_id)
    await db.delete(strategy)
    await db.commit()
    return success_response({"deleted": True})


# --- 전략 시작/중지 ---

@router.post("/{strategy_id}/start")
async def start_strategy(
    strategy_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """전략 활성화"""
    strategy = await _get_user_strategy(db, user.id, strategy_id)
    strategy.status = "active"
    await db.commit()
    return success_response(_to_response(strategy))


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """전략 중지"""
    strategy = await _get_user_strategy(db, user.id, strategy_id)
    strategy.status = "paused"
    await db.commit()
    return success_response(_to_response(strategy))


# --- 신호 체크 (실시간 분석) ---

@router.get("/{strategy_id}/signal")
async def check_signal(
    strategy_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    connector=Depends(get_connector),
):
    """현재 시장 데이터로 전략 신호 체크"""
    strategy = await _get_user_strategy(db, user.id, strategy_id)

    # 전략 인스턴스 생성
    engine = get_strategy(strategy.type, strategy.parameters)

    # 캔들 데이터 조회
    svc = MarketDataService(connector)
    candles = await svc.get_candles(strategy.symbol, strategy.timeframe, 100)

    # 현재 포지션 확인
    position = await connector.get_position(strategy.symbol)
    current_pos = position.side if position else None

    # 신호 생성
    signal = await engine.generate_signal(strategy.symbol, candles, current_pos)

    return success_response({
        "signal": signal.signal.value,
        "symbol": signal.symbol,
        "strength": signal.strength,
        "reason": signal.reason,
    })


# --- 헬퍼 함수 ---

async def _get_user_strategy(
    db: AsyncSession, user_id: UUID, strategy_id: str
) -> Strategy:
    """사용자의 전략 조회 (없으면 404)"""
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == UUID(strategy_id),
            Strategy.user_id == user_id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")
    return strategy


def _to_response(s: Strategy) -> dict:
    """Strategy ORM → 응답 dict"""
    risk = s.risk_settings or {}
    return {
        "id": str(s.id),
        "name": s.name,
        "strategy_type": s.type,
        "symbol": s.symbol,
        "interval": s.timeframe,
        "leverage": s.leverage,
        "max_position_pct": risk.get("max_position_pct", 0.1),
        "params": s.parameters or {},
        "status": s.status,
        "is_active": s.status == "active",
    }
