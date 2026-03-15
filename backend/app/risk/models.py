"""Risk module SQLAlchemy models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class RiskDecision(BaseModel):
    __tablename__ = "risk_decisions"

    signal_id: Mapped[UUID] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # approved | rejected | modified
    checks_passed: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    failed_check: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_text: Mapped[str] = mapped_column(String(500), nullable=False)
    modifications_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    portfolio_state_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_risk_decisions_status_created", "status", "created_at"),
        Index("ix_risk_decisions_reason_code", "reason_code"),
        Index("ix_risk_decisions_ts", "ts"),
    )


class KillSwitch(BaseModel):
    __tablename__ = "kill_switches"

    scope: Mapped[str] = mapped_column(String(20), nullable=False)  # global | strategy
    strategy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activated_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        Index("ix_kill_switches_scope_active", "scope", "is_active"),
        Index("ix_kill_switches_strategy_active", "strategy_id", "is_active"),
    )


class RiskConfig(BaseModel):
    __tablename__ = "risk_config"

    max_position_size_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("10.0"))
    max_symbol_exposure_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("20.0"))
    max_strategy_exposure_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("30.0"))
    max_total_exposure_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("80.0"))
    max_drawdown_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("10.0"))
    max_drawdown_catastrophic_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("20.0"))
    max_daily_loss_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("3.0"))
    max_daily_loss_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    min_position_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("100.0"))
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class RiskConfigAudit(BaseModel):
    __tablename__ = "risk_config_audit"

    field_changed: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str] = mapped_column(String(200), nullable=False)
    new_value: Mapped[str] = mapped_column(String(200), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_risk_config_audit_changed_at", "changed_at"),
    )
