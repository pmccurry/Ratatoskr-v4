"""Signal module SQLAlchemy models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class Signal(BaseModel):
    __tablename__ = "signals"

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    position_id: Mapped[UUID | None] = mapped_column(nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_signals_strategy_created", "strategy_id", "created_at"),
        Index("ix_signals_symbol_created", "symbol", "created_at"),
        Index("ix_signals_status", "status"),
        Index("ix_signals_strategy_symbol_status", "strategy_id", "symbol", "status"),
    )
