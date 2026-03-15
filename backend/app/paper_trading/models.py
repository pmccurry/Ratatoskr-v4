"""Paper trading module SQLAlchemy models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class PaperOrder(BaseModel):
    __tablename__ = "paper_orders"

    signal_id: Mapped[UUID] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    risk_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("risk_decisions.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, default="market")
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    requested_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    filled_qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("0"))
    filled_avg_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="simulation")
    broker_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    underlying_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_multiplier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_paper_orders_strategy_created", "strategy_id", "created_at"),
        Index("ix_paper_orders_symbol_status", "symbol", "status"),
        Index("ix_paper_orders_status", "status"),
        Index(
            "ix_paper_orders_broker_order_id",
            "broker_order_id",
            postgresql_where="broker_order_id IS NOT NULL",
        ),
    )


class PaperFill(BaseModel):
    __tablename__ = "paper_fills"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("paper_orders.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    gross_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    slippage_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    broker_fill_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_paper_fills_order_id", "order_id"),
        Index("ix_paper_fills_strategy_filled", "strategy_id", "filled_at"),
        Index("ix_paper_fills_symbol_filled", "symbol", "filled_at"),
    )


class BrokerAccount(BaseModel):
    __tablename__ = "broker_accounts"

    broker: Mapped[str] = mapped_column(String(20), nullable=False, default="oanda")
    account_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default="paper_virtual")
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capital_allocation: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    credentials_env_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_broker_accounts_broker_active", "broker", "is_active"),
    )


class AccountAllocation(BaseModel):
    __tablename__ = "account_allocations"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_account_allocations_account_symbol_status", "account_id", "symbol", "status"),
        Index("ix_account_allocations_strategy_status", "strategy_id", "status"),
        Index("ix_account_allocations_symbol_status", "symbol", "status"),
    )


class ShadowPosition(BaseModel):
    __tablename__ = "shadow_positions"

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    stop_loss_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    take_profit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    trailing_stop_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    highest_price_since_entry: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    entry_signal_id: Mapped[UUID] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), nullable=False
    )
    exit_signal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_shadow_positions_strategy_status", "strategy_id", "status"),
        Index("ix_shadow_positions_symbol_status", "symbol", "status"),
    )


class ShadowFill(BaseModel):
    __tablename__ = "shadow_fills"

    signal_id: Mapped[UUID] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    gross_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fill_type: Mapped[str] = mapped_column(String(10), nullable=False)
    shadow_position_id: Mapped[UUID] = mapped_column(
        ForeignKey("shadow_positions.id", ondelete="CASCADE"), nullable=False
    )
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_shadow_fills_strategy_filled", "strategy_id", "filled_at"),
        Index("ix_shadow_fills_position", "shadow_position_id"),
    )
