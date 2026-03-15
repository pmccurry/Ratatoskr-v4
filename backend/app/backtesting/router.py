"""Backtesting module API endpoints."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.backtesting.models import BacktestRun
from app.backtesting.repository import BacktestRepository
from app.backtesting.schemas import (
    BacktestEquityPointResponse,
    BacktestRequest,
    BacktestRunResponse,
    BacktestTradeResponse,
)
from app.common.database import get_db
from app.strategies.models import Strategy, StrategyConfigVersion

logger = logging.getLogger(__name__)

# Router for /backtesting/* endpoints (run detail, trades, equity curve)
router = APIRouter(
    prefix="/backtesting",
    tags=["Backtesting"],
)

# Router for /strategies/{id}/backtest* endpoints (trigger and list)
strategy_backtest_router = APIRouter(
    prefix="/strategies",
    tags=["Strategies", "Backtesting"],
)

_repo = BacktestRepository()


# ---------------------------------------------------------------------------
# Strategy-scoped endpoints
# ---------------------------------------------------------------------------


@strategy_backtest_router.post("/{strategy_id}/backtest", status_code=201)
async def trigger_backtest(
    strategy_id: UUID,
    body: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a backtest run for a strategy."""
    from app.backtesting.runner import BacktestRunner

    # Load strategy and verify ownership
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if strategy.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Get latest active config version
    config_result = await db.execute(
        select(StrategyConfigVersion)
        .where(
            StrategyConfigVersion.strategy_id == strategy_id,
            StrategyConfigVersion.is_active == True,  # noqa: E712
        )
        .limit(1)
    )
    config_version = config_result.scalar_one_or_none()
    if not config_version:
        raise HTTPException(status_code=400, detail="Strategy has no active config version")

    # Create BacktestRun record
    run = BacktestRun(
        strategy_id=strategy_id,
        status="pending",
        strategy_config=config_version.config_json,
        symbols=body.symbols,
        timeframe=body.timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        position_sizing=body.position_sizing,
        exit_config=body.exit_config,
    )
    run = await _repo.create(db, run)
    await db.flush()

    # Run backtest
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        runner = BacktestRunner()
        metrics = await runner.run(run, db)

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        if run.started_at:
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
    except Exception as exc:
        logger.exception("Backtest %s failed: %s", run.id, exc)
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        if run.started_at:
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
        run.error = str(exc)

    await db.flush()

    return {
        "data": BacktestRunResponse.model_validate(run).model_dump(by_alias=True)
    }


@strategy_backtest_router.get("/{strategy_id}/backtests")
async def list_backtests(
    strategy_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List backtest runs for a strategy."""
    # Verify strategy ownership
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if strategy.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Strategy not found")

    runs, total = await _repo.list_by_strategy(db, strategy_id, page=page, page_size=page_size)
    return {
        "data": [
            BacktestRunResponse.model_validate(r).model_dump(by_alias=True)
            for r in runs
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


# ---------------------------------------------------------------------------
# Backtest-scoped endpoints
# ---------------------------------------------------------------------------


@router.get("/{backtest_id}")
async def get_backtest(
    backtest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get backtest run details."""
    run = await _repo.get_by_id(db, backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # Verify ownership via strategy
    result = await db.execute(
        select(Strategy).where(Strategy.id == run.strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy or strategy.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    return {
        "data": BacktestRunResponse.model_validate(run).model_dump(by_alias=True)
    }


@router.get("/{backtest_id}/trades")
async def get_backtest_trades(
    backtest_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trades from a backtest run with pagination."""
    run = await _repo.get_by_id(db, backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # Verify ownership via strategy
    result = await db.execute(
        select(Strategy).where(Strategy.id == run.strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy or strategy.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    trades, total = await _repo.get_trades(db, backtest_id, page=page, page_size=page_size)
    return {
        "data": [
            BacktestTradeResponse.model_validate(t).model_dump(by_alias=True)
            for t in trades
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/{backtest_id}/equity-curve")
async def get_equity_curve(
    backtest_id: UUID,
    sample: int | None = Query(None, ge=10, le=5000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get equity curve for a backtest run with optional downsampling."""
    run = await _repo.get_by_id(db, backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # Verify ownership via strategy
    result = await db.execute(
        select(Strategy).where(Strategy.id == run.strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy or strategy.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    points = await _repo.get_equity_curve(db, backtest_id, sample=sample)
    return {
        "data": [
            BacktestEquityPointResponse.model_validate(p).model_dump(by_alias=True)
            for p in points
        ],
    }
