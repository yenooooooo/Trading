"""
전략 스키마
- 전략 생성/수정/조회 요청·응답 모델
- 사용처: strategies API 라우터
"""

from pydantic import BaseModel
from uuid import UUID


class StrategyCreate(BaseModel):
    """전략 생성 요청"""
    name: str                          # 사용자 지정 이름
    strategy_type: str                 # rsi_reversal, macd_crossover 등
    symbol: str                        # BTC-USDT 형식
    interval: str = "1h"               # 캔들 주기
    leverage: int = 1                  # 레버리지 (1~20)
    max_position_pct: float = 0.1      # 잔고 대비 최대 포지션 비율
    params: dict | None = None         # 전략 파라미터 오버라이드


class StrategyUpdate(BaseModel):
    """전략 수정 요청"""
    name: str | None = None
    interval: str | None = None
    leverage: int | None = None
    max_position_pct: float | None = None
    params: dict | None = None


class StrategyResponse(BaseModel):
    """전략 응답"""
    id: str
    name: str
    strategy_type: str
    symbol: str
    interval: str
    leverage: int
    max_position_pct: float
    params: dict
    status: str                        # active, paused, stopped
    is_active: bool


class SignalCheckResponse(BaseModel):
    """전략 신호 체크 응답"""
    signal: str
    symbol: str
    strength: float
    reason: str
