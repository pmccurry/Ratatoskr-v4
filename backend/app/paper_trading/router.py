"""Paper trading module API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.common.database import get_db
from app.paper_trading.schemas import (
    BrokerAccountResponse,
    PaperFillResponse,
    PaperOrderResponse,
    PoolStatusResponse,
    ShadowComparisonResponse,
    ShadowFillResponse,
    ShadowPositionResponse,
)
from app.paper_trading.startup import get_paper_trading_service, get_pool_manager

router = APIRouter(
    prefix="/paper-trading",
    tags=["Paper Trading"],
)


# --- Orders ---


@router.get("/orders", response_model=dict)
async def list_orders(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    symbol: str | None = Query(None),
    status: str | None = Query(None),
    signal_type: str | None = Query(None, alias="signalType"),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List paper trading orders with filters."""
    service = get_paper_trading_service()
    orders, total = await service.list_orders(
        db,
        user_id=user.id,
        strategy_id=strategy_id,
        symbol=symbol,
        status=status,
        signal_type=signal_type,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [
            PaperOrderResponse.model_validate(o).model_dump(by_alias=True)
            for o in orders
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/orders/{order_id}", response_model=dict)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a paper trading order by ID."""
    service = get_paper_trading_service()
    order = await service.get_order(db, order_id, user.id)
    return {
        "data": PaperOrderResponse.model_validate(order).model_dump(by_alias=True)
    }


@router.get("/orders/{order_id}/fills", response_model=dict)
async def get_order_fills(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all fills for a paper trading order."""
    service = get_paper_trading_service()
    fills = await service.get_order_fills(db, order_id, user.id)
    return {
        "data": [
            PaperFillResponse.model_validate(f).model_dump(by_alias=True)
            for f in fills
        ],
    }


# --- Fills ---


@router.get("/fills", response_model=dict)
async def list_fills(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    symbol: str | None = Query(None),
    side: str | None = Query(None),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List paper trading fills with filters."""
    service = get_paper_trading_service()
    fills, total = await service.list_fills(
        db,
        user_id=user.id,
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [
            PaperFillResponse.model_validate(f).model_dump(by_alias=True)
            for f in fills
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/fills/recent", response_model=dict)
async def get_recent_fills(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get recent fills across all strategies."""
    service = get_paper_trading_service()
    fills = await service.get_recent_fills(db, user.id, limit=limit)
    return {
        "data": [
            PaperFillResponse.model_validate(f).model_dump(by_alias=True)
            for f in fills
        ],
    }


@router.get("/fills/{fill_id}", response_model=dict)
async def get_fill(
    fill_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a paper trading fill by ID."""
    service = get_paper_trading_service()
    fill = await service.get_fill(db, fill_id, user.id)
    return {
        "data": PaperFillResponse.model_validate(fill).model_dump(by_alias=True)
    }


# --- Forex Pool ---


@router.get("/forex-pool/status", response_model=dict)
async def get_forex_pool_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get forex account pool status."""
    pool = get_pool_manager()
    if not pool:
        return {"data": {"accounts": [], "pair_capacity": {}, "total_accounts": 0, "fully_empty": 0}}

    status = await pool.get_pool_status(db)
    return {"data": PoolStatusResponse(**status).model_dump(by_alias=True)}


@router.get("/forex-pool/accounts", response_model=dict)
async def get_forex_pool_accounts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all forex pool accounts with allocations."""
    pool = get_pool_manager()
    if not pool:
        return {"data": []}

    from app.paper_trading.forex_pool.allocation import BrokerAccountRepository
    accounts = await BrokerAccountRepository().get_all_active(db)
    return {
        "data": [
            BrokerAccountResponse.model_validate(a).model_dump(by_alias=True)
            for a in accounts
        ],
    }


# --- Shadow Tracking ---


@router.get("/shadow/positions", response_model=dict)
async def list_shadow_positions(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List shadow positions."""
    from app.paper_trading.shadow.repository import ShadowPositionRepository

    repo = ShadowPositionRepository()
    positions, total = await repo.get_filtered(
        db, strategy_id=strategy_id, status=status, page=page, page_size=page_size
    )
    return {
        "data": [
            ShadowPositionResponse.model_validate(p).model_dump(by_alias=True)
            for p in positions
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/shadow/positions/{position_id}", response_model=dict)
async def get_shadow_position(
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get shadow position detail with fills."""
    from app.paper_trading.shadow.repository import ShadowFillRepository, ShadowPositionRepository

    pos_repo = ShadowPositionRepository()
    fill_repo = ShadowFillRepository()

    position = await pos_repo.get_by_id(db, position_id)
    if not position:
        from app.paper_trading.errors import OrderNotFoundError
        raise OrderNotFoundError(str(position_id))

    fills = await fill_repo.get_by_position(db, position_id)
    return {
        "data": {
            "position": ShadowPositionResponse.model_validate(position).model_dump(by_alias=True),
            "fills": [
                ShadowFillResponse.model_validate(f).model_dump(by_alias=True)
                for f in fills
            ],
        },
    }


@router.get("/shadow/comparison", response_model=dict)
async def get_shadow_comparison(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get real vs shadow performance comparison per strategy."""
    from decimal import Decimal
    from sqlalchemy import select, func
    from app.strategies.models import Strategy
    from app.paper_trading.models import PaperFill, ShadowPosition
    from app.paper_trading.shadow.repository import ShadowPositionRepository

    shadow_repo = ShadowPositionRepository()

    # Get user's strategies
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == user.id)
    )
    strategies = list(result.scalars().all())

    comparisons = []
    for strategy in strategies:
        # Real trades count
        real_count_result = await db.execute(
            select(func.count()).select_from(PaperFill)
            .where(PaperFill.strategy_id == strategy.id)
        )
        real_trades = real_count_result.scalar_one()

        # Real PnL (sum of fill net_value for sells minus buys — approximate)
        # Better: use portfolio realized_pnl if available
        real_pnl = Decimal("0")
        try:
            from app.portfolio.models import Position
            pnl_result = await db.execute(
                select(func.coalesce(func.sum(Position.realized_pnl), Decimal("0")))
                .where(Position.strategy_id == strategy.id)
            )
            real_pnl = pnl_result.scalar_one()
        except Exception:
            pass

        # Real win rate
        real_wins = 0
        real_closed = 0
        try:
            from app.portfolio.models import Position
            closed_result = await db.execute(
                select(func.count()).select_from(Position).where(
                    Position.strategy_id == strategy.id,
                    Position.status == "closed",
                )
            )
            real_closed = closed_result.scalar_one()

            wins_result = await db.execute(
                select(func.count()).select_from(Position).where(
                    Position.strategy_id == strategy.id,
                    Position.status == "closed",
                    Position.realized_pnl > 0,
                )
            )
            real_wins = wins_result.scalar_one()
        except Exception:
            pass

        real_win_rate = Decimal("0")
        if real_closed > 0:
            real_win_rate = Decimal(str(real_wins)) / Decimal(str(real_closed)) * 100

        # Shadow stats
        shadow_stats = await shadow_repo.get_comparison_stats(db, strategy.id)

        # Blocked signal count (shadow fills with fill_type=entry)
        from app.paper_trading.models import ShadowFill
        blocked_result = await db.execute(
            select(func.count()).select_from(ShadowFill).where(
                ShadowFill.strategy_id == strategy.id,
                ShadowFill.fill_type == "entry",
            )
        )
        blocked_signals = blocked_result.scalar_one()

        comparisons.append(
            ShadowComparisonResponse(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                real_trades=real_trades,
                real_pnl=real_pnl,
                real_win_rate=real_win_rate,
                shadow_trades=shadow_stats["shadow_trades"],
                shadow_pnl=shadow_stats["shadow_pnl"],
                shadow_win_rate=shadow_stats["shadow_win_rate"],
                blocked_signals=blocked_signals,
                missed_pnl=shadow_stats["shadow_pnl"],
            ).model_dump(by_alias=True)
        )

    return {"data": comparisons}


# --- Reconciliation ---


@router.get("/reconciliation", response_model=dict)
async def get_reconciliation(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Compare internal positions against broker state (admin only).

    Returns mismatch report for Alpaca (equities) and OANDA (forex).
    Unconfigured brokers return status='unconfigured'.
    """
    from app.paper_trading.reconciliation import reconcile

    report = await reconcile(db)
    return {"data": report}
