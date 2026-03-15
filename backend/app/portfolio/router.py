"""Portfolio module API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.common.database import get_db
from app.portfolio.schemas import (
    CashAdjustRequest,
    CashBalanceResponse,
    DividendPaymentResponse,
    DividendSummaryResponse,
    EquityBreakdownResponse,
    PerformanceMetricsResponse,
    PnlSummaryResponse,
    PortfolioSnapshotResponse,
    PortfolioSummaryResponse,
    PositionResponse,
    RealizedPnlEntryResponse,
)
from app.portfolio.startup import get_portfolio_service

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)


# --- Positions ---


@router.get("/positions", response_model=dict)
async def list_positions(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    symbol: str | None = Query(None),
    status: str | None = Query(None),
    market: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List positions with filters."""
    service = get_portfolio_service()
    if not service:
        return {"data": [], "total": 0, "page": page, "pageSize": page_size}

    positions, total = await service.list_positions(
        db,
        user_id=user.id,
        strategy_id=strategy_id,
        symbol=symbol,
        status=status,
        market=market,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [
            PositionResponse.model_validate(p).model_dump(by_alias=True)
            for p in positions
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/positions/open", response_model=dict)
async def get_open_positions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all open positions."""
    service = get_portfolio_service()
    if not service:
        return {"data": []}

    positions = await service.get_open_positions_for_user(db, user.id)
    return {
        "data": [
            PositionResponse.model_validate(p).model_dump(by_alias=True)
            for p in positions
        ],
    }


@router.get("/positions/closed", response_model=dict)
async def get_closed_positions(
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get closed positions with date range filter."""
    service = get_portfolio_service()
    if not service:
        return {"data": [], "total": 0, "page": page, "pageSize": page_size}

    positions, total = await service.get_closed_positions(
        db, user.id,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [
            PositionResponse.model_validate(p).model_dump(by_alias=True)
            for p in positions
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/positions/{position_id}", response_model=dict)
async def get_position(
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a position by ID."""
    service = get_portfolio_service()
    if not service:
        from app.portfolio.errors import PositionNotFoundError
        raise PositionNotFoundError(str(position_id))

    position = await service.get_position(db, position_id, user.id)
    return {
        "data": PositionResponse.model_validate(position).model_dump(by_alias=True)
    }


# --- Portfolio State ---


@router.get("/summary", response_model=dict)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get portfolio summary."""
    service = get_portfolio_service()
    if not service:
        return {"data": {}}

    summary = await service.get_summary(db, user.id)
    return {
        "data": PortfolioSummaryResponse(**summary).model_dump(by_alias=True)
    }


@router.get("/equity", response_model=dict)
async def get_equity_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get equity breakdown by market."""
    service = get_portfolio_service()
    if not service:
        return {"data": {}}

    breakdown = await service.get_equity_breakdown(db, user.id)
    return {
        "data": EquityBreakdownResponse(**breakdown).model_dump(by_alias=True)
    }


@router.get("/cash", response_model=dict)
async def get_cash_balances(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get cash balances per account scope."""
    service = get_portfolio_service()
    if not service:
        return {"data": []}

    balances = await service.get_all_cash_balances(db, user.id)
    return {
        "data": [
            CashBalanceResponse.model_validate(b).model_dump(by_alias=True)
            for b in balances
        ],
    }


# --- Snapshots and History ---


@router.get("/snapshots", response_model=dict)
async def list_snapshots(
    snapshot_type: str | None = Query(None, alias="snapshotType"),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get portfolio snapshots."""
    service = get_portfolio_service()
    if not service:
        return {"data": [], "total": 0, "page": page, "pageSize": page_size}

    snapshots, total = await service.get_snapshots(
        db, user.id, snapshot_type=snapshot_type,
        start=date_start, end=date_end, page=page, page_size=page_size,
    )
    return {
        "data": [
            PortfolioSnapshotResponse.model_validate(s).model_dump(by_alias=True)
            for s in snapshots
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/equity-curve", response_model=dict)
async def get_equity_curve(
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get equity curve for charting."""
    service = get_portfolio_service()
    if not service:
        return {"data": []}

    curve = await service.get_equity_curve(db, user.id, start=date_start, end=date_end)
    return {"data": curve}


# --- PnL ---


@router.get("/pnl/realized", response_model=dict)
async def list_realized_pnl(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    symbol: str | None = Query(None),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get realized PnL entries."""
    service = get_portfolio_service()
    if not service:
        return {"data": [], "total": 0, "page": page, "pageSize": page_size}

    entries, total = await service.get_pnl_entries(
        db, user.id, strategy_id=strategy_id, symbol=symbol,
        start=date_start, end=date_end, page=page, page_size=page_size,
    )
    return {
        "data": [
            RealizedPnlEntryResponse.model_validate(e).model_dump(by_alias=True)
            for e in entries
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/pnl/summary", response_model=dict)
async def get_pnl_summary(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get PnL summary."""
    service = get_portfolio_service()
    if not service:
        return {"data": {}}

    summary = await service.get_pnl_summary(db, user.id, strategy_id=strategy_id)
    return {"data": PnlSummaryResponse(**summary).model_dump(by_alias=True)}


# --- Dividends ---


@router.get("/dividends", response_model=dict)
async def list_dividends(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dividend payment history."""
    service = get_portfolio_service()
    if not service:
        return {"data": [], "total": 0, "page": page, "pageSize": page_size}

    payments, total = await service.get_dividend_payments(
        db, user.id, page=page, page_size=page_size,
    )
    return {
        "data": [
            DividendPaymentResponse.model_validate(p).model_dump(by_alias=True)
            for p in payments
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/dividends/upcoming", response_model=dict)
async def get_upcoming_dividends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get upcoming dividends for held positions."""
    service = get_portfolio_service()
    if not service:
        return {"data": []}

    upcoming = await service.get_upcoming_dividends(db, user.id)
    return {"data": upcoming}


@router.get("/dividends/summary", response_model=dict)
async def get_dividend_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dividend income summary."""
    service = get_portfolio_service()
    if not service:
        return {"data": {}}

    summary = await service.get_dividend_summary(db, user.id)
    return {"data": DividendSummaryResponse(**summary).model_dump(by_alias=True)}


# --- Performance Metrics ---


@router.get("/metrics", response_model=dict)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get portfolio-wide performance metrics."""
    service = get_portfolio_service()
    if not service:
        return {"data": {}}

    metrics = await service.get_metrics(db, user.id)
    return {"data": PerformanceMetricsResponse(**metrics).model_dump(by_alias=True)}


@router.get("/metrics/{strategy_id}", response_model=dict)
async def get_strategy_metrics(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get per-strategy performance metrics."""
    service = get_portfolio_service()
    if not service:
        return {"data": {}}

    metrics = await service.get_metrics(db, user.id, strategy_id=strategy_id)
    return {"data": PerformanceMetricsResponse(**metrics).model_dump(by_alias=True)}


# --- Admin ---


@router.post("/drawdown/reset-peak", response_model=dict)
async def reset_peak_equity(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Reset peak equity to current equity (admin only)."""
    service = get_portfolio_service()
    if not service:
        return {"data": {"status": "service_unavailable"}}

    await service.reset_peak_equity(db, user.id, admin_user=str(user.id))
    await db.commit()
    return {"data": {"status": "ok"}}


@router.post("/cash/adjust", response_model=dict)
async def adjust_cash(
    body: CashAdjustRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Manual cash adjustment (admin only)."""
    service = get_portfolio_service()
    if not service:
        return {"data": {"status": "service_unavailable"}}

    cash = await service.adjust_cash(
        db, user.id, body.account_scope, body.amount, body.reason,
        admin_user=str(user.id),
    )
    await db.commit()
    return {"data": CashBalanceResponse.model_validate(cash).model_dump(by_alias=True)}
