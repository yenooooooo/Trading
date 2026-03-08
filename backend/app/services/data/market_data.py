"""
시장 데이터 서비스
- 거래소에서 시세/캔들/티커 데이터 조회
- Redis 캐싱으로 API 호출 최소화
- 사용처: 전략 엔진, 시장 데이터 API
"""

from decimal import Decimal
import structlog

from app.services.exchange.base import ExchangeConnector, Ticker, Candle

logger = structlog.get_logger()


class MarketDataService:
    """시장 데이터 조회 서비스"""

    def __init__(self, connector: ExchangeConnector):
        self.connector = connector

    # --- 시세 조회 ---

    async def get_ticker(self, symbol: str) -> Ticker:
        """실시간 시세 조회"""
        return await self.connector.get_ticker(symbol)

    async def get_tickers(self, symbols: list[str]) -> list[Ticker]:
        """여러 심볼 시세 조회"""
        tickers = []
        for symbol in symbols:
            try:
                ticker = await self.connector.get_ticker(symbol)
                tickers.append(ticker)
            except Exception as e:
                logger.warning("ticker_fetch_failed", symbol=symbol, error=str(e))
        return tickers

    # --- 캔들 데이터 ---

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        """OHLCV 캔들 데이터 조회"""
        return await self.connector.get_klines(symbol, interval, limit)

    # --- 현재가 ---

    async def get_price(self, symbol: str) -> Decimal:
        """현재가만 빠르게 조회"""
        ticker = await self.connector.get_ticker(symbol)
        return ticker.price

    # --- 변동성 계산 ---

    async def get_volatility(
        self, symbol: str, interval: str = "1h", period: int = 24
    ) -> float:
        """ATR 기반 변동성 계산 (%)"""
        candles = await self.get_candles(symbol, interval, limit=period + 1)
        if len(candles) < 2:
            return 0.0

        # ATR(Average True Range) 계산
        true_ranges = []
        for i in range(1, len(candles)):
            high = float(candles[i].high)
            low = float(candles[i].low)
            prev_close = float(candles[i - 1].close)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        atr = sum(true_ranges) / len(true_ranges)
        current_price = float(candles[-1].close)

        return (atr / current_price) * 100 if current_price > 0 else 0.0
