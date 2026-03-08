"""
청산 캐스케이드 반등 전략
- 급격한 가격 하락 + OI 급감 → 청산 캐스케이드 감지
- 캐스케이드 종료 후 반등 진입
- 포지션 관리: 손절 -1.5%, 익절 +4%, 시간손절 4시간
- 쿨다운: 청산 후 30분 재진입 금지
- 소액 계좌 최적화: 큰 움직임만 포착, 저빈도 매매
"""

from decimal import Decimal

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy, TradeSignal, SignalType, MarketContext,
)
from app.services.strategy.indicators import closes, rsi, atr
from app.services.strategy.fee_calculator import is_profitable_signal


class LiquidationBounceStrategy(BaseStrategy):
    """청산 캐스케이드 반등 전략 (포지션 관리 내장)"""

    name = "liquidation_bounce"
    description = "청산 캐스케이드 반등 — 급락 후 반등 포착"
    min_candles = 50
    default_params = {
        "price_drop_pct": 1.5,          # 급락 감지 임계 (%) (3.0→1.5 완화)
        "oi_drop_pct": 5.0,             # OI 급감 임계 (%)
        "rsi_bounce_level": 30,         # RSI 반등 레벨 (25→30 완화)
        "volume_spike": 1.8,            # 거래량 급등 배수 (2.0→1.8 완화)
        "atr_period": 14,               # ATR 기간
        "sl_atr_mult": 1.5,             # 손절 ATR 배수
        "tp_atr_mult": 3.0,             # 익절 ATR 배수
        "min_expected_move": 0.3,       # 최소 예상 변동 (%) (0.5→0.3 완화)
        "sl_pct": 1.5,                  # 손절 퍼센트 (%)
        "tp_pct": 4.0,                  # 익절 퍼센트 (%)
        "max_hold_bars": 6,             # 최대 보유 캔들 수 (4→6 확장)
        "cooldown_bars": 1,             # 쿨다운 캔들 수
    }

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        # 포지션 추적 상태
        self._entry_price: float = 0.0
        self._entry_bar: int = 0
        self._position_side: str = ""
        self._is_in_position: bool = False
        self._last_exit_bar: int = -100  # 쿨다운용

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

        close_prices = closes(candles)
        current_price = close_prices[-1]
        current_bar = len(candles) - 1

        # --- 포지션 보유 중: 청산 조건 먼저 체크 ---
        if self._is_in_position and current_position:
            sl_pct = self.get_param("sl_pct", 1.5)
            tp_pct = self.get_param("tp_pct", 4.0)
            max_hold = int(self.get_param("max_hold_bars", 4))

            if self._position_side == "long":
                price_change_pct = (current_price - self._entry_price) / self._entry_price * 100
            else:
                price_change_pct = (self._entry_price - current_price) / self._entry_price * 100

            # 1) 손절: 진입가 대비 -sl_pct% 도달
            if price_change_pct <= -sl_pct:
                self._clear_position()
                self._last_exit_bar = current_bar
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=1.0,
                    reason=f"손절 {price_change_pct:+.2f}% (한도 -{sl_pct}%)",
                )

            # 2) 익절: 진입가 대비 +tp_pct% 도달
            if price_change_pct >= tp_pct:
                self._clear_position()
                self._last_exit_bar = current_bar
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=1.0,
                    reason=f"익절 {price_change_pct:+.2f}% (목표 +{tp_pct}%)",
                )

            # 3) 시간 손절: max_hold_bars 경과
            bars_held = current_bar - self._entry_bar
            if bars_held >= max_hold:
                self._clear_position()
                self._last_exit_bar = current_bar
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=0.8,
                    reason=f"시간손절 {bars_held}봉 (한도 {max_hold}봉) P/L {price_change_pct:+.2f}%",
                )

            # 청산 조건 미충족 → 홀드
            return hold

        # 외부에서 포지션이 사라진 경우 내부 상태 리셋
        if self._is_in_position and not current_position:
            self._clear_position()

        # --- 쿨다운 체크 ---
        cooldown = int(self.get_param("cooldown_bars", 1))
        if current_bar - self._last_exit_bar < cooldown:
            return hold

        # --- 진입 조건 체크 ---
        min_move = self.get_param("min_expected_move", 0.5)
        if not is_profitable_signal(min_move, leverage=1):
            return hold

        # --- 급락 감지 ---
        lookback = min(10, len(close_prices) - 1)
        recent_high = max(close_prices[-lookback - 1:-1])
        drop_pct = (recent_high - current_price) / recent_high * 100

        price_drop_threshold = self.get_param("price_drop_pct", 3.0)

        # --- OI 급감 확인 ---
        oi_change = context.open_interest_change if context else 0.0
        oi_threshold = self.get_param("oi_drop_pct", 5.0)

        # --- RSI ---
        rsi_values = rsi(close_prices, 14)
        current_rsi = rsi_values[-1]
        bounce_level = self.get_param("rsi_bounce_level", 25)

        # --- ATR (손절/익절 계산) ---
        atr_values = atr(candles, self.get_param("atr_period", 14))
        current_atr = atr_values[-1] if atr_values else 0.0

        # --- 청산 캐스케이드 감지 (롱 청산 → 급락 → 롱 반등) ---
        if drop_pct >= price_drop_threshold:
            strength = 0.0
            reasons = []

            reasons.append(f"급락 {drop_pct:.1f}%")
            strength += min(drop_pct / (price_drop_threshold * 2), 0.4)

            if oi_change <= -oi_threshold:
                strength += 0.3
                reasons.append(f"OI {oi_change:+.1f}%")

            if current_rsi <= bounce_level:
                strength += 0.2
                reasons.append(f"RSI {current_rsi:.0f}")

            vol_spike = self.get_param("volume_spike", 2.0)
            if context and context.volume_ratio >= vol_spike:
                strength += 0.1
                reasons.append(f"거래량 {context.volume_ratio:.1f}x")

            strength = min(strength, 1.0)

            if strength >= 0.4:
                sl_price = Decimal(str(
                    current_price - current_atr * self.get_param("sl_atr_mult", 1.5)
                )) if current_atr > 0 else None

                tp_price = Decimal(str(
                    current_price + current_atr * self.get_param("tp_atr_mult", 3.0)
                )) if current_atr > 0 else None

                if current_position == "short":
                    self._clear_position()
                    self._last_exit_bar = current_bar
                    return TradeSignal(
                        signal=SignalType.CLOSE, symbol=symbol,
                        strength=strength,
                        reason=" | ".join(reasons) + " → 숏 청산",
                    )

                if current_position == "long":
                    return hold

                # 포지션 상태 기록
                self._entry_price = current_price
                self._entry_bar = current_bar
                self._position_side = "long"
                self._is_in_position = True

                return TradeSignal(
                    signal=SignalType.LONG, symbol=symbol,
                    strength=strength,
                    reason="청산 반등: " + " | ".join(reasons),
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    amount_pct=min(strength * 0.6, 0.5),
                )

        # --- 급등 + 숏 청산 캐스케이드 (반대 방향) ---
        lookback_low = min(close_prices[-lookback - 1:-1])
        surge_pct = (current_price - lookback_low) / lookback_low * 100 if lookback_low > 0 else 0

        if surge_pct >= price_drop_threshold:
            strength = 0.0
            reasons = []

            reasons.append(f"급등 {surge_pct:.1f}%")
            strength += min(surge_pct / (price_drop_threshold * 2), 0.4)

            if oi_change <= -oi_threshold:
                strength += 0.3
                reasons.append(f"OI {oi_change:+.1f}%")

            if current_rsi >= (100 - bounce_level):
                strength += 0.2
                reasons.append(f"RSI {current_rsi:.0f}")

            if context and context.volume_ratio >= self.get_param("volume_spike", 2.0):
                strength += 0.1
                reasons.append(f"거래량 {context.volume_ratio:.1f}x")

            strength = min(strength, 1.0)

            if strength >= 0.4:
                sl_price = Decimal(str(
                    current_price + current_atr * self.get_param("sl_atr_mult", 1.5)
                )) if current_atr > 0 else None

                tp_price = Decimal(str(
                    current_price - current_atr * self.get_param("tp_atr_mult", 3.0)
                )) if current_atr > 0 else None

                if current_position == "long":
                    self._clear_position()
                    self._last_exit_bar = current_bar
                    return TradeSignal(
                        signal=SignalType.CLOSE, symbol=symbol,
                        strength=strength,
                        reason=" | ".join(reasons) + " → 롱 청산",
                    )

                if current_position == "short":
                    return hold

                self._entry_price = current_price
                self._entry_bar = current_bar
                self._position_side = "short"
                self._is_in_position = True

                return TradeSignal(
                    signal=SignalType.SHORT, symbol=symbol,
                    strength=strength,
                    reason="숏스퀴즈 반전: " + " | ".join(reasons),
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    amount_pct=min(strength * 0.6, 0.5),
                )

        return hold

    def _clear_position(self):
        """내부 포지션 상태 리셋"""
        self._entry_price = 0.0
        self._entry_bar = 0
        self._position_side = ""
        self._is_in_position = False
