"""
RSI 과매수/과매도 전략
- RSI가 과매도(30 이하) → 롱 진입
- RSI가 과매수(70 이상) → 숏 진입
- 반대 신호 또는 중립대(40~60) 복귀 시 종료
- 사용처: 내장 전략 #1
"""

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy,
    TradeSignal,
    SignalType,
)
from app.services.strategy.indicators import closes, rsi


class RSIStrategy(BaseStrategy):
    """RSI 기반 추세 반전 전략"""

    name = "rsi_reversal"
    description = "RSI 과매수/과매도 반전 전략"
    default_params = {
        "rsi_period": 14,
        "overbought": 70,
        "oversold": 30,
        "exit_upper": 60,
        "exit_lower": 40,
    }

    async def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        current_position: str | None = None,
    ) -> TradeSignal:
        if len(candles) < self.params["rsi_period"] + 2:
            return TradeSignal(signal=SignalType.HOLD, symbol=symbol)

        prices = closes(candles)
        rsi_values = rsi(prices, self.params["rsi_period"])
        current_rsi = rsi_values[-1]
        prev_rsi = rsi_values[-2]

        oversold = self.params["oversold"]
        overbought = self.params["overbought"]
        exit_upper = self.params["exit_upper"]
        exit_lower = self.params["exit_lower"]

        # --- 포지션 종료 신호 ---
        if current_position == "long" and current_rsi >= exit_upper:
            return TradeSignal(
                signal=SignalType.CLOSE,
                symbol=symbol,
                strength=min((current_rsi - exit_upper) / 20, 1.0),
                reason=f"RSI {current_rsi:.1f} → 중립대 복귀, 롱 종료",
            )

        if current_position == "short" and current_rsi <= exit_lower:
            return TradeSignal(
                signal=SignalType.CLOSE,
                symbol=symbol,
                strength=min((exit_lower - current_rsi) / 20, 1.0),
                reason=f"RSI {current_rsi:.1f} → 중립대 복귀, 숏 종료",
            )

        # --- 진입 신호 (포지션 없을 때만) ---
        if current_position is None:
            if prev_rsi > oversold and current_rsi <= oversold:
                return TradeSignal(
                    signal=SignalType.LONG,
                    symbol=symbol,
                    strength=min((oversold - current_rsi) / 10, 1.0),
                    reason=f"RSI {current_rsi:.1f} → 과매도 진입, 롱",
                )

            if prev_rsi < overbought and current_rsi >= overbought:
                return TradeSignal(
                    signal=SignalType.SHORT,
                    symbol=symbol,
                    strength=min((current_rsi - overbought) / 10, 1.0),
                    reason=f"RSI {current_rsi:.1f} → 과매수 진입, 숏",
                )

        return TradeSignal(
            signal=SignalType.HOLD,
            symbol=symbol,
            reason=f"RSI {current_rsi:.1f} → 대기",
        )
