"""
백테스트 API 엔드포인트
- 백테스트 실행: 전략 + 캔들 → 결과
- 전략 목록 조회
- 사용처: 백테스트 페이지
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_connector
from app.services.exchange.binance import BinanceFuturesConnector
from app.services.data.market_data import MarketDataService
from app.services.strategy.registry import get_strategy, list_strategies
from app.services.backtest.backtest_engine import BacktestEngine
from app.schemas.common import success_response

router = APIRouter()


class BacktestRequest(BaseModel):
    """백테스트 실행 요청"""
    strategy: str = "funding_rate"
    symbol: str = "BTC-USDT"
    timeframe: str = "1h"
    initial_balance: float = 200.0
    leverage: int = 3
    candle_limit: int = 500          # 캔들 수 (max 1500)
    params: dict | None = None       # 전략 파라미터 오버라이드


@router.get("/strategies")
async def get_available_strategies():
    """사용 가능한 전략 목록"""
    return success_response(list_strategies())


@router.post("")
async def run_backtest(
    req: BacktestRequest,
    connector: BinanceFuturesConnector = Depends(get_connector),
):
    """백테스트 실행"""
    # 입력 검증
    if req.candle_limit < 50:
        raise HTTPException(400, "최소 50개 캔들 필요")
    if req.candle_limit > 1500:
        req.candle_limit = 1500
    if req.leverage < 1 or req.leverage > 20:
        raise HTTPException(400, "레버리지: 1~20")
    if req.initial_balance < 10:
        raise HTTPException(400, "최소 잔고: $10")

    # 1) 전략 생성
    try:
        strategy = get_strategy(req.strategy, req.params)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # 2) 캔들 가져오기
    formatted_symbol = req.symbol.replace("-", "/") + ":USDT"
    svc = MarketDataService(connector)

    try:
        candles = await svc.get_candles(formatted_symbol, req.timeframe, req.candle_limit)
    except Exception as e:
        raise HTTPException(500, f"캔들 조회 실패: {e}")

    if len(candles) < strategy.min_candles:
        raise HTTPException(
            400,
            f"캔들 부족: {len(candles)}개 (최소 {strategy.min_candles}개 필요)",
        )

    # 3) 백테스트 실행
    engine = BacktestEngine(
        strategy=strategy,
        initial_balance=req.initial_balance,
        leverage=req.leverage,
    )

    result = await engine.run(
        candles=candles,
        symbol=formatted_symbol,
        timeframe=req.timeframe,
    )

    return success_response(result.to_dict())
