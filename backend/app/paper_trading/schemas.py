"""Paper trading module Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PaperOrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    signal_id: UUID
    risk_decision_id: UUID
    strategy_id: UUID
    symbol: str
    market: str
    side: str
    order_type: str
    signal_type: str
    requested_qty: Decimal
    requested_price: Decimal | None
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    status: str
    rejection_reason: str | None
    execution_mode: str
    broker_order_id: str | None
    broker_account_id: str | None
    underlying_symbol: str | None
    contract_type: str | None
    strike_price: Decimal | None
    expiration_date: date | None
    contract_multiplier: int
    submitted_at: datetime
    accepted_at: datetime | None
    filled_at: datetime | None
    created_at: datetime


class PaperFillResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    order_id: UUID
    strategy_id: UUID
    symbol: str
    side: str
    qty: Decimal
    reference_price: Decimal
    price: Decimal
    gross_value: Decimal
    fee: Decimal
    slippage_bps: Decimal
    slippage_amount: Decimal
    net_value: Decimal
    broker_fill_id: str | None
    broker_account_id: str | None
    filled_at: datetime
    created_at: datetime


class OrderQueryParams(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    strategy_id: UUID | None = None
    symbol: str | None = None
    status: str | None = None
    signal_type: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    page: int = 1
    page_size: int = 20


class FillQueryParams(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    strategy_id: UUID | None = None
    symbol: str | None = None
    side: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    page: int = 1
    page_size: int = 20


class ShadowPositionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    strategy_id: UUID
    symbol: str
    side: str
    qty: Decimal
    avg_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    status: str
    stop_loss_price: Decimal | None
    take_profit_price: Decimal | None
    trailing_stop_price: Decimal | None
    highest_price_since_entry: Decimal | None
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None
    entry_signal_id: UUID
    exit_signal_id: UUID | None
    created_at: datetime


class ShadowFillResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    signal_id: UUID
    strategy_id: UUID
    symbol: str
    side: str
    qty: Decimal
    reference_price: Decimal
    price: Decimal
    fee: Decimal
    slippage_bps: Decimal
    gross_value: Decimal
    net_value: Decimal
    fill_type: str
    shadow_position_id: UUID
    filled_at: datetime
    created_at: datetime


class PoolStatusResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    accounts: list[dict]
    pair_capacity: dict
    total_accounts: int
    fully_empty: int


class ShadowComparisonResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    strategy_id: UUID
    strategy_name: str
    real_trades: int
    real_pnl: Decimal
    real_win_rate: Decimal
    shadow_trades: int
    shadow_pnl: Decimal
    shadow_win_rate: Decimal
    blocked_signals: int
    missed_pnl: Decimal


class BrokerAccountResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    broker: str
    account_id: str
    account_type: str
    label: str
    is_active: bool
    capital_allocation: Decimal
    created_at: datetime
