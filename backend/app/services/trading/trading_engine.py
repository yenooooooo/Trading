"""
트레이딩 엔진
- 전략 신호 → 리스크 검증 → 주문 실행 파이프라인
- 모든 주문은 반드시 RiskManager를 통과
- 사용처: 전략 스케줄러에서 호출
"""

from decimal import Decimal
import structlog

from app.services.exchange.base import (
    ExchangeConnector,
    OrderResult,
    PositionInfo,
)
from app.services.strategy.base_strategy import TradeSignal, SignalType
from app.services.risk.risk_manager import SmallAccountRiskManager, RiskCheckResult

logger = structlog.get_logger()


class TradingEngine:
    """매매 실행 엔진 (리스크 매니저 통합)"""

    def __init__(
        self,
        connector: ExchangeConnector,
        risk_manager: SmallAccountRiskManager | None = None,
    ):
        self.connector = connector
        self.risk_manager = risk_manager or SmallAccountRiskManager()

        # 당일 거래 추적
        self._today_trades: list[dict] = []
        self._today_pnl: float = 0.0
        self._week_pnl: float = 0.0
        self._recent_trades: list[dict] = []

    # --- 신호 실행 ---

    async def execute_signal(
        self,
        signal: TradeSignal,
        leverage: int = 1,
        max_position_pct: float = 0.1,
    ) -> OrderResult | None:
        """
        매매 신호를 주문으로 변환하여 실행

        Args:
            signal: 전략에서 생성한 매매 신호
            leverage: 레버리지 배수
            max_position_pct: 잔고 대비 최대 포지션 비율
        """
        if signal.signal == SignalType.HOLD:
            return None

        # 포지션 종료 (리스크 체크 없이 허용)
        if signal.signal == SignalType.CLOSE:
            return await self._close_position(signal.symbol)

        # 포지션 진입 (리스크 체크 필수)
        return await self._open_position(
            signal=signal,
            leverage=leverage,
            max_position_pct=max_position_pct,
        )

    # --- 포지션 진입 ---

    async def _open_position(
        self,
        signal: TradeSignal,
        leverage: int,
        max_position_pct: float,
    ) -> OrderResult | None:
        """새 포지션 진입 (리스크 검증 포함)"""
        try:
            # 잔고 조회
            balance = await self.connector.get_balance()
            available = float(balance.available)

            if available <= 0:
                logger.warning("insufficient_balance", available=available)
                return None

            # 포지션 크기 계산 (잔고 × 비율 × 레버리지)
            position_value = available * max_position_pct * signal.amount_pct
            current_price = float(
                (await self.connector.get_ticker(signal.symbol)).price
            )

            if current_price <= 0:
                return None

            position_size_usdt = Decimal(str(position_value * leverage))
            side = "long" if signal.signal == SignalType.LONG else "short"

            # --- 리스크 검증 ---
            open_positions = await self.connector.get_all_positions()
            expected_profit = signal.strength * 2.0  # 강도 기반 예상 수익률 (%)

            risk_result: RiskCheckResult = await self.risk_manager.validate_order(
                balance=Decimal(str(available)),
                position_size_usdt=position_size_usdt,
                leverage=leverage,
                side=side,
                expected_profit_pct=expected_profit,
                open_positions=open_positions,
                today_trades=self._today_trades,
                today_pnl=self._today_pnl,
                week_pnl=self._week_pnl,
                recent_trades=self._recent_trades,
            )

            if not risk_result.approved:
                logger.warning(
                    "order_rejected_by_risk",
                    reason=risk_result.reason,
                    symbol=signal.symbol,
                    side=side,
                )
                return None

            # 경고 로깅
            for w in risk_result.warnings:
                logger.info("risk_warning", warning=w)

            # 포지션 크기 조정 (연속 손실 시)
            if risk_result.adjusted_size is not None:
                position_size_usdt = risk_result.adjusted_size
                logger.info(
                    "position_size_reduced",
                    adjusted=str(position_size_usdt),
                )

            amount = Decimal(str(float(position_size_usdt) / current_price))

            logger.info(
                "opening_position",
                symbol=signal.symbol,
                side=side,
                amount=str(amount),
                leverage=leverage,
                reason=signal.reason,
            )

            # 시장가 주문
            result = await self.connector.place_order(
                symbol=signal.symbol,
                side="buy" if side == "long" else "sell",
                order_type="market",
                amount=amount,
            )

            # 거래 기록 추가
            self._today_trades.append({
                "symbol": signal.symbol,
                "side": side,
                "size": str(position_size_usdt),
            })

            logger.info(
                "position_opened",
                order_id=result.order_id,
                status=result.status,
            )
            return result

        except Exception as e:
            logger.error("open_position_failed", error=str(e))
            return None

    # --- 포지션 종료 ---

    async def _close_position(self, symbol: str) -> OrderResult | None:
        """현재 포지션 종료 (반대 방향 시장가 주문)"""
        try:
            position = await self.connector.get_position(symbol)
            if not position:
                logger.info("no_position_to_close", symbol=symbol)
                return None

            # 반대 방향으로 같은 수량 주문
            close_side = "sell" if position.side == "long" else "buy"

            logger.info(
                "closing_position",
                symbol=symbol,
                side=close_side,
                size=str(position.size),
            )

            result = await self.connector.place_order(
                symbol=symbol,
                side=close_side,
                order_type="market",
                amount=position.size,
                params={"reduceOnly": True},
            )

            logger.info(
                "position_closed",
                order_id=result.order_id,
                status=result.status,
            )
            return result

        except Exception as e:
            logger.error("close_position_failed", error=str(e))
            return None

    # --- PnL 업데이트 (외부에서 호출) ---

    def update_pnl(self, trade_pnl: float):
        """거래 완료 후 PnL 업데이트"""
        self._today_pnl += trade_pnl
        self._week_pnl += trade_pnl
        self._recent_trades.append({"pnl": trade_pnl})
        # 최근 10거래만 유지
        if len(self._recent_trades) > 10:
            self._recent_trades = self._recent_trades[-10:]

    def reset_daily(self):
        """일일 리셋 (자정에 호출)"""
        self._today_trades = []
        self._today_pnl = 0.0

    def reset_weekly(self):
        """주간 리셋 (월요일에 호출)"""
        self._week_pnl = 0.0

    # --- 포지션 조회 ---

    async def get_position(self, symbol: str) -> PositionInfo | None:
        """현재 포지션 조회"""
        return await self.connector.get_position(symbol)

    async def get_all_positions(self) -> list[PositionInfo]:
        """모든 활성 포지션 조회"""
        return await self.connector.get_all_positions()
