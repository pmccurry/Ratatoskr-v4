"""Backtest repository — database operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.models import BacktestRun, BacktestTrade, BacktestEquityPoint


class BacktestRepository:
    async def create(self, db: AsyncSession, run: BacktestRun) -> BacktestRun:
        db.add(run)
        await db.flush()
        return run

    async def get_by_id(self, db: AsyncSession, backtest_id: UUID) -> BacktestRun | None:
        result = await db.execute(
            select(BacktestRun).where(BacktestRun.id == backtest_id)
        )
        return result.scalar_one_or_none()

    async def list_by_strategy(
        self, db: AsyncSession, strategy_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[BacktestRun], int]:
        # Count
        count_result = await db.execute(
            select(func.count()).select_from(BacktestRun).where(
                BacktestRun.strategy_id == strategy_id
            )
        )
        total = count_result.scalar_one()

        # Fetch
        offset = (page - 1) * page_size
        result = await db.execute(
            select(BacktestRun)
            .where(BacktestRun.strategy_id == strategy_id)
            .order_by(desc(BacktestRun.created_at))
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_trades(
        self, db: AsyncSession, backtest_id: UUID, page: int = 1, page_size: int = 50
    ) -> tuple[list[BacktestTrade], int]:
        count_result = await db.execute(
            select(func.count()).select_from(BacktestTrade).where(
                BacktestTrade.backtest_id == backtest_id
            )
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await db.execute(
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)
            .order_by(BacktestTrade.entry_time.asc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_equity_curve(
        self, db: AsyncSession, backtest_id: UUID, sample: int | None = None
    ) -> list[BacktestEquityPoint]:
        query = (
            select(BacktestEquityPoint)
            .where(BacktestEquityPoint.backtest_id == backtest_id)
            .order_by(BacktestEquityPoint.bar_index.asc())
        )
        result = await db.execute(query)
        points = list(result.scalars().all())

        # Downsample if requested
        if sample and len(points) > sample:
            step = len(points) / sample
            indices = [int(i * step) for i in range(sample)]
            # Always include last point
            if indices[-1] != len(points) - 1:
                indices[-1] = len(points) - 1
            points = [points[i] for i in indices]

        return points
