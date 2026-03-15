"""Portfolio snapshot management."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.config import PortfolioConfig
from app.portfolio.models import (
    DividendPayment,
    PortfolioSnapshot,
    Position,
    RealizedPnlEntry,
)
from app.portfolio.repository import (
    CashBalanceRepository,
    PortfolioMetaRepository,
)

logger = logging.getLogger(__name__)

_cash_repo = CashBalanceRepository()
_meta_repo = PortfolioMetaRepository()

# US equities market close: 4:00 PM ET = 21:00 UTC (EST) or 20:00 UTC (EDT)
_MARKET_CLOSE_HOUR_UTC = 21


class SnapshotManager:
    """Creates and queries portfolio snapshots."""

    def __init__(self, config: PortfolioConfig):
        self._config = config
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_daily_run: date | None = None

    async def take_snapshot(
        self, db: AsyncSession, user_id: UUID, snapshot_type: str
    ) -> PortfolioSnapshot:
        """Capture current portfolio state."""
        # Cash
        total_cash = await _cash_repo.get_total_cash(db, user_id)

        # Positions
        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id, Position.status == "open"
            )
        )
        positions = list(result.scalars().all())

        positions_value = sum((p.market_value for p in positions), Decimal("0"))
        unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal("0"))
        equity = total_cash + positions_value

        # Peak equity
        peak_str = await _meta_repo.get(db, "peak_equity", user_id)
        peak_equity = Decimal(peak_str) if peak_str else equity

        # Drawdown
        drawdown_percent = Decimal("0")
        if peak_equity > 0:
            drawdown_percent = max(
                (peak_equity - equity) / peak_equity * 100, Decimal("0")
            )

        # Today boundary (approximate ET midnight as 05:00 UTC)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now.hour < 5:
            today_start -= timedelta(days=1)

        # Realized PnL today
        rpnl_today_result = await db.execute(
            select(func.coalesce(func.sum(RealizedPnlEntry.net_pnl), Decimal("0")))
            .where(
                RealizedPnlEntry.user_id == user_id,
                RealizedPnlEntry.closed_at >= today_start,
            )
        )
        realized_pnl_today = rpnl_today_result.scalar_one()

        # Realized PnL total
        rpnl_total_result = await db.execute(
            select(func.coalesce(func.sum(RealizedPnlEntry.net_pnl), Decimal("0")))
            .where(RealizedPnlEntry.user_id == user_id)
        )
        realized_pnl_total = rpnl_total_result.scalar_one()

        # Dividend income today
        div_today_result = await db.execute(
            select(func.coalesce(func.sum(DividendPayment.net_amount), Decimal("0")))
            .where(
                DividendPayment.user_id == user_id,
                DividendPayment.status == "paid",
                DividendPayment.paid_at >= today_start,
            )
        )
        dividend_income_today = div_today_result.scalar_one()

        # Dividend income total
        div_total_result = await db.execute(
            select(func.coalesce(func.sum(DividendPayment.net_amount), Decimal("0")))
            .where(
                DividendPayment.user_id == user_id,
                DividendPayment.status == "paid",
            )
        )
        dividend_income_total = div_total_result.scalar_one()

        snapshot = PortfolioSnapshot(
            user_id=user_id,
            ts=now,
            cash_balance=total_cash,
            positions_value=positions_value,
            equity=equity,
            unrealized_pnl=unrealized_pnl,
            realized_pnl_today=realized_pnl_today,
            realized_pnl_total=realized_pnl_total,
            dividend_income_today=dividend_income_today,
            dividend_income_total=dividend_income_total,
            drawdown_percent=drawdown_percent,
            peak_equity=peak_equity,
            open_positions_count=len(positions),
            snapshot_type=snapshot_type,
        )
        db.add(snapshot)
        await db.flush()

        return snapshot

    async def start_periodic(self) -> None:
        """Start background task for periodic snapshots."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Periodic snapshots started (interval=%ds)",
            self._config.snapshot_interval,
        )

    async def stop_periodic(self) -> None:
        """Stop periodic snapshot task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Periodic snapshots stopped")

    async def _run_loop(self) -> None:
        """Periodically take snapshots for all users with open positions.

        Also checks if a new trading day has started (after market close)
        and triggers DailyPortfolioJobs automatically.
        """
        from app.common.database import get_session_factory

        factory = get_session_factory()
        while self._running:
            try:
                async with factory() as db:
                    # Get distinct user_ids with open positions or cash
                    from app.portfolio.models import CashBalance
                    result = await db.execute(
                        select(CashBalance.user_id).distinct()
                    )
                    user_ids = [row[0] for row in result.all()]

                    for user_id in user_ids:
                        try:
                            await self.take_snapshot(db, user_id, "periodic")
                        except Exception as e:
                            logger.error(
                                "Snapshot error for user %s: %s", user_id, e
                            )

                    # Check if daily jobs should run
                    await self._check_daily_jobs(db, user_ids)

                    await db.commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Periodic snapshot error: %s", e)

            try:
                await asyncio.sleep(self._config.snapshot_interval)
            except asyncio.CancelledError:
                break

    async def _check_daily_jobs(
        self, db: AsyncSession, user_ids: list[UUID]
    ) -> None:
        """Run daily portfolio jobs once per day after market close."""
        today = date.today()
        if self._last_daily_run == today:
            return

        now = datetime.now(timezone.utc)
        if now.hour < _MARKET_CLOSE_HOUR_UTC:
            return

        try:
            from app.portfolio.daily_jobs import DailyPortfolioJobs

            daily_jobs = DailyPortfolioJobs()
            for user_id in user_ids:
                try:
                    summary = await daily_jobs.run_daily(db, user_id)
                    logger.info(
                        "Daily portfolio jobs completed for user %s: %s",
                        user_id, summary,
                    )
                except Exception as e:
                    logger.error(
                        "Daily jobs error for user %s: %s", user_id, e
                    )
            self._last_daily_run = today
        except Exception as e:
            logger.error("Daily jobs check error: %s", e)

    async def take_daily_close_snapshot(
        self, db: AsyncSession, user_id: UUID
    ) -> PortfolioSnapshot:
        """Take a daily close snapshot."""
        return await self.take_snapshot(db, user_id, "daily_close")

    async def get_equity_curve(
        self,
        db: AsyncSession,
        user_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        snapshot_type: str = "periodic",
    ) -> list[dict]:
        """Return equity time series for charting."""
        query = select(
            PortfolioSnapshot.ts, PortfolioSnapshot.equity
        ).where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.snapshot_type == snapshot_type,
        )
        if start:
            query = query.where(PortfolioSnapshot.ts >= start)
        if end:
            query = query.where(PortfolioSnapshot.ts <= end)
        query = query.order_by(PortfolioSnapshot.ts.asc())

        result = await db.execute(query)
        return [{"ts": row.ts, "equity": row.equity} for row in result.all()]

    async def get_snapshots(
        self,
        db: AsyncSession,
        user_id: UUID,
        snapshot_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PortfolioSnapshot], int]:
        """Query snapshots with filters."""
        query = select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id
        )
        count_query = select(func.count()).select_from(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id
        )

        if snapshot_type:
            query = query.where(PortfolioSnapshot.snapshot_type == snapshot_type)
            count_query = count_query.where(
                PortfolioSnapshot.snapshot_type == snapshot_type
            )
        if start:
            query = query.where(PortfolioSnapshot.ts >= start)
            count_query = count_query.where(PortfolioSnapshot.ts >= start)
        if end:
            query = query.where(PortfolioSnapshot.ts <= end)
            count_query = count_query.where(PortfolioSnapshot.ts <= end)

        query = query.order_by(PortfolioSnapshot.ts.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        snapshots = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return snapshots, total
