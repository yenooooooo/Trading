"""
거래소 커넥터 팩토리
- 거래소 이름으로 적절한 커넥터 인스턴스 생성
- 사용처: API 라우터, 전략 엔진에서 커넥터 생성 시
"""

from app.services.exchange.base import ExchangeConnector
from app.services.exchange.binance import BinanceFuturesConnector
from app.core.exceptions import ValidationError


def create_connector(
    exchange: str,
    api_key: str,
    secret_key: str,
    testnet: bool = False,
) -> ExchangeConnector:
    """거래소 이름에 맞는 커넥터 생성"""

    connectors = {
        "binance": BinanceFuturesConnector,
        # "bybit": BybitConnector,   # Phase 5에서 추가
        # "okx": OkxConnector,       # Phase 5에서 추가
    }

    connector_class = connectors.get(exchange.lower())
    if not connector_class:
        raise ValidationError(f"지원하지 않는 거래소: {exchange}")

    return connector_class(
        api_key=api_key,
        secret_key=secret_key,
        testnet=testnet,
    )
