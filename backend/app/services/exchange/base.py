"""
거래소 커넥터 추상 클래스
- 모든 거래소 커넥터의 공통 인터페이스 정의
- 전략 코드는 이 인터페이스에만 의존 (거래소 독립적)
- 사용처: BinanceConnector, BybitConnector 등에서 상속
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime


# --- 공통 데이터 클래스 ---

@dataclass
class Balance:
    """잔고 정보"""
    total: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    used: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str = ""
    side: str = ""  # 'long' | 'short'
    size: Decimal = Decimal("0")
    entry_price: Decimal = Decimal("0")
    mark_price: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    leverage: int = 1
    liquidation_price: Decimal = Decimal("0")


@dataclass
class OrderResult:
    """주문 결과"""
    order_id: str = ""
    exchange_order_id: str = ""
    symbol: str = ""
    type: str = ""
    side: str = ""
    price: Decimal | None = None
    amount: Decimal = Decimal("0")
    filled: Decimal = Decimal("0")
    status: str = ""
    timestamp: datetime | None = None


@dataclass
class Ticker:
    """실시간 시세"""
    symbol: str = ""
    price: Decimal = Decimal("0")
    change_24h: float = 0.0
    volume_24h: Decimal = Decimal("0")
    high_24h: Decimal = Decimal("0")
    low_24h: Decimal = Decimal("0")


@dataclass
class Candle:
    """OHLCV 캔들"""
    timestamp: int = 0
    open: Decimal = Decimal("0")
    high: Decimal = Decimal("0")
    low: Decimal = Decimal("0")
    close: Decimal = Decimal("0")
    volume: Decimal = Decimal("0")


class ExchangeConnector(ABC):
    """
    거래소 커넥터 추상 클래스

    설계 원칙:
    1. 거래소 추상화 — 전략 코드는 거래소에 독립적
    2. Rate Limit 자동 관리 — 429 에러 방지
    3. 재연결 로직 — WebSocket 끊김 자동 복구
    4. 모든 금액은 Decimal — float 사용 금지
    """

    @abstractmethod
    async def connect(self) -> bool:
        """거래소 연결 및 인증 확인"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """연결 종료"""
        pass

    @abstractmethod
    async def get_balance(self) -> Balance:
        """잔고 조회"""
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> PositionInfo | None:
        """특정 심볼 포지션 조회"""
        pass

    @abstractmethod
    async def get_all_positions(self) -> list[PositionInfo]:
        """모든 활성 포지션 조회"""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """실시간 시세 조회"""
        pass

    @abstractmethod
    async def get_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        """OHLCV 캔들 데이터 조회"""
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Decimal | None = None,
        params: dict | None = None,
    ) -> OrderResult:
        """주문 실행"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """주문 취소"""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """미체결 주문 조회"""
        pass
