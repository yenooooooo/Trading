"""
Binance Futures (USDT-M) 커넥터
- ccxt.binanceusdm (선물 전용) 클래스 사용
- sapi/margin 엔드포인트 호출 없이 순수 선물 API만 사용
- 사용처: 거래소 커넥터 팩토리에서 생성
"""

import ccxt.async_support as ccxt
import aiohttp
from decimal import Decimal
from datetime import datetime, timezone
import structlog

from app.services.exchange.base import (
    ExchangeConnector,
    Balance,
    PositionInfo,
    OrderResult,
    Ticker,
    Candle,
)

logger = structlog.get_logger()


class BinanceFuturesConnector(ExchangeConnector):
    """바이낸스 USDT-M 선물 커넥터"""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        testnet: bool = False,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.exchange: ccxt.binanceusdm | None = None
        self._session: aiohttp.ClientSession | None = None

    # --- 연결 관리 ---

    async def connect(self) -> bool:
        """바이낸스 선물 API 연결"""
        try:
            # Windows DNS 문제 우회: ThreadedResolver 사용
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
            )

            # binanceusdm = USDT-M 선물 전용 (margin/sapi 호출 안 함)
            self.exchange = ccxt.binanceusdm({
                "apiKey": self.api_key,
                "secret": self.secret_key,
                "enableRateLimit": True,
                "session": self._session,
                "options": {
                    "adjustForTimeDifference": True,
                    "recvWindow": 10000,
                },
            })

            # 테스트넷 URL 설정
            if self.testnet:
                self.exchange.set_sandbox_mode(True)

            # 서버 시간과 동기화 후 마켓 로드
            await self.exchange.load_time_difference()
            await self.exchange.load_markets()
            logger.info("binance_connected", testnet=self.testnet)
            return True

        except ccxt.AuthenticationError:
            logger.error("binance_auth_failed", testnet=self.testnet)
            return False
        except Exception as e:
            logger.error("binance_connect_error", error=str(e))
            return False

    async def disconnect(self) -> None:
        """연결 종료"""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        logger.info("binance_disconnected")

    # --- 잔고 조회 ---

    async def get_balance(self) -> Balance:
        """USDT 선물 잔고 조회"""
        raw = await self.exchange.fetch_balance()
        usdt = raw.get("USDT", {})

        return Balance(
            total=Decimal(str(usdt.get("total", 0))),
            available=Decimal(str(usdt.get("free", 0))),
            used=Decimal(str(usdt.get("used", 0))),
            unrealized_pnl=Decimal(
                str(raw.get("info", {}).get("totalUnrealizedProfit", 0))
            ),
        )

    # --- 포지션 조회 ---

    async def get_position(self, symbol: str) -> PositionInfo | None:
        """특정 심볼 포지션 조회"""
        positions = await self.exchange.fetch_positions([symbol])

        for pos in positions:
            size = float(pos.get("contracts", 0))
            if size == 0:
                continue

            return self._parse_position(pos)

        return None

    async def get_all_positions(self) -> list[PositionInfo]:
        """모든 활성 포지션 조회"""
        positions = await self.exchange.fetch_positions()
        return [
            self._parse_position(pos)
            for pos in positions
            if float(pos.get("contracts", 0)) != 0
        ]

    def _parse_position(self, pos: dict) -> PositionInfo:
        """거래소 응답을 PositionInfo로 변환"""
        return PositionInfo(
            symbol=pos["symbol"],
            side="long" if pos["side"] == "long" else "short",
            size=Decimal(str(abs(float(pos.get("contracts", 0))))),
            entry_price=Decimal(str(pos.get("entryPrice", 0))),
            mark_price=Decimal(str(pos.get("markPrice", 0))),
            unrealized_pnl=Decimal(str(pos.get("unrealizedPnl", 0))),
            leverage=int(pos.get("leverage", 1)),
            liquidation_price=Decimal(str(pos.get("liquidationPrice", 0))),
        )

    # --- 시세 조회 ---

    async def get_ticker(self, symbol: str) -> Ticker:
        """실시간 시세 조회"""
        raw = await self.exchange.fetch_ticker(symbol)

        return Ticker(
            symbol=raw["symbol"],
            price=Decimal(str(raw.get("last", 0))),
            change_24h=float(raw.get("percentage", 0) or 0),
            volume_24h=Decimal(str(raw.get("quoteVolume", 0))),
            high_24h=Decimal(str(raw.get("high", 0))),
            low_24h=Decimal(str(raw.get("low", 0))),
        )

    async def get_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        """OHLCV 캔들 데이터 조회"""
        raw = await self.exchange.fetch_ohlcv(symbol, interval, limit=limit)

        return [
            Candle(
                timestamp=int(c[0]),
                open=Decimal(str(c[1])),
                high=Decimal(str(c[2])),
                low=Decimal(str(c[3])),
                close=Decimal(str(c[4])),
                volume=Decimal(str(c[5])),
            )
            for c in raw
        ]

    # --- 주문 실행 ---

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Decimal | None = None,
        params: dict | None = None,
    ) -> OrderResult:
        """주문 실행 — 반드시 RiskManager 통과 후 호출"""
        raw = await self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=float(amount),
            price=float(price) if price else None,
            params=params or {},
        )

        return OrderResult(
            order_id=raw["id"],
            exchange_order_id=raw.get("info", {}).get("orderId", ""),
            symbol=raw["symbol"],
            type=raw["type"],
            side=raw["side"],
            price=Decimal(str(raw["price"])) if raw.get("price") else None,
            amount=Decimal(str(raw.get("amount", 0))),
            filled=Decimal(str(raw.get("filled", 0))),
            status=raw.get("status", "unknown"),
            timestamp=datetime.now(timezone.utc),
        )

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """주문 취소"""
        try:
            await self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            logger.error("cancel_order_failed", order_id=order_id, error=str(e))
            return False

    async def get_open_orders(
        self, symbol: str | None = None
    ) -> list[OrderResult]:
        """미체결 주문 조회"""
        raw = await self.exchange.fetch_open_orders(symbol)

        return [
            OrderResult(
                order_id=o["id"],
                exchange_order_id=o.get("info", {}).get("orderId", ""),
                symbol=o["symbol"],
                type=o["type"],
                side=o["side"],
                price=Decimal(str(o["price"])) if o.get("price") else None,
                amount=Decimal(str(o.get("amount", 0))),
                filled=Decimal(str(o.get("filled", 0))),
                status=o.get("status", "unknown"),
            )
            for o in raw
        ]
