"""
ExchangeKey ORM 모델
- 거래소 API 키 (AES-256 암호화 저장)
- 사용처: 거래소 연동, 주문 실행
"""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.core.database import Base


class ExchangeKey(Base):
    __tablename__ = "exchange_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    passphrase_encrypted: Mapped[str | None] = mapped_column(String)
    label: Mapped[str | None] = mapped_column(String(100))
    permissions: Mapped[dict] = mapped_column(
        JSONB, default=lambda: {"trade": True, "withdraw": False}
    )
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
