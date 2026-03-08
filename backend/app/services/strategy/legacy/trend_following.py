"""
심플 추세추종 전략 (Simple Trend Following)
- 20/50 EMA 교차 기반 진입
- RSI 확인 (과매수/과매도 제외)
- 트레일링 스탑으로 수익 극대화
- 저빈도 매매 (월 3~8회) → 소액 수수료 부담 적음
- 승률 낮지만 이길 때 크게 이기는 구조
"""

from decimal import Decimal

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy, TradeSignal, SignalType, MarketContext,
)
from app.services.strategy.indicators import closes, ema, rsi, atr


class TrendFollowingStrategy(BaseStrategy):
    """심플 추세추종 - EMA 교차 + RSI + 트레일링 스탑"""

    name = "trend_following"
    description = "추세추종 - EMA 교차, 트레일링 스탑으로 수익 극대화"
    min_candles = 60
    default_params = {
        "fast_ema": 10,                 # 빠른 EMA (20->10 더 빠른 반응)
        "slow_ema": 40,                 # 느린 EMA (50->40 교차 빈도 약간 증가)
        "rsi_period": 14,               # RSI 기간
        "rsi_long_min": 50,             # 롱 진입 RSI 하한
        "rsi_long_max": 70,             # 롱 진입 RSI 상한 (과매수 제외)
        "rsi_short_min": 30,            # 숏 진입 RSI 하한 (과매도 제외)
        "rsi_short_max": 50,            # 숏 진입 RSI 상한
        "atr_period": 14,               # ATR 기간
        "sl_atr_mult": 3.0,             # 손절 ATR 배수 (2->3, 넓은 손절이 핵심)
        "trail_activate_atr": 1.5,      # 트레일링 활성화 (2->1.5 ATR)
        "trail_offset_atr": 2.0,        # 트레일링 간격 (1.5->2.0 더 넓게 추적)
        "volume_lookback": 20,          # 거래량 비교 기간
        "position_size_pct": 0.4,       # 포지션 크기 (잔고의 40%)
        "cooldown_bars": 8,             # 쿨다운 (8시간 / 4h봉이면 2봉)
    }

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self._entry_price: float = 0.0
        self._entry_bar: int = 0
        self._position_side: str = ""
        self._is_in_position: bool = False
        self._last_exit_bar: int = -100
        self._trail_active: bool = False
        self._trail_stop: float = 0.0
        self._highest_since_entry: float = 0.0
        self._lowest_since_entry: float = float("inf")

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

        current_bar = len(candles) - 1
        close_prices = closes(candles)
        current_price = close_prices[-1]

        # --- 지표 계산 ---
        fast_period = int(self.get_param("fast_ema", 20))
        slow_period = int(self.get_param("slow_ema", 50))
        fast_ema_values = ema(close_prices, fast_period)
        slow_ema_values = ema(close_prices, slow_period)

        current_fast = fast_ema_values[-1]
        current_slow = slow_ema_values[-1]
        prev_fast = fast_ema_values[-2] if len(fast_ema_values) >= 2 else current_fast
        prev_slow = slow_ema_values[-2] if len(slow_ema_values) >= 2 else current_slow

        rsi_values = rsi(close_prices, int(self.get_param("rsi_period", 14)))
        current_rsi = rsi_values[-1]

        atr_values = atr(candles, int(self.get_param("atr_period", 14)))
        current_atr = atr_values[-1] if atr_values else 0

        # EMA 교차 감지
        golden_cross = prev_fast <= prev_slow and current_fast > current_slow
        death_cross = prev_fast >= prev_slow and current_fast < current_slow

        # 거래량 확인
        vol_ok = context and context.volume_ratio >= 1.0

        # --- 포지션 보유 중: 청산 로직 ---
        if self._is_in_position and current_position:
            return self._manage_position(
                symbol, current_bar, current_price, current_atr,
                current_fast, current_slow, death_cross, golden_cross,
            )

        # 외부 청산 감지
        if self._is_in_position and not current_position:
            self._clear_position()

        # --- 쿨다운 ---
        cooldown = int(self.get_param("cooldown_bars", 8))
        if current_bar - self._last_exit_bar < cooldown:
            return hold

        # --- 진입 조건 ---
        pos_size = self.get_param("position_size_pct", 0.4)

        # 롱 진입: 골든크로스 + 가격 > 50 EMA + RSI 50~70 + 거래량
        if golden_cross:
            rsi_min = self.get_param("rsi_long_min", 50)
            rsi_max = self.get_param("rsi_long_max", 70)

            if (current_price > current_slow
                    and rsi_min <= current_rsi <= rsi_max
                    and vol_ok):

                sl_price = current_price - current_atr * self.get_param("sl_atr_mult", 2.0)

                self._entry_price = current_price
                self._entry_bar = current_bar
                self._position_side = "long"
                self._is_in_position = True
                self._trail_active = False
                self._highest_since_entry = current_price
                self._lowest_since_entry = current_price

                if current_position == "short":
                    self._clear_position()
                    self._last_exit_bar = current_bar
                    # 재진입을 위해 entry 상태도 설정
                    self._entry_price = current_price
                    self._entry_bar = current_bar
                    self._position_side = "long"
                    self._is_in_position = True
                    return TradeSignal(
                        signal=SignalType.CLOSE, symbol=symbol,
                        strength=0.8,
                        reason=f"골든크로스 - 숏 청산 (RSI {current_rsi:.0f})",
                    )

                return TradeSignal(
                    signal=SignalType.LONG, symbol=symbol,
                    strength=0.7,
                    reason=f"골든크로스 | RSI {current_rsi:.0f} | 가격 > EMA50",
                    stop_loss=Decimal(str(round(sl_price, 2))),
                    amount_pct=pos_size,
                )

        # 숏 진입: 데드크로스 + 가격 < 50 EMA + RSI 30~50 + 거래량
        if death_cross:
            rsi_min = self.get_param("rsi_short_min", 30)
            rsi_max = self.get_param("rsi_short_max", 50)

            if (current_price < current_slow
                    and rsi_min <= current_rsi <= rsi_max
                    and vol_ok):

                sl_price = current_price + current_atr * self.get_param("sl_atr_mult", 2.0)

                self._entry_price = current_price
                self._entry_bar = current_bar
                self._position_side = "short"
                self._is_in_position = True
                self._trail_active = False
                self._highest_since_entry = current_price
                self._lowest_since_entry = current_price

                if current_position == "long":
                    self._clear_position()
                    self._last_exit_bar = current_bar
                    self._entry_price = current_price
                    self._entry_bar = current_bar
                    self._position_side = "short"
                    self._is_in_position = True
                    return TradeSignal(
                        signal=SignalType.CLOSE, symbol=symbol,
                        strength=0.8,
                        reason=f"데드크로스 - 롱 청산 (RSI {current_rsi:.0f})",
                    )

                return TradeSignal(
                    signal=SignalType.SHORT, symbol=symbol,
                    strength=0.7,
                    reason=f"데드크로스 | RSI {current_rsi:.0f} | 가격 < EMA50",
                    stop_loss=Decimal(str(round(sl_price, 2))),
                    amount_pct=pos_size,
                )

        return hold

    def _manage_position(
        self,
        symbol: str,
        current_bar: int,
        current_price: float,
        current_atr: float,
        current_fast: float,
        current_slow: float,
        death_cross: bool,
        golden_cross: bool,
    ) -> TradeSignal:
        """포지션 관리: 손절, 트레일링 스탑, 추세 종료 청산"""
        hold = TradeSignal(signal=SignalType.HOLD, symbol=symbol, reason="보유 중")

        if self._position_side == "long":
            price_change = (current_price - self._entry_price) / self._entry_price * 100
            self._highest_since_entry = max(self._highest_since_entry, current_price)
        else:
            price_change = (self._entry_price - current_price) / self._entry_price * 100
            self._lowest_since_entry = min(self._lowest_since_entry, current_price)

        sl_mult = self.get_param("sl_atr_mult", 2.0)
        trail_activate = self.get_param("trail_activate_atr", 2.0)
        trail_offset = self.get_param("trail_offset_atr", 1.5)

        # 1) 고정 손절 (ATR 기반)
        if self._position_side == "long":
            if current_price <= self._entry_price - current_atr * sl_mult:
                self._exit(current_bar)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=1.0,
                    reason=f"손절 {price_change:+.2f}% (ATR {sl_mult}x)",
                )
        else:
            if current_price >= self._entry_price + current_atr * sl_mult:
                self._exit(current_bar)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=1.0,
                    reason=f"손절 {price_change:+.2f}% (ATR {sl_mult}x)",
                )

        # 2) 트레일링 스탑
        if self._position_side == "long":
            profit_dist = self._highest_since_entry - self._entry_price
            if profit_dist >= current_atr * trail_activate:
                self._trail_active = True
                new_stop = self._highest_since_entry - current_atr * trail_offset
                self._trail_stop = max(self._trail_stop, new_stop)

            if self._trail_active and current_price <= self._trail_stop:
                self._exit(current_bar)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=0.9,
                    reason=f"트레일링 스탑 (최고 {self._highest_since_entry:.1f}, P/L {price_change:+.2f}%)",
                )
        else:
            profit_dist = self._entry_price - self._lowest_since_entry
            if profit_dist >= current_atr * trail_activate:
                self._trail_active = True
                new_stop = self._lowest_since_entry + current_atr * trail_offset
                if self._trail_stop == 0:
                    self._trail_stop = new_stop
                else:
                    self._trail_stop = min(self._trail_stop, new_stop)

            if self._trail_active and current_price >= self._trail_stop:
                self._exit(current_bar)
                return TradeSignal(
                    signal=SignalType.CLOSE, symbol=symbol,
                    strength=0.9,
                    reason=f"트레일링 스탑 (최저 {self._lowest_since_entry:.1f}, P/L {price_change:+.2f}%)",
                )

        # 3) 추세 종료 청산: EMA 역교차
        if self._position_side == "long" and death_cross:
            self._exit(current_bar)
            return TradeSignal(
                signal=SignalType.CLOSE, symbol=symbol,
                strength=0.8,
                reason=f"추세 종료 (데드크로스, P/L {price_change:+.2f}%)",
            )

        if self._position_side == "short" and golden_cross:
            self._exit(current_bar)
            return TradeSignal(
                signal=SignalType.CLOSE, symbol=symbol,
                strength=0.8,
                reason=f"추세 종료 (골든크로스, P/L {price_change:+.2f}%)",
            )

        return hold

    def _exit(self, bar: int):
        self._last_exit_bar = bar
        self._clear_position()

    def _clear_position(self):
        self._entry_price = 0.0
        self._entry_bar = 0
        self._position_side = ""
        self._is_in_position = False
        self._trail_active = False
        self._trail_stop = 0.0
        self._highest_since_entry = 0.0
        self._lowest_since_entry = float("inf")
