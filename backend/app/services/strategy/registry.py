"""
전략 레지스트리
- 내장 전략 등록 및 조회
- 전략 이름으로 인스턴스 생성
- 사용처: 전략 API, 트레이딩 엔진
"""

from app.services.strategy.base_strategy import BaseStrategy
from app.services.strategy.funding_rate_strategy import FundingRateStrategy

# --- 내장 전략 목록 ---
BUILTIN_STRATEGIES: dict[str, type[BaseStrategy]] = {
    "funding_rate": FundingRateStrategy,
}


def get_strategy(name: str, params: dict | None = None) -> BaseStrategy:
    """전략 이름으로 인스턴스 생성"""
    strategy_class = BUILTIN_STRATEGIES.get(name)
    if not strategy_class:
        raise ValueError(f"알 수 없는 전략: {name}")
    return strategy_class(params)


def list_strategies() -> list[dict]:
    """사용 가능한 전략 목록 반환"""
    return [
        {
            "name": cls.name,
            "description": cls.description,
            "default_params": cls.default_params,
        }
        for cls in BUILTIN_STRATEGIES.values()
    ]
