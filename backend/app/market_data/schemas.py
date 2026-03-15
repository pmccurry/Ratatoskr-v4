"""Pydantic request/response schemas for the market data module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# === Response Schemas ===


class MarketSymbolResponse(BaseModel):
    """Market symbol metadata response."""

    id: UUID
    symbol: str
    name: str
    market: str
    exchange: str | None = None
    base_asset: str | None = Field(None, alias="baseAsset")
    quote_asset: str | None = Field(None, alias="quoteAsset")
    broker: str
    status: str
    options_enabled: bool = Field(alias="optionsEnabled")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class WatchlistEntryResponse(BaseModel):
    """Watchlist entry response."""

    id: UUID
    symbol: str
    market: str
    broker: str
    status: str
    added_at: datetime = Field(alias="addedAt")
    removed_at: datetime | None = Field(None, alias="removedAt")
    filter_metadata_json: dict | None = Field(None, alias="filterMetadataJson")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class OHLCVBarResponse(BaseModel):
    """OHLCV bar response with Decimal fields serialized as strings."""

    id: UUID
    symbol: str
    market: str
    timeframe: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source: str
    is_aggregated: bool = Field(alias="isAggregated")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class BackfillJobResponse(BaseModel):
    """Backfill job status response."""

    id: UUID
    symbol: str
    market: str
    timeframe: str
    start_date: datetime = Field(alias="startDate")
    end_date: datetime = Field(alias="endDate")
    status: str
    bars_fetched: int = Field(alias="barsFetched")
    started_at: datetime | None = Field(None, alias="startedAt")
    completed_at: datetime | None = Field(None, alias="completedAt")
    error_message: str | None = Field(None, alias="errorMessage")
    retry_count: int = Field(alias="retryCount")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DividendAnnouncementResponse(BaseModel):
    """Dividend announcement response."""

    id: UUID
    symbol: str
    corporate_action_id: str = Field(alias="corporateActionId")
    ca_type: str = Field(alias="caType")
    declaration_date: date = Field(alias="declarationDate")
    ex_date: date = Field(alias="exDate")
    record_date: date = Field(alias="recordDate")
    payable_date: date = Field(alias="payableDate")
    cash_amount: Decimal = Field(alias="cashAmount")
    stock_rate: Decimal | None = Field(None, alias="stockRate")
    status: str
    source: str
    created_at: datetime = Field(alias="createdAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class MarketDataHealthResponse(BaseModel):
    """Market data health status response."""

    overall_status: str = Field(alias="overallStatus")
    connections: dict
    stale_symbols: list[str] = Field(alias="staleSymbols")
    write_pipeline: dict = Field(alias="writePipeline")
    backfill: dict

    model_config = {"populate_by_name": True}


# === Query/Filter Schemas ===


class BarQueryParams(BaseModel):
    """Query parameters for bar data requests."""

    symbol: str
    timeframe: str
    limit: int = Field(default=200, ge=1, le=10000)
    start: datetime | None = None
    end: datetime | None = None


class WatchlistQueryParams(BaseModel):
    """Query parameters for watchlist requests."""

    market: str | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}
