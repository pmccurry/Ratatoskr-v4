"""Market data API endpoints."""

import math

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.common.database import get_db
from app.common.schemas import PaginationMeta
from app.market_data.repository import (
    BackfillJobRepository,
    DividendAnnouncementRepository,
    MarketSymbolRepository,
    OHLCVBarRepository,
    WatchlistRepository,
)
from app.market_data.schemas import (
    BackfillJobResponse,
    DividendAnnouncementResponse,
    MarketSymbolResponse,
    OHLCVBarResponse,
    WatchlistEntryResponse,
)
from app.market_data.service import MarketDataService

router = APIRouter(
    prefix="/market-data",
    tags=["Market Data"],
)

_symbol_repo = MarketSymbolRepository()
_watchlist_repo = WatchlistRepository()
_bar_repo = OHLCVBarRepository()
_backfill_repo = BackfillJobRepository()
_dividend_repo = DividendAnnouncementRepository()
_service = MarketDataService()


@router.get("/health")
async def get_health(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get market data health status."""
    health = await _service.get_health(db)
    return {"data": health}


@router.get("/symbols")
async def list_symbols(
    market: str | None = Query(None),
    status: str = Query("active"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List known market symbols with metadata."""
    symbols = await _symbol_repo.get_all(db, market=market, status=status)
    return {
        "data": [
            MarketSymbolResponse.model_validate(s).model_dump(by_alias=True)
            for s in symbols
        ]
    }


@router.get("/watchlist")
async def get_watchlist(
    market: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get paginated watchlist."""
    entries, total = await _watchlist_repo.get_paginated(
        db, market=market, status=status, page=page, page_size=page_size
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return {
        "data": [
            WatchlistEntryResponse.model_validate(e).model_dump(by_alias=True)
            for e in entries
        ],
        "pagination": PaginationMeta(
            page=page,
            pageSize=page_size,
            totalItems=total,
            totalPages=total_pages,
        ).model_dump(by_alias=True),
    }


@router.get("/bars")
async def get_bars(
    symbol: str = Query(...),
    timeframe: str = Query(...),
    limit: int = Query(200, ge=1, le=10000),
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Query OHLCV bars for a symbol and timeframe."""
    from datetime import datetime

    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    bars = await _bar_repo.get_bars(
        db, symbol=symbol, timeframe=timeframe, limit=limit, start=start_dt, end=end_dt
    )
    return {
        "data": [
            OHLCVBarResponse.model_validate(b).model_dump(by_alias=True)
            for b in bars
        ]
    }


@router.get("/backfill/status")
async def get_backfill_status(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get backfill job status."""
    jobs = await _backfill_repo.get_all(db, status=status)
    return {
        "data": [
            BackfillJobResponse.model_validate(j).model_dump(by_alias=True)
            for j in jobs
        ]
    }


@router.get("/dividends")
async def get_dividends(
    symbol: str | None = Query(None),
    days_ahead: int = Query(30, ge=1, le=365, alias="daysAhead"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get upcoming dividend announcements."""
    announcements = await _dividend_repo.get_upcoming(db, symbol=symbol, days_ahead=days_ahead)
    return {
        "data": [
            DividendAnnouncementResponse.model_validate(a).model_dump(by_alias=True)
            for a in announcements
        ]
    }


@router.get("/options/chain/{symbol}")
async def get_option_chain(
    symbol: str = Path(...),
    _current_user: User = Depends(get_current_user),
):
    """Fetch option chain for an underlying symbol."""
    chain = await _service.get_option_chain(symbol)
    return {"data": chain}


@router.post("/backfill/trigger")
async def trigger_backfill(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    """Trigger a backfill job (admin only)."""
    result = await _service.run_backfill(db)
    return {"data": result}


@router.post("/watchlist/refresh")
async def refresh_watchlist(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    """Trigger universe filter refresh (admin only)."""
    result = await _service.run_universe_filter(db)
    return {"data": result}
