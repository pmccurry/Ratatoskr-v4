"""Strategy module SQLAlchemy models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class Strategy(BaseModel):
    __tablename__ = "strategies"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="config")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    current_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    auto_pause_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_strategies_status", "status"),
        Index("ix_strategies_market_status", "market", "status"),
        Index("ix_strategies_user_id", "user_id"),
    )


class StrategyConfigVersion(BaseModel):
    """Versioned strategy configuration snapshot.

    Named StrategyConfigVersion to avoid collision with the module's
    StrategyConfig settings class in config.py.
    """

    __tablename__ = "strategy_configs"

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_strategy_configs_strategy_active", "strategy_id", "is_active"),
        UniqueConstraint("strategy_id", "version", name="uq_strategy_configs_strategy_version"),
    )


class StrategyState(BaseModel):
    __tablename__ = "strategy_states"

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class StrategyEvaluation(BaseModel):
    __tablename__ = "strategy_evaluations"

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbols_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_emitted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exits_triggered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_strategy_evaluations_strategy_at", "strategy_id", "evaluated_at"),
        Index("ix_strategy_evaluations_status", "status"),
    )


class PositionOverride(BaseModel):
    __tablename__ = "position_overrides"

    position_id: Mapped[UUID] = mapped_column(nullable=False)
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    override_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    override_value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_position_overrides_position_active", "position_id", "is_active"),
        Index("ix_position_overrides_strategy_id", "strategy_id"),
    )
