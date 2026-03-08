"""
거래소 수수료 정밀 계산기
- 바이낸스 USDT-M 선물 수수료 구조 기반
- 왕복 수수료 + 펀딩비 포함 실질 순수익 계산
- 사용처: 포지션 사이징, 전략 신호 필터링, 손익분기 계산
"""

from decimal import Decimal, ROUND_HALF_UP
import structlog

logger = structlog.get_logger()


# --- 바이낸스 선물 수수료율 (일반 등급, VIP 0) ---
MAKER_FEE = Decimal("0.0002")      # 0.02%
TAKER_FEE = Decimal("0.0004")      # 0.04%
MAKER_FEE_BNB = Decimal("0.00018") # 0.018% (BNB 할인)
TAKER_FEE_BNB = Decimal("0.00036") # 0.036% (BNB 할인)


class FeeCalculator:
    """
    거래소 수수료 정밀 계산기

    기능:
    1. 진입/청산 수수료 개별 계산 (maker/taker)
    2. 왕복 수수료 합산
    3. 펀딩비 예상 비용 (8시간마다 발생)
    4. 수수료 차감 후 실질 순수익
    5. 손익분기 최소 움직임 계산
    """

    def __init__(self, use_bnb_discount: bool = False):
        if use_bnb_discount:
            self.maker_fee = MAKER_FEE_BNB
            self.taker_fee = TAKER_FEE_BNB
        else:
            self.maker_fee = MAKER_FEE
            self.taker_fee = TAKER_FEE

    def _get_fee_rate(self, order_type: str) -> Decimal:
        """주문 유형별 수수료율 반환"""
        return self.maker_fee if order_type == "maker" else self.taker_fee

    # --- 1. 왕복 수수료 계산 ---

    def calculate_round_trip_fee(
        self,
        position_size_usdt: Decimal,
        entry_type: str = "taker",
        exit_type: str = "taker",
    ) -> dict:
        """
        왕복 수수료 계산 (진입 + 청산)

        Args:
            position_size_usdt: 포지션 명목 가치 ($)
            entry_type: 진입 주문 유형 ('maker' | 'taker')
            exit_type: 청산 주문 유형 ('maker' | 'taker')

        Returns:
            entry_fee, exit_fee, total_fee, total_fee_pct
        """
        entry_rate = self._get_fee_rate(entry_type)
        exit_rate = self._get_fee_rate(exit_type)

        entry_fee = (position_size_usdt * entry_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        exit_fee = (position_size_usdt * exit_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_fee = entry_fee + exit_fee
        total_fee_pct = float(entry_rate + exit_rate) * 100

        return {
            "entry_fee": entry_fee,
            "exit_fee": exit_fee,
            "total_fee": total_fee,
            "total_fee_pct": round(total_fee_pct, 4),
        }

    # --- 2. 펀딩비 비용 계산 ---

    def calculate_funding_cost(
        self,
        position_size_usdt: Decimal,
        funding_rate: float,
        holding_hours: float,
    ) -> Decimal:
        """
        펀딩비 예상 비용 계산

        - 8시간마다 1회 부과
        - funding_rate > 0: 롱이 숏에게 지급
        - funding_rate < 0: 숏이 롱에게 지급

        Args:
            position_size_usdt: 포지션 명목 가치
            funding_rate: 펀딩비 (예: 0.0001 = 0.01%)
            holding_hours: 예상 보유 시간

        Returns:
            예상 펀딩비 비용 (양수=지출, 음수=수입)
        """
        # 8시간마다 1회 → 보유 시간 / 8 = 횟수
        funding_periods = int(holding_hours / 8)
        if funding_periods <= 0:
            return Decimal("0")

        cost_per_period = position_size_usdt * Decimal(str(funding_rate))
        total_cost = (cost_per_period * funding_periods).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return total_cost

    # --- 3. 실질 순수익 계산 ---

    def calculate_net_profit(
        self,
        gross_profit: Decimal,
        position_size_usdt: Decimal,
        entry_type: str = "taker",
        exit_type: str = "taker",
        funding_rate: float = 0.0,
        holding_hours: float = 0.0,
    ) -> dict:
        """
        수수료·펀딩비 차감 후 실질 순수익

        Returns:
            gross_profit, total_fee, funding_cost, net_profit, net_profit_pct
        """
        fees = self.calculate_round_trip_fee(
            position_size_usdt, entry_type, exit_type
        )
        funding_cost = self.calculate_funding_cost(
            position_size_usdt, funding_rate, holding_hours
        )

        net_profit = gross_profit - fees["total_fee"] - funding_cost

        # 투입 증거금 대비 수익률 (레버리지 반영 전)
        net_profit_pct = (
            float(net_profit / position_size_usdt) * 100
            if position_size_usdt > 0 else 0.0
        )

        return {
            "gross_profit": gross_profit,
            "total_fee": fees["total_fee"],
            "funding_cost": funding_cost,
            "net_profit": net_profit,
            "net_profit_pct": round(net_profit_pct, 4),
        }

    # --- 4. 손익분기 최소 움직임 ---

    def get_min_profitable_move(
        self,
        position_size_usdt: Decimal,
        leverage: int = 1,
        entry_type: str = "taker",
        exit_type: str = "taker",
    ) -> float:
        """
        수수료를 커버하는 최소 가격 움직임 (%)

        예: $200 시드, 3x 레버리지, taker 0.04%
        → 왕복 0.08% → 가격이 0.08% 이상 움직여야 본전
        """
        entry_rate = float(self._get_fee_rate(entry_type))
        exit_rate = float(self._get_fee_rate(exit_type))
        round_trip_pct = (entry_rate + exit_rate) * 100
        return round(round_trip_pct, 4)

    # --- 5. 수익성 판단 ---

    def is_profitable_signal(
        self,
        expected_move_pct: float,
        leverage: int = 1,
        min_rr_ratio: float = 1.5,
    ) -> bool:
        """
        신호가 수수료 대비 수익성 있는지 판단

        Args:
            expected_move_pct: 예상 가격 변동 (%)
            leverage: 레버리지 배수
            min_rr_ratio: 최소 위험보상비 (기본 1.5)
        """
        breakeven = self.get_min_profitable_move(
            Decimal("1000"), leverage  # 비율 계산이므로 금액 무관
        )
        return expected_move_pct >= breakeven * min_rr_ratio


# --- 모듈 레벨 편의 함수 (기존 호환) ---

_default_calc = FeeCalculator()


def calc_fee(notional: Decimal, is_maker: bool = False) -> Decimal:
    """단일 수수료 계산"""
    rate = MAKER_FEE if is_maker else TAKER_FEE
    return notional * rate


def calc_round_trip_fee(notional: Decimal, is_maker: bool = False) -> Decimal:
    """왕복 수수료 계산"""
    return calc_fee(notional, is_maker) * 2


def calc_breakeven_pct(leverage: int = 1, is_maker: bool = False) -> float:
    """손익분기 변동률 (%)"""
    rate = float(MAKER_FEE if is_maker else TAKER_FEE)
    return rate * 2 * 100  # 왕복


def is_profitable_signal(
    expected_move_pct: float,
    leverage: int = 1,
    is_maker: bool = False,
    min_rr_ratio: float = 1.5,
) -> bool:
    """수수료 대비 수익성 판단 (편의 함수)"""
    breakeven = calc_breakeven_pct(leverage, is_maker)
    return expected_move_pct >= breakeven * min_rr_ratio
