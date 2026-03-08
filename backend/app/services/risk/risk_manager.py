"""
소액 전용 리스크 관리 엔진
- $50~400 계좌에 최적화된 리스크 규칙
- 모든 주문은 반드시 이 매니저를 통과해야 함
- 사용처: TradingEngine에서 주문 실행 전 호출
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import structlog

from app.services.strategy.fee_calculator import FeeCalculator

logger = structlog.get_logger()


# --- 리스크 체크 결과 ---

@dataclass
class RiskCheckResult:
    """리스크 검증 결과"""
    approved: bool = False
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    adjusted_size: Decimal | None = None   # 축소된 포지션 크기 (None이면 원래 크기)
    adjusted_leverage: int | None = None   # 축소된 레버리지


# --- 소액 리스크 설정 ---

@dataclass
class RiskConfig:
    """리스크 한도 설정"""
    # 포지션 리스크
    max_risk_per_trade: float = 0.05       # 1회 최대 리스크 5%
    min_risk_per_trade: float = 0.03       # 1회 최소 리스크 3%

    # 손실 한도
    daily_loss_limit: float = 0.08         # 일일 손실 한도 8%
    weekly_loss_limit: float = 0.15        # 주간 손실 한도 15%

    # 레버리지
    max_leverage: int = 5                  # 최대 레버리지 (하드 리밋)

    # 포지션 수
    max_positions_small: int = 1           # $200 이하: 동시 1개
    max_positions_medium: int = 2          # $200~400: 동시 2개
    position_threshold: float = 200.0      # 구간 기준

    # 거래 빈도
    max_daily_trades: int = 3              # 일일 최대 거래 횟수

    # 연속 손실
    consecutive_loss_reduce: int = 3       # 3연패 → 포지션 50% 축소
    consecutive_loss_stop: int = 5         # 5연패 → 당일 매매 중단
    reduce_factor: float = 0.5            # 축소 비율

    # 수수료 대비 수익
    min_profit_fee_ratio: float = 2.0      # 예상 수익 >= 왕복 수수료 × 2


class SmallAccountRiskManager:
    """
    소액 계좌 전용 리스크 매니저

    규칙:
    1. 단일 포지션 리스크 3~5%
    2. 일일 손실 한도 8%
    3. 주간 손실 한도 15%
    4. 최대 레버리지 5x
    5. 동시 포지션 1~2개 (잔고 기준)
    6. 일일 최대 거래 3회
    7. 3연패 → 50% 축소, 5연패 → 매매 중단
    8. 수수료 대비 수익 2배 이상
    """

    def __init__(
        self,
        config: RiskConfig | None = None,
        fee_calculator: FeeCalculator | None = None,
    ):
        self.config = config or RiskConfig()
        self.fee_calc = fee_calculator or FeeCalculator()

    # --- 1. 주문 전 종합 리스크 검증 ---

    async def validate_order(
        self,
        balance: Decimal,
        position_size_usdt: Decimal,
        leverage: int,
        side: str,
        expected_profit_pct: float,
        open_positions: list,
        today_trades: list,
        today_pnl: float,
        week_pnl: float,
        recent_trades: list,
    ) -> RiskCheckResult:
        """
        주문 전 리스크 검증 — 통과 못하면 주문 거부

        Args:
            balance: 현재 잔고
            position_size_usdt: 포지션 명목 가치
            leverage: 요청 레버리지
            side: 'long' | 'short'
            expected_profit_pct: 예상 수익률 (%)
            open_positions: 현재 열린 포지션 목록
            today_trades: 오늘 거래 목록
            today_pnl: 오늘 누적 손익 ($)
            week_pnl: 이번 주 누적 손익 ($)
            recent_trades: 최근 거래 (연속 손실 체크용)
        """
        warnings: list[str] = []

        # 1) 레버리지 하드 리밋
        if leverage > self.config.max_leverage:
            return RiskCheckResult(
                approved=False,
                reason=f"레버리지 초과: {leverage}x > 최대 {self.config.max_leverage}x",
            )

        # 2) 일일 손실 한도
        daily_ok = await self.check_daily_limit(float(balance), today_pnl)
        if not daily_ok:
            return RiskCheckResult(
                approved=False,
                reason=f"일일 손실 한도 초과: ${abs(today_pnl):.2f} (한도 {self.config.daily_loss_limit*100}%)",
            )

        # 3) 주간 손실 한도
        weekly_ok = await self.check_weekly_limit(float(balance), week_pnl)
        if not weekly_ok:
            return RiskCheckResult(
                approved=False,
                reason=f"주간 손실 한도 초과: ${abs(week_pnl):.2f} (한도 {self.config.weekly_loss_limit*100}%)",
            )

        # 4) 일일 거래 횟수
        if len(today_trades) >= self.config.max_daily_trades:
            return RiskCheckResult(
                approved=False,
                reason=f"일일 거래 한도 초과: {len(today_trades)}회 (한도 {self.config.max_daily_trades}회)",
            )

        # 5) 동시 포지션 수
        max_pos = (
            self.config.max_positions_medium
            if float(balance) > self.config.position_threshold
            else self.config.max_positions_small
        )
        if len(open_positions) >= max_pos:
            return RiskCheckResult(
                approved=False,
                reason=f"동시 포지션 한도 초과: {len(open_positions)}개 (한도 {max_pos}개)",
            )

        # 6) 연속 손실 체크
        consec_result = await self.check_consecutive_losses(recent_trades)
        if consec_result["action"] == "stop":
            return RiskCheckResult(
                approved=False,
                reason=f"연속 {consec_result['count']}연패 — 당일 매매 중단",
            )

        # 7) 수수료 대비 수익 체크
        fee_ok = await self.check_fee_worthiness(
            expected_profit_pct, float(position_size_usdt), leverage
        )
        if not fee_ok:
            return RiskCheckResult(
                approved=False,
                reason="예상 수익이 왕복 수수료의 2배 미만 — 수익성 부족",
            )

        # 8) 포지션 크기 검증
        margin_required = position_size_usdt / leverage
        fee = self.fee_calc.calculate_round_trip_fee(position_size_usdt)
        total_required = margin_required + fee["total_fee"]

        if total_required > balance:
            return RiskCheckResult(
                approved=False,
                reason=f"잔고 부족: 필요 ${total_required:.2f}, 보유 ${balance:.2f}",
            )

        # 9) 최대 리스크 비율 체크
        risk_pct = float(margin_required / balance)
        if risk_pct > self.config.max_risk_per_trade:
            warnings.append(
                f"포지션 비율 {risk_pct*100:.1f}% > 권장 {self.config.max_risk_per_trade*100}%"
            )

        # --- 포지션 크기 조정 (연속 손실 시) ---
        adjusted_size = None
        if consec_result["action"] == "reduce":
            adjusted_size = self.get_adjusted_position_size(
                position_size_usdt, consec_result["count"]
            )
            warnings.append(
                f"연속 {consec_result['count']}연패 — 포지션 {self.config.reduce_factor*100:.0f}% 축소"
            )

        # 소액 경고
        if float(balance) < 50:
            warnings.append("잔고 $50 미만 — 수수료 비중 높음, 거래 최소화 권장")

        return RiskCheckResult(
            approved=True,
            reason="OK",
            warnings=warnings,
            adjusted_size=adjusted_size,
        )

    # --- 2. 일일 손실 한도 ---

    async def check_daily_limit(self, balance: float, today_pnl: float) -> bool:
        """
        일일 손실 한도 체크
        - today_pnl < 0이고 |today_pnl| > balance × daily_loss_limit → 매매 중단
        """
        if today_pnl >= 0:
            return True
        limit = balance * self.config.daily_loss_limit
        return abs(today_pnl) < limit

    # --- 3. 주간 손실 한도 ---

    async def check_weekly_limit(self, balance: float, week_pnl: float) -> bool:
        """
        주간 손실 한도 체크
        - 초과 시 1주일 쿨다운 권고
        """
        if week_pnl >= 0:
            return True
        limit = balance * self.config.weekly_loss_limit
        return abs(week_pnl) < limit

    # --- 4. 연속 손실 체크 ---

    async def check_consecutive_losses(self, recent_trades: list) -> dict:
        """
        연속 손실 체크

        Returns:
            count: 연속 손실 횟수
            action: 'none' | 'reduce' | 'stop'
        """
        if not recent_trades:
            return {"count": 0, "action": "none"}

        consecutive = 0
        for trade in reversed(recent_trades):
            pnl = trade.get("pnl", 0) if isinstance(trade, dict) else getattr(trade, "pnl_net", 0)
            if pnl < 0:
                consecutive += 1
            else:
                break

        if consecutive >= self.config.consecutive_loss_stop:
            return {"count": consecutive, "action": "stop"}
        elif consecutive >= self.config.consecutive_loss_reduce:
            return {"count": consecutive, "action": "reduce"}
        else:
            return {"count": consecutive, "action": "none"}

    # --- 5. 수수료 대비 수익 체크 ---

    async def check_fee_worthiness(
        self,
        expected_profit_pct: float,
        position_size_usdt: float,
        leverage: int,
    ) -> bool:
        """
        수수료 대비 수익성 체크
        - 예상 수익 >= 왕복 수수료 × min_profit_fee_ratio
        """
        # 왕복 수수료 (%)
        fee_pct = self.fee_calc.get_min_profitable_move(
            Decimal(str(position_size_usdt)), leverage
        )
        min_required = fee_pct * self.config.min_profit_fee_ratio
        return expected_profit_pct >= min_required

    # --- 6. 연속 손실 포지션 축소 ---

    def get_adjusted_position_size(
        self,
        base_size: Decimal,
        consecutive_losses: int,
    ) -> Decimal:
        """
        연속 손실에 따른 포지션 크기 조절
        - 3연패: 50% 축소
        - 4연패: 50% 축소 유지
        """
        if consecutive_losses >= self.config.consecutive_loss_reduce:
            return Decimal(str(
                float(base_size) * self.config.reduce_factor
            )).quantize(Decimal("0.01"))
        return base_size
