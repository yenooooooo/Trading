"""
소액 포지션 사이징 모듈

핵심 원칙:
- 시드: $50 ~ $400 기준
- 레버리지: 최대 5x (하드 리밋), 권장 3x
- 단일 포지션 리스크: 총 자산의 3~5% (소액이라 2%는 너무 작음)
- 동시 포지션: 1개 (소액에서 분산은 의미 없음)
- 최소 주문 금액: 바이낸스 USDT-M 최소 $5
- 수수료 고려: 왕복 수수료를 반드시 차감

사용처: 전략 신호 → 실제 주문 수량 결정
"""

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import structlog

from app.services.strategy.fee_calculator import FeeCalculator, TAKER_FEE

logger = structlog.get_logger()


# --- 하드 리밋 ---
MAX_LEVERAGE = 5              # 절대 초과 불가
MIN_TRADE_USDT = Decimal("5") # 바이낸스 USDT-M 최소 주문


class SmallAccountPositionSizer:
    """
    소액 계좌($50~400) 전용 포지션 사이징

    메서드:
    1. calculate_position_size() — 잔고·리스크·손절 기반 수량 계산
    2. validate_order() — 주문 유효성 검증
    3. calculate_breakeven_move() — 손익분기 가격 변동 계산
    4. get_recommended_settings() — 잔고 구간별 권장 설정
    """

    def __init__(self, fee_calculator: FeeCalculator | None = None):
        self.fee_calc = fee_calculator or FeeCalculator()

    # --- 1. 포지션 크기 계산 ---

    def calculate_position_size(
        self,
        balance: Decimal,
        risk_percent: float,
        stop_loss_percent: float,
        leverage: int = 3,
        entry_price: Decimal | None = None,
    ) -> dict:
        """
        잔고·리스크·손절 기반 포지션 사이징

        Args:
            balance: 사용 가능 잔고 ($)
            risk_percent: 리스크 비율 (예: 0.04 = 4%)
            stop_loss_percent: 손절폭 (예: 0.02 = 2%)
            leverage: 레버리지 (하드 리밋 5x)
            entry_price: 진입 가격 (코인 수량 계산용, 없으면 생략)

        Returns:
            size_usdt: 포지션 명목 가치 ($)
            size_contracts: 코인 수량 (entry_price 필요)
            leverage: 적용 레버리지
            margin_required: 필요 증거금
            risk_amount: 최대 손실 금액
            min_profit_to_breakeven: 손익분기 최소 수익률 (%)
        """
        # 레버리지 하드 리밋
        leverage = min(leverage, MAX_LEVERAGE)

        # 리스크 금액 = 잔고 × 리스크 비율
        risk_amount = (balance * Decimal(str(risk_percent))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 포지션 명목 가치 = 리스크 금액 / 손절폭
        if stop_loss_percent <= 0:
            logger.warning("invalid_stop_loss", stop_loss_percent=stop_loss_percent)
            return self._empty_result(leverage)

        size_usdt = (risk_amount / Decimal(str(stop_loss_percent))).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        # 최대 포지션 제한: 잔고 × 레버리지
        max_size = balance * leverage
        size_usdt = min(size_usdt, max_size)

        # 최소 주문 체크
        if size_usdt < MIN_TRADE_USDT:
            logger.info("below_min_trade", size=str(size_usdt))
            return self._empty_result(leverage)

        # 필요 증거금
        margin_required = (size_usdt / leverage).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 손익분기 계산
        breakeven = self.calculate_breakeven_move(size_usdt, leverage)

        # 코인 수량 (entry_price 있을 때)
        size_contracts = Decimal("0")
        if entry_price and entry_price > 0:
            size_contracts = (size_usdt / entry_price).quantize(
                Decimal("0.00001"), rounding=ROUND_DOWN
            )

        return {
            "size_usdt": size_usdt,
            "size_contracts": size_contracts,
            "leverage": leverage,
            "margin_required": margin_required,
            "risk_amount": risk_amount,
            "min_profit_to_breakeven": breakeven,
        }

    # --- 2. 주문 유효성 검증 ---

    def validate_order(
        self,
        balance: Decimal,
        size_usdt: Decimal,
        leverage: int = 3,
    ) -> dict:
        """
        주문 유효성 검증

        Returns:
            valid: 주문 가능 여부
            reason: 거부 사유 (valid=False일 때)
            warnings: 경고 목록 (valid=True여도 주의사항)
        """
        warnings: list[str] = []

        # 1) 레버리지 하드 리밋
        if leverage > MAX_LEVERAGE:
            return {
                "valid": False,
                "reason": f"레버리지 초과: {leverage}x > 최대 {MAX_LEVERAGE}x",
                "warnings": [],
            }

        # 2) 최소 주문 금액
        if size_usdt < MIN_TRADE_USDT:
            return {
                "valid": False,
                "reason": f"최소 주문 금액 미달: ${size_usdt} < ${MIN_TRADE_USDT}",
                "warnings": [],
            }

        # 3) 필요 증거금 + 수수료 체크
        margin = size_usdt / leverage
        fees = self.fee_calc.calculate_round_trip_fee(size_usdt)
        required = margin + fees["total_fee"]

        if required > balance:
            return {
                "valid": False,
                "reason": f"잔고 부족: 필요 ${required:.2f} (증거금 ${margin:.2f} + 수수료 ${fees['total_fee']}), 보유 ${balance:.2f}",
                "warnings": [],
            }

        # 4) 과도한 포지션 경고 (잔고의 80% 이상 사용)
        usage_pct = float(required / balance) * 100
        if usage_pct > 80:
            warnings.append(f"잔고의 {usage_pct:.0f}%를 사용합니다 (위험)")
        elif usage_pct > 60:
            warnings.append(f"잔고의 {usage_pct:.0f}%를 사용합니다 (주의)")

        # 5) 레버리지 경고
        if leverage >= 5:
            warnings.append(f"최대 레버리지 {leverage}x — 청산 위험 높음")
        elif leverage >= 4:
            warnings.append(f"레버리지 {leverage}x — 변동성 주의")

        # 6) 소액 경고
        if balance < Decimal("50"):
            warnings.append("잔고 $50 미만 — 수수료 비중 높음")

        return {
            "valid": True,
            "reason": "OK",
            "warnings": warnings,
        }

    # --- 3. 손익분기 가격 움직임 ---

    def calculate_breakeven_move(
        self,
        size_usdt: Decimal,
        leverage: int = 3,
        fee_rate: float = 0.0004,
    ) -> float:
        """
        왕복 수수료를 커버하는 최소 가격 움직임 (%)

        예: taker 0.04% → 왕복 0.08%
        레버리지 3x → 실제 가격 0.08% 움직이면 수익 0.24% (>0.08% 커버)
        → 최소 가격 움직임 = 왕복수수료% (레버리지는 수익을 증폭하므로)
        """
        round_trip_pct = fee_rate * 2 * 100  # %
        return round(round_trip_pct, 4)

    # --- 4. 잔고 구간별 권장 설정 ---

    def get_recommended_settings(self, balance: Decimal) -> dict:
        """
        잔고 구간별 권장 설정

        Returns:
            leverage: 권장 레버리지
            risk_percent: 권장 리스크 비율
            max_positions: 동시 최대 포지션 수
            max_daily_trades: 일 최대 거래 횟수
            description: 구간 설명
        """
        bal = float(balance)

        if bal < 50:
            return {
                "leverage": 2,
                "risk_percent": 0.05,
                "max_positions": 1,
                "max_daily_trades": 1,
                "description": "극소액 — 최소 레버리지, 거래 최소화",
            }
        elif bal < 100:
            return {
                "leverage": 3,
                "risk_percent": 0.05,
                "max_positions": 1,
                "max_daily_trades": 2,
                "description": "$50~100 — 보수적 운용, 수수료 비중 주의",
            }
        elif bal < 200:
            return {
                "leverage": 3,
                "risk_percent": 0.04,
                "max_positions": 1,
                "max_daily_trades": 2,
                "description": "$100~200 — 안정적 운용, 레버리지 3x 권장",
            }
        elif bal < 400:
            return {
                "leverage": 3,
                "risk_percent": 0.03,
                "max_positions": 1,
                "max_daily_trades": 3,
                "description": "$200~400 — 적정 운용, 포지션 분산 가능",
            }
        else:
            return {
                "leverage": 5,
                "risk_percent": 0.03,
                "max_positions": 2,
                "max_daily_trades": 3,
                "description": "$400+ — 표준 운용, 레버리지 3~5x",
            }

    # --- 내부 헬퍼 ---

    def _empty_result(self, leverage: int) -> dict:
        """빈 결과 (주문 불가 시)"""
        return {
            "size_usdt": Decimal("0"),
            "size_contracts": Decimal("0"),
            "leverage": leverage,
            "margin_required": Decimal("0"),
            "risk_amount": Decimal("0"),
            "min_profit_to_breakeven": 0.0,
        }


# --- 모듈 레벨 편의 함수 (기존 호환) ---

_default_sizer = None


def _get_sizer() -> SmallAccountPositionSizer:
    global _default_sizer
    if _default_sizer is None:
        _default_sizer = SmallAccountPositionSizer()
    return _default_sizer


def calc_position_size(
    balance: Decimal,
    entry_price: Decimal,
    stop_loss_price: Decimal,
    leverage: int = 1,
    risk_pct: float = 0.03,
) -> Decimal:
    """포지션 수량 계산 (편의 함수)"""
    if entry_price <= 0 or stop_loss_price <= 0:
        return Decimal("0")
    sl_pct = float(abs(entry_price - stop_loss_price) / entry_price)
    if sl_pct == 0:
        return Decimal("0")
    result = _get_sizer().calculate_position_size(
        balance, risk_pct, sl_pct, leverage, entry_price
    )
    return result["size_contracts"]


def calc_safe_leverage(balance: Decimal, volatility_pct: float) -> int:
    """계좌 크기·변동성 기반 안전 레버리지 (편의 함수)"""
    settings = _get_sizer().get_recommended_settings(balance)
    base_lev = settings["leverage"]

    # 변동성 보정
    if volatility_pct > 5.0:
        base_lev = max(1, base_lev // 3)
    elif volatility_pct > 3.0:
        base_lev = max(1, base_lev // 2)

    return min(base_lev, MAX_LEVERAGE)


def validate_order(
    balance: Decimal,
    notional: Decimal,
    leverage: int = 1,
) -> tuple[bool, str]:
    """주문 유효성 검증 (편의 함수)"""
    result = _get_sizer().validate_order(balance, notional, leverage)
    return result["valid"], result["reason"]
