"""Signal module Pydantic schemas for API request/response."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SignalResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: UUID
    strategy_id: UUID
    strategy_version: str
    symbol: str
    market: str
    timeframe: str
    side: str
    signal_type: str
    source: str
    confidence: Decimal | None
    status: str
    payload_json: dict | None
    position_id: UUID | None
    exit_reason: str | None
    ts: datetime
    expires_at: datetime | None
    created_at: datetime


class SignalStatsResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    total: int
    by_status: dict[str, int]
    by_strategy: dict[str, int]
    by_symbol: dict[str, int]
    by_signal_type: dict[str, int]
    by_source: dict[str, int]


class SignalQueryParams(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    strategy_id: UUID | None = None
    symbol: str | None = None
    status: str | None = None
    signal_type: str | None = None
    source: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    page: int = 1
    page_size: int = 20
