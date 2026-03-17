"""Backtesting module SQLAlchemy models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class BacktestRun(BaseModel):
    __tablename__ = "backtest_runs"

    strategy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    strategy_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="conditions"
    )  # "conditions" or "python"
    strategy_file: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # filename for python strategies
    strategy_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    symbols: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=Decimal("100000")
    )
    position_sizing: Mapped[dict] = mapped_column(JSONB, nullable=False)
    exit_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    bars_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_backtest_runs_strategy_id", "strategy_id"),
        Index("ix_backtest_runs_status", "status"),
    )


class BacktestTrade(BaseModel):
    __tablename__ = "backtest_trades"

    backtest_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    entry_bar_index: Mapped[int] = mapped_column(Integer, nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    exit_bar_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    pnl_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    fees: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    hold_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_favorable: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    max_adverse: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    __table_args__ = (
        Index("ix_backtest_trades_backtest_id", "backtest_id"),
    )


class BacktestEquityPoint(BaseModel):
    __tablename__ = "backtest_equity_curve"

    backtest_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bar_index: Mapped[int] = mapped_column(Integer, nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    open_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal("0")
    )
    drawdown_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0")
    )

    __table_args__ = (
        Index("ix_backtest_equity_curve_backtest_id", "backtest_id"),
        Index("ix_backtest_equity_curve_backtest_bar", "backtest_id", "bar_index"),
    )
