"""SQLAlchemy models for the market data module."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import BaseModel


class MarketSymbol(BaseModel):
    """Symbol metadata — exchange, base/quote asset, status."""

    __tablename__ = "market_symbols"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    base_asset: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quote_asset: Mapped[str | None] = mapped_column(String(20), nullable=True)
    broker: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    options_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("symbol", "market", "broker", name="uq_market_symbols_symbol_market_broker"),
        Index("ix_market_symbols_market_status", "market", "status"),
        Index("ix_market_symbols_broker_status", "broker", "status"),
    )


class WatchlistEntry(BaseModel):
    """Curated active watchlist with filter metadata."""

    __tablename__ = "watchlist_entries"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    broker: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filter_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_watchlist_entries_symbol_market_broker_status", "symbol", "market", "broker", "status"),
        Index("ix_watchlist_entries_status", "status"),
    )


class OHLCVBar(BaseModel):
    """OHLCV bar data — streamed and aggregated."""

    __tablename__ = "ohlcv_bars"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    is_aggregated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "ts", name="uq_ohlcv_bars_symbol_timeframe_ts"),
        Index("ix_ohlcv_bars_symbol_timeframe_ts", "symbol", "timeframe", "ts"),
    )


class BackfillJob(BaseModel):
    """Backfill job tracking and status."""

    __tablename__ = "backfill_jobs"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    bars_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_backfill_jobs_symbol_timeframe_status", "symbol", "timeframe", "status"),
        Index("ix_backfill_jobs_status", "status"),
    )


class DividendAnnouncement(BaseModel):
    """Dividend announcement data from broker corporate actions."""

    __tablename__ = "dividend_announcements"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    corporate_action_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ca_type: Mapped[str] = mapped_column(String(20), nullable=False)
    declaration_date: Mapped[date] = mapped_column(Date, nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    payable_date: Mapped[date] = mapped_column(Date, nullable=False)
    cash_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    stock_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="announced")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="alpaca")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_dividend_announcements_symbol_ex_date", "symbol", "ex_date"),
        Index("ix_dividend_announcements_ex_date", "ex_date"),
        Index("ix_dividend_announcements_payable_date", "payable_date"),
        Index("ix_dividend_announcements_status", "status"),
    )
