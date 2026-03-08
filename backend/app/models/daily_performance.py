"""
DailyPerformance ORM 모델
- 일일 성과 기록 (대시보드 차트용)
- 사용처: 일별 PnL 차트, 성과 분석
"""

from datetime import date
from decimal import Decimal
from sqlalchemy import Date, Integer, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.database import Base


class DailyPerformance(Base):
    __tablename__ = "daily_performance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id")
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    starting_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    ending_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    fees: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    funding: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    win_count: Mapped[int] = mapped_column(Integer, default=0)
    loss_count: Mapped[int] = mapped_column(Integer, default=0)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    __table_args__ = (
        UniqueConstraint("user_id", "strategy_id", "date"),
    )
