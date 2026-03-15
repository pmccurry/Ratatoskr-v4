"""Portfolio module SQLAlchemy models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class Position(BaseModel):
    __tablename__ = "positions"

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    unrealized_pnl_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_dividends_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_return: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_return_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    highest_price_since_entry: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    lowest_price_since_entry: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    bars_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    broker_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    underlying_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_multiplier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_positions_strategy_status", "strategy_id", "status"),
        Index("ix_positions_symbol_status", "symbol", "status"),
        Index("ix_positions_status", "status"),
        Index("ix_positions_strategy_symbol_status", "strategy_id", "symbol", "status"),
        Index("ix_positions_user_status", "user_id", "status"),
        Index(
            "ix_positions_broker_account_status",
            "broker_account_id", "status",
            postgresql_where="broker_account_id IS NOT NULL",
        ),
        Index(
            "ix_positions_expiration_date",
            "expiration_date",
            postgresql_where="expiration_date IS NOT NULL",
        ),
    )


class CashBalance(BaseModel):
    __tablename__ = "cash_balances"

    account_scope: Mapped[str] = mapped_column(String(50), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("account_scope", "user_id", name="uq_cash_balance_scope_user"),
    )


class PortfolioMeta(BaseModel):
    __tablename__ = "portfolio_meta"

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("key", "user_id", name="uq_portfolio_meta_key_user"),
    )


class PortfolioSnapshot(BaseModel):
    __tablename__ = "portfolio_snapshots"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    positions_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl_today: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    dividend_income_today: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    dividend_income_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    drawdown_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    peak_equity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    open_positions_count: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_portfolio_snapshots_ts", "ts"),
        Index("ix_portfolio_snapshots_type_ts", "snapshot_type", "ts"),
        Index("ix_portfolio_snapshots_user_ts", "user_id", "ts"),
    )


class RealizedPnlEntry(BaseModel):
    __tablename__ = "realized_pnl_entries"

    position_id: Mapped[UUID] = mapped_column(
        ForeignKey("positions.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    qty_closed: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    gross_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    pnl_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    holding_period_bars: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_realized_pnl_entries_strategy_closed", "strategy_id", "closed_at"),
        Index("ix_realized_pnl_entries_symbol_closed", "symbol", "closed_at"),
        Index("ix_realized_pnl_entries_closed_at", "closed_at"),
        Index("ix_realized_pnl_entries_user_closed", "user_id", "closed_at"),
    )


class DividendPayment(BaseModel):
    __tablename__ = "dividend_payments"

    position_id: Mapped[UUID] = mapped_column(
        ForeignKey("positions.id", ondelete="CASCADE"), nullable=False
    )
    announcement_id: Mapped[UUID] = mapped_column(
        ForeignKey("dividend_announcements.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    payable_date: Mapped[date] = mapped_column(Date, nullable=False)
    shares_held: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    amount_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_dividend_payments_position", "position_id"),
        Index("ix_dividend_payments_user_payable", "user_id", "payable_date"),
        Index("ix_dividend_payments_status", "status"),
    )


class SplitAdjustment(BaseModel):
    __tablename__ = "split_adjustments"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    split_type: Mapped[str] = mapped_column(String(20), nullable=False)
    old_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    new_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    positions_adjusted: Mapped[int] = mapped_column(Integer, nullable=False)
    adjustments_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_split_adjustments_symbol_date", "symbol", "effective_date"),
    )
