"""
전략 엔진 베이스 클래스
- 모든 트레이딩 전략의 공통 인터페이스
- 시장 미시구조 데이터(펀딩비, OI 등)도 신호 입력으로 지원
- 사용처: 펀딩비, 청산 반등, 변동성 돌파 등 실전 전략에서 상속
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from app.services.exchange.base import Candle


class SignalType(Enum):
    """매매 신호 타입"""
    LONG = "long"
    SHORT = "short"
    CLOSE = "close"
    HOLD = "hold"


@dataclass
class TradeSignal:
    """전략이 생성하는 매매 신호"""
    signal: SignalType
    symbol: str
    strength: float = 0.0       # 신호 강도 (0~1)
    reason: str = ""            # 신호 발생 이유
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    amount_pct: float = 1.0     # 자본 대비 진입 비율 (0~1)


@dataclass
class MarketContext:
    """
    전략에 전달되는 시장 맥락 데이터
    - 캔들 외에 펀딩비, 거래량 급등, 변동성 등 추가 정보
    """
    candles: list[Candle] = field(default_factory=list)
    funding_rate: float = 0.0           # 현재 펀딩비 (%)
    predicted_funding: float = 0.0      # 예측 펀딩비 (%)
    volume_ratio: float = 1.0           # 평균 대비 거래량 배율
    spread_pct: float = 0.0             # 스프레드 (%)
    open_interest_change: float = 0.0   # OI 변화율 (%)
    long_short_ratio: float = 1.0       # 롱숏 비율


class BaseStrategy(ABC):
    """
    전략 베이스 클래스

    구현 규칙:
    1. name, description 속성 정의
    2. default_params 정의 (기본 파라미터)
    3. generate_signal() 구현 — 시장 데이터 → 매매 신호
    4. min_candles 정의 — 최소 캔들 수
    """

    name: str = ""
    description: str = ""
    default_params: dict = {}
    min_candles: int = 50    # 전략 실행에 필요한 최소 캔들 수

    def __init__(self, params: dict | None = None):
        self.params = {**self.default_params, **(params or {})}

    @abstractmethod
    async def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        current_position: str | None = None,
        context: MarketContext | None = None,
    ) -> TradeSignal:
        """
        시장 데이터를 분석하여 매매 신호 생성

        Args:
            symbol: 심볼 (예: BTC/USDT:USDT)
            candles: OHLCV 캔들 리스트 (과거→현재)
            current_position: 현재 포지션 ('long', 'short', None)
            context: 추가 시장 맥락 (펀딩비, OI 등)
        """
        pass

    def get_param(self, key: str, default=None):
        """파라미터 안전 조회"""
        return self.params.get(key, default)
