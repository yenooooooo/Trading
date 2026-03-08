"""
MACD 크로스오버 전략
- MACD가 시그널선 상향 돌파 → 롱 진입
- MACD가 시그널선 하향 돌파 → 숏 진입
- 반대 크로스 시 종료
- 사용처: 내장 전략 #2
"""

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy,
    TradeSignal,
    SignalType,
)
from app.services.strategy.indicators import closes, macd


class MACDStrategy(BaseStrategy):
    """MACD 크로스오버 추세 추종 전략"""

    name = "macd_crossover"
    description = "MACD 골든/데드 크로스 전략"
    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "min_histogram": 0.0,  # 최소 히스토그램 크기 (노이즈 필터)
    }

    async def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        current_position: str | None = None,
    ) -> TradeSignal:
        min_candles = self.params["slow_period"] + self.params["signal_period"]
        if len(candles) < min_candles + 2:
            return TradeSignal(signal=SignalType.HOLD, symbol=symbol)

        prices = closes(candles)
        macd_line, signal_line, histogram = macd(
            prices,
            self.params["fast_period"],
            self.params["slow_period"],
            self.params["signal_period"],
        )

        curr_hist = histogram[-1]
        prev_hist = histogram[-2]
        min_hist = self.params["min_histogram"]

        # 골든 크로스: 히스토그램이 음 → 양으로 전환
        golden_cross = prev_hist <= 0 and curr_hist > min_hist
        # 데드 크로스: 히스토그램이 양 → 음으로 전환
        dead_cross = prev_hist >= 0 and curr_hist < -min_hist

        # --- 포지션 종료 ---
        if current_position == "long" and dead_cross:
            return TradeSignal(
                signal=SignalType.CLOSE,
                symbol=symbol,
                strength=min(abs(curr_hist) / abs(prices[-1]) * 1000, 1.0),
                reason=f"MACD 데드크로스 → 롱 종료",
            )

        if current_position == "short" and golden_cross:
            return TradeSignal(
                signal=SignalType.CLOSE,
                symbol=symbol,
                strength=min(abs(curr_hist) / abs(prices[-1]) * 1000, 1.0),
                reason=f"MACD 골든크로스 → 숏 종료",
            )

        # --- 진입 ---
        if current_position is None:
            if golden_cross:
                return TradeSignal(
                    signal=SignalType.LONG,
                    symbol=symbol,
                    strength=min(abs(curr_hist) / abs(prices[-1]) * 1000, 1.0),
                    reason=f"MACD 골든크로스 → 롱 진입",
                )

            if dead_cross:
                return TradeSignal(
                    signal=SignalType.SHORT,
                    symbol=symbol,
                    strength=min(abs(curr_hist) / abs(prices[-1]) * 1000, 1.0),
                    reason=f"MACD 데드크로스 → 숏 진입",
                )

        return TradeSignal(
            signal=SignalType.HOLD,
            symbol=symbol,
            reason=f"MACD hist={curr_hist:.4f} → 대기",
        )
