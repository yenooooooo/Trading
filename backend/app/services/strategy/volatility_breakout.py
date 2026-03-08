"""
변동성 돌파 전략 v4
- 2단계 진입: 스퀴즈 감지 -> 방향 확인 후 진입
- 일봉 EMA 추세 필터: 일봉 20 EMA 방향과 같은 방향만 진입
- 스퀴즈 품질 필터: BB 폭이 100봉 중 하위 20%일 때만 유효
- 최소 수익 필터: 예상 수익 > 왕복 수수료 x 3
- 거짓 돌파 방지 + 12시간 쿨다운
- 트레일링 스탑: 1 ATR 수익 후 0.7 ATR 추적
- 목표 거래 빈도: 30~50회 / 90일
"""

from decimal import Decimal

from app.services.exchange.base import Candle
from app.services.strategy.base_strategy import (
    BaseStrategy, TradeSignal, SignalType, MarketContext,
)
from app.services.strategy.indicators import closes, atr, ema, bollinger_bands
from app.services.strategy.fee_calculator import calc_breakeven_pct


class VolatilityBreakoutStrategy(BaseStrategy):
    """변동성 돌파 전략 - 2단계 진입 + 다중 필터"""

    name = "volatility_breakout"
    description = "변동성 돌파 - 스퀴즈 후 확인 진입, 추세/수익성 필터"
    min_candles = 100
    default_params = {
        "k_factor": 0.5,                # 돌파 계수
        "atr_period": 14,               # ATR 기간
        "sl_atr_mult": 1.5,             # 손절 ATR 배수
        "tp_atr_mult": 2.0,             # 익절 ATR 배수
        "trail_activate_atr": 1.0,      # 트레일링 활성화 ATR 배수
        "trail_offset_atr": 0.7,        # 트레일링 간격 ATR 배수
        "fast_ema_period": 20,          # 빠른 EMA
        "daily_ema_period": 20,         # 일봉 추세 EMA (24봉 = 1일)
        "bb_period": 20,                # 볼린저 밴드 기간
        "bb_std": 2.0,                  # 볼린저 밴드 표준편차
        "volume_confirm": 1.7,          # 거래량 확인 배수
        "atr_squeeze_ratio": 0.9,       # ATR 수축 비율
        "bb_squeeze_percentile": 20,    # BB 폭 하위 N% 필터
        "confirm_bars": 2,              # 방향 확인 봉 수
        "fakeout_check_bars": 3,        # 거짓 돌파 체크 봉 수
        "cooldown_bars": 12,            # 쿨다운 (12시간)
        "min_profit_mult": 3.0,         # 예상 수익 >= 수수료 x N
        "position_size_pct": 0.5,       # 포지션 크기
    }

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self._last_exit_bar: int = -100
        self._squeeze_detected: bool = False
        self._squeeze_bar: int = -100
        self._entry_price: float = 0.0
        self._entry_bar: int = 0
        self._position_side: str = ""
        self._is_in_position: bool = False
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
        current_price = float(candles[-1].close)
        close_prices = closes(candles)

        # --- 지표 계산 ---
        atr_period = int(self.get_param("atr_period", 14))
        atr_values = atr(candles, atr_period)
        current_atr = atr_values[-1] if atr_values else 0

        bb_period = int(self.get_param("bb_period", 20))
        bb_std = self.get_param("bb_std", 2.0)
        bb_upper, bb_mid, bb_lower = bollinger_bands(close_prices, bb_period, bb_std)

        # 일봉 추세 필터: 24봉 단위 EMA로 일봉 추세 근사
        daily_ema_period = int(self.get_param("daily_ema_period", 20))
        # 24봉(=1일) x daily_ema_period = 일봉 EMA를 시간봉으로 환산
        long_ema_period = min(daily_ema_period * 24, len(close_prices) - 1)
        if long_ema_period < 48:
            long_ema_period = 48  # 최소 2일
        long_ema_values = ema(close_prices, long_ema_period)
        daily_trend_up = len(long_ema_values) >= 2 and long_ema_values[-1] > long_ema_values[-2]
        daily_trend_down = len(long_ema_values) >= 2 and long_ema_values[-1] < long_ema_values[-2]

        # --- 포지션 보유 중: 청산 로직 ---
        if self._is_in_position and current_position:
            return self._manage_position(
                symbol, candles, current_bar, current_price,
                current_atr, bb_upper, bb_lower,
            )

        if self._is_in_position and not current_position:
            self._clear_position()

        # --- 쿨다운 ---
        cooldown = int(self.get_param("cooldown_bars", 12))
        if current_bar - self._last_exit_bar < cooldown:
            return hold

        # --- ATR 스퀴즈 감지 ---
        atr_squeeze = self.get_param("atr_squeeze_ratio", 0.9)
        if len(atr_values) >= 20:
            avg_atr = sum(atr_values[-20:]) / 20
            atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
        else:
            atr_ratio = 1.0

        # --- BB 스퀴즈 품질 필터 ---
        bb_squeeze_ok = False
        if len(bb_upper) >= 100 and len(bb_lower) >= 100:
            bb_widths = [bb_upper[i] - bb_lower[i] for i in range(-100, 0)]
            current_width = bb_upper[-1] - bb_lower[-1]
            sorted_widths = sorted(bb_widths)
            percentile = self.get_param("bb_squeeze_percentile", 20)
            threshold_idx = max(int(len(sorted_widths) * percentile / 100) - 1, 0)
            bb_squeeze_ok = current_width <= sorted_widths[threshold_idx]
        elif len(bb_upper) >= 20:
            # 데이터 부족 시 ATR 스퀴즈만으로 판단
            bb_squeeze_ok = atr_ratio <= atr_squeeze

        # 스퀴즈 감지
        if atr_ratio <= atr_squeeze and bb_squeeze_ok and not self._squeeze_detected:
            self._squeeze_detected = True
            self._squeeze_bar = current_bar
            return hold

        # 스퀴즈 후 30봉 대기 초과 -> 리셋
        if self._squeeze_detected and current_bar - self._squeeze_bar > 30:
            self._squeeze_detected = False

        if not self._squeeze_detected:
            return hold

        # --- 2단계: 방향 확인 진입 ---
        confirm_bars = int(self.get_param("confirm_bars", 2))
        if current_bar - self._squeeze_bar < confirm_bars:
            return hold

        confirm_long = self._check_confirm_bars(candles, "long")
        confirm_short = self._check_confirm_bars(candles, "short")
        vol_ok = context and context.volume_ratio >= self.get_param("volume_confirm", 1.7)

        # --- 최소 수익 필터 ---
        min_profit_mult = self.get_param("min_profit_mult", 3.0)
        breakeven_pct = calc_breakeven_pct(leverage=1)  # 왕복 수수료 %
        expected_move_pct = (current_atr / current_price * 100) * self.get_param("tp_atr_mult", 2.0)
        if expected_move_pct < breakeven_pct * min_profit_mult:
            return hold

        # 롱 진입: 스퀴즈 + 연속 양봉 + 일봉 추세 상승
        if confirm_long and daily_trend_up and vol_ok:
            self._squeeze_detected = False
            return self._enter_long(
                symbol, current_price, current_atr, current_bar,
                f"스퀴즈 돌파 | 일봉 추세 상승 | 거래량 {context.volume_ratio:.1f}x",
            )

        # 숏 진입
        if confirm_short and daily_trend_down and vol_ok:
            self._squeeze_detected = False
            return self._enter_short(
                symbol, current_price, current_atr, current_bar,
                f"스퀴즈 돌파 | 일봉 추세 하락 | 거래량 {context.volume_ratio:.1f}x",
            )

        return hold

    def _check_confirm_bars(self, candles: list[Candle], direction: str) -> bool:
        """연속 N봉 같은 방향 확인"""
        n = int(self.get_param("confirm_bars", 2))
        if len(candles) < n + 1:
            return False
        for i in range(-n, 0):
            c = candles[i]
            if direction == "long" and float(c.close) <= float(c.open):
                return False
            if direction == "short" and float(c.close) >= float(c.open):
                return False
        return True

    def _enter_long(self, symbol, price, atr_val, bar, reason):
        sl_mult = self.get_param("sl_atr_mult", 1.5)
        tp_mult = self.get_param("tp_atr_mult", 2.0)
        self._entry_price = price
        self._entry_bar = bar
        self._position_side = "long"
        self._is_in_position = True
        self._trail_active = False
        self._highest_since_entry = price
        self._lowest_since_entry = price
        return TradeSignal(
            signal=SignalType.LONG, symbol=symbol, strength=0.7, reason=reason,
            stop_loss=Decimal(str(price - atr_val * sl_mult)),
            take_profit=Decimal(str(price + atr_val * tp_mult)),
            amount_pct=self.get_param("position_size_pct", 0.5),
        )

    def _enter_short(self, symbol, price, atr_val, bar, reason):
        sl_mult = self.get_param("sl_atr_mult", 1.5)
        tp_mult = self.get_param("tp_atr_mult", 2.0)
        self._entry_price = price
        self._entry_bar = bar
        self._position_side = "short"
        self._is_in_position = True
        self._trail_active = False
        self._highest_since_entry = price
        self._lowest_since_entry = price
        return TradeSignal(
            signal=SignalType.SHORT, symbol=symbol, strength=0.7, reason=reason,
            stop_loss=Decimal(str(price + atr_val * sl_mult)),
            take_profit=Decimal(str(price - atr_val * tp_mult)),
            amount_pct=self.get_param("position_size_pct", 0.5),
        )

    def _manage_position(self, symbol, candles, current_bar, current_price, current_atr, bb_upper, bb_lower):
        """포지션 관리: 손절, 거짓돌파, 트레일링, 익절"""
        hold = TradeSignal(signal=SignalType.HOLD, symbol=symbol, reason="보유 중")

        if self._position_side == "long":
            price_change = (current_price - self._entry_price) / self._entry_price * 100
            self._highest_since_entry = max(self._highest_since_entry, current_price)
        else:
            price_change = (self._entry_price - current_price) / self._entry_price * 100
            self._lowest_since_entry = min(self._lowest_since_entry, current_price)

        bars_held = current_bar - self._entry_bar
        sl_mult = self.get_param("sl_atr_mult", 1.5)
        tp_mult = self.get_param("tp_atr_mult", 2.0)

        # 1) 고정 손절
        sl_dist = current_atr * sl_mult
        if self._position_side == "long" and current_price <= self._entry_price - sl_dist:
            self._exit(current_bar)
            return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=1.0,
                             reason=f"손절 {price_change:+.2f}% (ATR {sl_mult}x)")
        if self._position_side == "short" and current_price >= self._entry_price + sl_dist:
            self._exit(current_bar)
            return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=1.0,
                             reason=f"손절 {price_change:+.2f}% (ATR {sl_mult}x)")

        # 2) 거짓 돌파: 3봉 이내 BB 복귀 -> 즉시 청산 + 12시간 쿨다운
        fakeout_bars = int(self.get_param("fakeout_check_bars", 3))
        if 1 <= bars_held <= fakeout_bars:
            if self._position_side == "long" and bb_upper and current_price < bb_upper[-1]:
                self._exit(current_bar)
                return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=0.9,
                                 reason=f"거짓 돌파 ({bars_held}봉, {price_change:+.2f}%)")
            if self._position_side == "short" and bb_lower and current_price > bb_lower[-1]:
                self._exit(current_bar)
                return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=0.9,
                                 reason=f"거짓 돌파 ({bars_held}봉, {price_change:+.2f}%)")

        # 3) 트레일링 스탑
        trail_activate = self.get_param("trail_activate_atr", 1.0)
        trail_offset = self.get_param("trail_offset_atr", 0.7)

        if self._position_side == "long":
            profit_dist = self._highest_since_entry - self._entry_price
            if profit_dist >= current_atr * trail_activate:
                self._trail_active = True
                self._trail_stop = max(
                    self._trail_stop,
                    self._highest_since_entry - current_atr * trail_offset,
                )
            if self._trail_active and current_price <= self._trail_stop:
                self._exit(current_bar)
                return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=0.8,
                                 reason=f"트레일링 스탑 (P/L {price_change:+.2f}%)")
        else:
            profit_dist = self._entry_price - self._lowest_since_entry
            if profit_dist >= current_atr * trail_activate:
                self._trail_active = True
                new_stop = self._lowest_since_entry + current_atr * trail_offset
                self._trail_stop = min(self._trail_stop, new_stop) if self._trail_stop > 0 else new_stop
            if self._trail_active and current_price >= self._trail_stop:
                self._exit(current_bar)
                return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=0.8,
                                 reason=f"트레일링 스탑 (P/L {price_change:+.2f}%)")

        # 4) 고정 익절 (트레일링 미활성)
        if not self._trail_active:
            tp_dist = current_atr * tp_mult
            if self._position_side == "long" and current_price >= self._entry_price + tp_dist:
                self._exit(current_bar)
                return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=1.0,
                                 reason=f"익절 {price_change:+.2f}% (ATR {tp_mult}x)")
            if self._position_side == "short" and current_price <= self._entry_price - tp_dist:
                self._exit(current_bar)
                return TradeSignal(signal=SignalType.CLOSE, symbol=symbol, strength=1.0,
                                 reason=f"익절 {price_change:+.2f}% (ATR {tp_mult}x)")

        return hold

    def _exit(self, bar):
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
        self._squeeze_detected = False
