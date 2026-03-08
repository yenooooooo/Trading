"""
볼린저밴드 전략
- 가격이 하단 밴드 터치 → 롱 진입 (반등 기대)
- 가격이 상단 밴드 터치 → 숏 진입 (되돌림 기대)
- 중간선(SMA) 도달 시 종료
- 사용처: 내장 전략 #3
"""

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy,
    TradeSignal,
    SignalType,
)
from app.services.strategy.indicators import closes, bollinger_bands


class BollingerStrategy(BaseStrategy):
    """볼린저밴드 평균 회귀 전략"""

    name = "bollinger_reversal"
    description = "볼린저밴드 상/하단 반전 전략"
    default_params = {
        "bb_period": 20,
        "bb_std": 2.0,
    }

    async def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        current_position: str | None = None,
    ) -> TradeSignal:
        if len(candles) < self.params["bb_period"] + 2:
            return TradeSignal(signal=SignalType.HOLD, symbol=symbol)

        prices = closes(candles)
        upper, middle, lower = bollinger_bands(
            prices, self.params["bb_period"], self.params["bb_std"]
        )

        price = prices[-1]
        prev_price = prices[-2]
        curr_upper = upper[-1]
        curr_lower = lower[-1]
        curr_middle = middle[-1]
        band_width = curr_upper - curr_lower

        if band_width == 0:
            return TradeSignal(signal=SignalType.HOLD, symbol=symbol)

        # 밴드 내 위치 (0=하단, 1=상단)
        bb_position = (price - curr_lower) / band_width

        # --- 포지션 종료: 중간선 도달 ---
        if current_position == "long" and price >= curr_middle:
            return TradeSignal(
                signal=SignalType.CLOSE,
                symbol=symbol,
                strength=0.7,
                reason=f"BB 중간선 도달 → 롱 종료 (pos={bb_position:.2f})",
            )

        if current_position == "short" and price <= curr_middle:
            return TradeSignal(
                signal=SignalType.CLOSE,
                symbol=symbol,
                strength=0.7,
                reason=f"BB 중간선 도달 → 숏 종료 (pos={bb_position:.2f})",
            )

        # --- 진입: 밴드 터치 ---
        if current_position is None:
            if price <= curr_lower and prev_price > curr_lower:
                return TradeSignal(
                    signal=SignalType.LONG,
                    symbol=symbol,
                    strength=min(abs(bb_position), 1.0),
                    reason=f"BB 하단 터치 → 롱 진입 (pos={bb_position:.2f})",
                )

            if price >= curr_upper and prev_price < curr_upper:
                return TradeSignal(
                    signal=SignalType.SHORT,
                    symbol=symbol,
                    strength=min(abs(1 - bb_position), 1.0),
                    reason=f"BB 상단 터치 → 숏 진입 (pos={bb_position:.2f})",
                )

        return TradeSignal(
            signal=SignalType.HOLD,
            symbol=symbol,
            reason=f"BB pos={bb_position:.2f} → 대기",
        )
