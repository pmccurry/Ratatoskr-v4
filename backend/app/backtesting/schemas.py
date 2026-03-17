"""Backtest request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PythonBacktestRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbols: list[str] | None = None
    timeframe: str | None = None
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000
    position_sizing: dict | None = None
    parameter_overrides: dict | None = None


class BacktestRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbols: list[str]
    timeframe: str = "1h"
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("100000")
    position_sizing: dict = Field(default_factory=lambda: {"type": "fixed", "amount": 10000})
    exit_config: dict = Field(default_factory=dict)


class BacktestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    strategy_id: UUID | None = None
    status: str
    strategy_type: str = "conditions"
    strategy_file: str | None = None
    symbols: list
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    position_sizing: dict
    exit_config: dict
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    metrics: dict | None = None
    bars_processed: int | None = None
    total_trades: int | None = None
    error: str | None = None
    created_at: datetime | None = None


class BacktestTradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    backtest_id: UUID
    symbol: str
    side: str
    quantity: Decimal
    entry_time: datetime
    entry_price: Decimal
    entry_bar_index: int
    exit_time: datetime | None = None
    exit_price: Decimal | None = None
    exit_bar_index: int | None = None
    exit_reason: str | None = None
    pnl: Decimal | None = None
    pnl_percent: Decimal | None = None
    fees: Decimal | None = None
    hold_bars: int | None = None
    max_favorable: Decimal | None = None
    max_adverse: Decimal | None = None


class BacktestEquityPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    bar_time: datetime
    bar_index: int
    equity: Decimal
    cash: Decimal
    open_positions: int
    unrealized_pnl: Decimal
    drawdown_pct: Decimal
