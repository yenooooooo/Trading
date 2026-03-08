"""
시장 데이터 API 엔드포인트
- 실시간 시세, OHLCV 캔들, 변동성 조회
- 인증 불필요 (공개 데이터)
- 사용처: 트레이딩 뷰, 차트, 대시보드
"""

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_connector
from app.services.exchange.binance import BinanceFuturesConnector
from app.services.data.market_data import MarketDataService
from app.schemas.common import success_response

router = APIRouter()

# 인기 선물 심볼 목록
POPULAR_SYMBOLS = [
    "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
    "XRP/USDT:USDT", "DOGE/USDT:USDT", "ADA/USDT:USDT",
    "AVAX/USDT:USDT", "LINK/USDT:USDT", "DOT/USDT:USDT",
    "MATIC/USDT:USDT",
]


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    connector: BinanceFuturesConnector = Depends(get_connector),
):
    """실시간 시세 조회 (예: BTC-USDT → BTC/USDT:USDT)"""
    # URL 친화적 심볼 변환: BTC-USDT → BTC/USDT:USDT
    formatted = symbol.replace("-", "/") + ":USDT"
    svc = MarketDataService(connector)
    ticker = await svc.get_ticker(formatted)

    return success_response({
        "symbol": ticker.symbol,
        "price": str(ticker.price),
        "change_24h": ticker.change_24h,
        "volume_24h": str(ticker.volume_24h),
        "high_24h": str(ticker.high_24h),
        "low_24h": str(ticker.low_24h),
    })


@router.get("/tickers")
async def get_tickers(
    connector: BinanceFuturesConnector = Depends(get_connector),
):
    """인기 심볼 시세 일괄 조회"""
    svc = MarketDataService(connector)
    tickers = await svc.get_tickers(POPULAR_SYMBOLS)

    return success_response([
        {
            "symbol": t.symbol,
            "price": str(t.price),
            "change_24h": t.change_24h,
            "volume_24h": str(t.volume_24h),
        }
        for t in tickers
    ])


@router.get("/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = Query(default="1h", description="1m,5m,15m,1h,4h,1d"),
    limit: int = Query(default=100, le=500),
    connector: BinanceFuturesConnector = Depends(get_connector),
):
    """OHLCV 캔들 데이터"""
    formatted = symbol.replace("-", "/") + ":USDT"
    svc = MarketDataService(connector)
    candles = await svc.get_candles(formatted, interval, limit)

    return success_response([
        {
            "timestamp": c.timestamp,
            "open": str(c.open),
            "high": str(c.high),
            "low": str(c.low),
            "close": str(c.close),
            "volume": str(c.volume),
        }
        for c in candles
    ])


@router.get("/volatility/{symbol}")
async def get_volatility(
    symbol: str,
    connector: BinanceFuturesConnector = Depends(get_connector),
):
    """심볼 변동성 (ATR 기반 %)"""
    formatted = symbol.replace("-", "/") + ":USDT"
    svc = MarketDataService(connector)
    vol = await svc.get_volatility(formatted)

    return success_response({
        "symbol": formatted,
        "volatility_pct": round(vol, 4),
    })
