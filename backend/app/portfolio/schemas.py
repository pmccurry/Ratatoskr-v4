"""Portfolio module Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PositionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    strategy_id: UUID
    symbol: str
    market: str
    side: str
    qty: Decimal
    avg_entry_price: Decimal
    cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    realized_pnl: Decimal
    total_fees: Decimal
    total_dividends_received: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    status: str
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None
    highest_price_since_entry: Decimal
    lowest_price_since_entry: Decimal
    bars_held: int
    broker_account_id: str | None
    contract_multiplier: int
    created_at: datetime


class PortfolioSummaryResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    equity: Decimal
    cash: Decimal
    positions_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl_total: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    drawdown_percent: Decimal
    peak_equity: Decimal
    open_positions_count: int


class CashBalanceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    account_scope: str
    balance: Decimal


class EquityBreakdownResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_equity: Decimal
    total_cash: Decimal
    total_positions_value: Decimal
    equities_cash: Decimal
    equities_positions_value: Decimal
    forex_cash: Decimal
    forex_positions_value: Decimal


class PositionQueryParams(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    strategy_id: UUID | None = None
    symbol: str | None = None
    status: str | None = None
    market: str | None = None
    page: int = 1
    page_size: int = 20


class PortfolioSnapshotResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    ts: datetime
    cash_balance: Decimal
    positions_value: Decimal
    equity: Decimal
    unrealized_pnl: Decimal
    realized_pnl_today: Decimal
    realized_pnl_total: Decimal
    dividend_income_today: Decimal
    dividend_income_total: Decimal
    drawdown_percent: Decimal
    peak_equity: Decimal
    open_positions_count: int
    snapshot_type: str
    created_at: datetime


class RealizedPnlEntryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    position_id: UUID
    strategy_id: UUID
    symbol: str
    market: str
    side: str
    qty_closed: Decimal
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl: Decimal
    fees: Decimal
    net_pnl: Decimal
    pnl_percent: Decimal
    holding_period_bars: int
    closed_at: datetime
    created_at: datetime


class DividendPaymentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    position_id: UUID
    symbol: str
    ex_date: date
    payable_date: date
    shares_held: Decimal
    amount_per_share: Decimal
    gross_amount: Decimal
    net_amount: Decimal
    status: str
    paid_at: datetime | None
    created_at: datetime


class PnlSummaryResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    today: Decimal
    this_week: Decimal
    this_month: Decimal
    total: Decimal
    by_strategy: dict
    by_symbol: dict


class DividendSummaryResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    today: Decimal
    this_month: Decimal
    this_year: Decimal
    total: Decimal
    by_symbol: dict


class PerformanceMetricsResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_return: Decimal
    total_return_percent: Decimal
    total_pnl: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    average_winner: Decimal
    average_loser: Decimal
    risk_reward_ratio: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    average_hold_bars: Decimal
    longest_win_streak: int
    longest_loss_streak: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_fees: Decimal
    total_dividend_income: Decimal


class CashAdjustRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    account_scope: str
    amount: Decimal
    reason: str
