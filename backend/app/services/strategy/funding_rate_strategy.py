"""
펀딩비 수확 전략 (Funding Rate Farm)
- 목적: 펀딩비 수입을 안정적으로 수확, 가격 변동 리스크 최소화
- 펀딩비 양수 → 숏 진입 (숏이 펀딩비 수취)
- 펀딩비 음수 → 롱 진입 (롱이 펀딩비 수취)
- 빡빡한 손절/익절로 가격 리스크 제한
- 펀딩비 정산 후 빠르게 청산
"""

from decimal import Decimal

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy, TradeSignal, SignalType, MarketContext,
)
from app.services.strategy.indicators import closes, ema
from app.services.strategy.fee_calculator import is_profitable_signal


class FundingRateStrategy(BaseStrategy):
    """펀딩비 수확 전략 - 펀딩비 수입 극대화, 가격 리스크 최소화"""

    name = "funding_rate"
    description = "펀딩비 수확 - 펀딩비 수입 목적, 가격 헷지"
    min_candles = 30
    default_params = {
        "dynamic_std_mult": 1.0,        # 동적 기준: 평균 + 1σ (1.5→1.0 완화)
        "funding_min_abs": 0.01,        # 최소 펀딩비 절대값 (%)
        "sl_pct": 1.0,                  # 손절 (%) - 빡빡하게
        "tp_pct": 1.5,                  # 익절 (%)
        "max_hold_bars": 24,            # 최대 보유 (24봉 = 24시간)
        "post_funding_exit_bars": 2,    # 펀딩비 정산 후 청산까지 대기 봉수
        "position_size_pct": 0.3,       # 포지션 크기 (잔고의 30%)
        "daily_loss_limit_pct": 3.0,    # 일일 최대 손실 (%)
        "cooldown_bars": 4,             # 쿨다운 (4시간)
    }

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self._funding_history: list[float] = []
        self._entry_price: float = 0.0
        self._entry_bar: int = 0
        self._position_side: str = ""
        self._is_in_position: bool = False
        self._last_exit_bar: int = -100
        self._daily_pnl: float = 0.0
        self._last_funding_bar: int = -100  # 마지막 펀딩비 정산 봉

    async def generate_signal(
        self,
        symbol: str,
        candles: list[Candle],
        current_position: str | None = None,
        context: MarketContext | None = None,
    ) -> TradeSignal:
        hold = TradeSignal(signal=SignalType.HOLD, symbol=symbol, reason="대기")

        if len(candles) < self.min_candles:
            return hold

        if not context:
            return hold

        funding = context.funding_rate
        current_price = float(candles[-1].close)
        current_bar = len(candles) - 1

        # 펀딩비 히스토리 업데이트
        self._funding_history.append(funding)
        if len(self._funding_history) > 90:
            self._funding_history = self._funding_history[-90:]

        # 펀딩비 정산 시각 감지 (8봉마다 = 8시간)
        is_near_funding = (current_bar % 8) >= 7  # 정산 1봉 전
        is_post_funding = (current_bar % 8) <= 1   # 정산 직후 2봉

        # --- 포지션 보유 중: 청산 조건 ---
        if self._is_in_position and current_position:
            sl_pct = self.get_param("sl_pct", 1.0)
            tp_pct = self.get_param("tp_pct", 1.5)
            max_hold = int(self.get_param("max_hold_bars", 24))
            post_exit = int(self.get_param("post_funding_exit_bars", 2))

            if self._position_side == "long":
                price_change = (current_price - self._entry_price) / self._entry_price * 100
            else:
                price_change = (self._entry_price - current_price) / self._entry_price * 100

            bars_held = current_bar - self._entry_bar

            # 1) 손절
            if price_change <= -sl_pct:
                self._exit_position(current_bar, price_change)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=1.0,
                    reason=f"손절 {price_change:+.2f}% (한도 -{sl_pct}%)",
                )

            # 2) 익절
            if price_change >= tp_pct:
                self._exit_position(current_bar, price_change)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=1.0,
                    reason=f"익절 {price_change:+.2f}% (목표 +{tp_pct}%)",
                )

            # 3) 펀딩비 정산 후 청산 (핵심: 펀딩비 받고 빠르게 나감)
            if bars_held >= 8 and is_post_funding and bars_held >= 8 + post_exit:
                self._exit_position(current_bar, price_change)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=0.8,
                    reason=f"펀딩비 정산 후 청산 (보유 {bars_held}봉, P/L {price_change:+.2f}%)",
                )

            # 4) 펀딩비가 중립으로 돌아옴 → 추가 수입 기대 없음
            if abs(funding) < self.get_param("funding_min_abs", 0.01):
                self._exit_position(current_bar, price_change)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=0.7,
                    reason=f"펀딩비 중립 ({funding:+.4f}%) → 청산 (P/L {price_change:+.2f}%)",
                )

            # 5) 최대 보유 시간 초과
            if bars_held >= max_hold:
                self._exit_position(current_bar, price_change)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=0.8,
                    reason=f"최대 보유 초과 {bars_held}봉 (P/L {price_change:+.2f}%)",
                )

            return hold

        # 외부 청산 감지
        if self._is_in_position and not current_position:
            self._clear_position()

        # --- 쿨다운 ---
        cooldown = int(self.get_param("cooldown_bars", 4))
        if current_bar - self._last_exit_bar < cooldown:
            return hold

        # --- 일일 손실 제한 ---
        daily_limit = self.get_param("daily_loss_limit_pct", 3.0)
        if self._daily_pnl <= -daily_limit:
            return TradeSignal(
                signal=SignalType.HOLD, symbol=symbol,
                reason=f"일일 손실 한도 도달 ({self._daily_pnl:.2f}%)",
            )

        # --- 진입 조건 ---
        # 펀딩비 정산 전에만 진입 (정산 직전 1봉)
        if not is_near_funding:
            return hold

        # 동적 임계값 계산
        min_abs = self.get_param("funding_min_abs", 0.01)
        std_mult = self.get_param("dynamic_std_mult", 1.0)

        if abs(funding) < min_abs:
            return hold

        threshold_met = False
        if len(self._funding_history) >= 20:
            avg_f = sum(self._funding_history) / len(self._funding_history)
            variance = sum((f - avg_f) ** 2 for f in self._funding_history) / len(self._funding_history)
            std_f = variance ** 0.5

            if funding > 0 and funding >= avg_f + std_mult * std_f:
                threshold_met = True
            elif funding < 0 and funding <= avg_f - std_mult * std_f:
                threshold_met = True
        else:
            # 히스토리 부족 시 고정 기준
            if abs(funding) >= 0.02:
                threshold_met = True

        if not threshold_met:
            return hold

        # --- 신호 생성 ---
        pos_size = self.get_param("position_size_pct", 0.3)
        strength = min(abs(funding) / 0.05, 1.0)

        if funding > 0:
            # 양수 펀딩비 → 숏 진입 (숏이 펀딩비 수취)
            if current_position == "short":
                return hold

            if current_position == "long":
                self._clear_position()
                self._last_exit_bar = current_bar
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=strength,
                    reason=f"펀딩비 양수 {funding:+.4f}% -> 롱 청산",
                )

            sl = Decimal(str(current_price * (1 + self.get_param("sl_pct", 1.0) / 100)))
            tp = Decimal(str(current_price * (1 - self.get_param("tp_pct", 1.5) / 100)))

            self._enter_position(current_bar, current_price, "short")
            return TradeSignal(
                signal=SignalType.SHORT, symbol=symbol,
                strength=strength,
                reason=f"펀딩비 수확: {funding:+.4f}% (숏=수취)",
                stop_loss=sl, take_profit=tp,
                amount_pct=pos_size,
            )

        else:
            # 음수 펀딩비 → 롱 진입 (롱이 펀딩비 수취)
            if current_position == "long":
                return hold

            if current_position == "short":
                self._clear_position()
                self._last_exit_bar = current_bar
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=strength,
                    reason=f"펀딩비 음수 {funding:+.4f}% -> 숏 청산",
                )

            sl = Decimal(str(current_price * (1 - self.get_param("sl_pct", 1.0) / 100)))
            tp = Decimal(str(current_price * (1 + self.get_param("tp_pct", 1.5) / 100)))

            self._enter_position(current_bar, current_price, "long")
            return TradeSignal(
                signal=SignalType.LONG, symbol=symbol,
                strength=strength,
                reason=f"펀딩비 수확: {funding:+.4f}% (롱=수취)",
                stop_loss=sl, take_profit=tp,
                amount_pct=pos_size,
            )

    def _enter_position(self, bar: int, price: float, side: str):
        self._entry_price = price
        self._entry_bar = bar
        self._position_side = side
        self._is_in_position = True

    def _exit_position(self, bar: int, pnl_pct: float):
        self._daily_pnl += pnl_pct
        self._last_exit_bar = bar
        self._clear_position()

    def _clear_position(self):
        self._entry_price = 0.0
        self._entry_bar = 0
        self._position_side = ""
        self._is_in_position = False
