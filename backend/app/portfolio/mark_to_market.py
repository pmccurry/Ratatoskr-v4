"""Mark-to-market — periodically updates open positions with current prices."""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.config import PortfolioConfig
from app.portfolio.repository import (
    CashBalanceRepository,
    PortfolioMetaRepository,
    PositionRepository,
)

logger = logging.getLogger(__name__)

_position_repo = PositionRepository()
_cash_repo = CashBalanceRepository()
_meta_repo = PortfolioMetaRepository()


class MarkToMarket:
    """Periodically updates open positions with current prices."""

    def __init__(self, config: PortfolioConfig):
        self._config = config
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the mark-to-market loop as a background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Mark-to-market started (interval=%ds)", self._config.mark_to_market_interval
        )

    async def stop(self) -> None:
        """Stop the loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Mark-to-market stopped")

    async def _run_loop(self) -> None:
        """Periodically run mark-to-market."""
        from app.common.database import get_session_factory

        factory = get_session_factory()
        while self._running:
            try:
                async with factory() as db:
                    result = await self.run_cycle(db)
                    await db.commit()
                    if result["positions_updated"] > 0:
                        logger.info(
                            "MTM cycle: updated=%d skipped=%d",
                            result["positions_updated"],
                            result["skipped_closed_market"],
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Mark-to-market error: %s", e)

            try:
                await asyncio.sleep(self._config.mark_to_market_interval)
            except asyncio.CancelledError:
                break

    async def run_cycle(self, db: AsyncSession) -> dict:
        """Run one mark-to-market cycle."""
        from app.market_data.service import MarketDataService

        md_service = MarketDataService()

        # Get all open positions across all users
        from sqlalchemy import select
        from app.portfolio.models import Position

        result = await db.execute(
            select(Position).where(Position.status == "open")
        )
        positions = list(result.scalars().all())

        updated = 0
        skipped = 0
        user_ids_updated: set = set()

        for position in positions:
            # Skip if market is closed
            if not self._is_market_open(position.market):
                skipped += 1
                continue

            current_price = await md_service.get_latest_close(
                db, position.symbol, "1m"
            )
            if current_price is None:
                skipped += 1
                continue

            multiplier = Decimal(str(position.contract_multiplier))

            # Update position
            position.current_price = current_price
            position.market_value = position.qty * current_price * multiplier

            # Unrealized PnL
            if position.side == "long":
                position.unrealized_pnl = (
                    (current_price - position.avg_entry_price)
                    * position.qty * multiplier
                )
                if position.avg_entry_price > 0:
                    position.unrealized_pnl_percent = (
                        (current_price - position.avg_entry_price)
                        / position.avg_entry_price * 100
                    )
            else:
                position.unrealized_pnl = (
                    (position.avg_entry_price - current_price)
                    * position.qty * multiplier
                )
                if position.avg_entry_price > 0:
                    position.unrealized_pnl_percent = (
                        (position.avg_entry_price - current_price)
                        / position.avg_entry_price * 100
                    )

            # Total return
            position.total_return = (
                position.unrealized_pnl + position.realized_pnl
                + position.total_dividends_received
            )
            if position.cost_basis > 0:
                position.total_return_percent = (
                    position.total_return / position.cost_basis * 100
                )

            # Track highest/lowest
            if current_price > position.highest_price_since_entry:
                position.highest_price_since_entry = current_price
            if current_price < position.lowest_price_since_entry:
                position.lowest_price_since_entry = current_price

            updated += 1
            user_ids_updated.add(position.user_id)

        await db.flush()

        # Update peak equity for each user that had positions updated
        for user_id in user_ids_updated:
            await self._update_peak_equity(db, user_id)

        return {
            "positions_updated": updated,
            "skipped_closed_market": skipped,
        }

    async def _update_peak_equity(
        self, db: AsyncSession, user_id: object
    ) -> None:
        """Update peak equity if current equity is a new high."""
        total_cash = await _cash_repo.get_total_cash(db, user_id)

        from sqlalchemy import select, func
        from app.portfolio.models import Position

        result = await db.execute(
            select(func.coalesce(func.sum(Position.market_value), Decimal("0")))
            .where(Position.user_id == user_id, Position.status == "open")
        )
        positions_value = result.scalar_one()

        current_equity = total_cash + positions_value

        # Read current peak
        peak_str = await _meta_repo.get(db, "peak_equity", user_id)
        peak = Decimal(peak_str) if peak_str else current_equity

        if current_equity > peak:
            now = datetime.now(timezone.utc)
            await _meta_repo.set(db, "peak_equity", str(current_equity), user_id)
            await _meta_repo.set(db, "peak_equity_at", now.isoformat(), user_id)

    def _is_market_open(self, market: str) -> bool:
        """Check if market is open (approximate)."""
        now = datetime.now(timezone.utc)
        weekday = now.weekday()

        if market == "forex":
            # Sunday 22:00 UTC through Friday 22:00 UTC
            if weekday == 5:  # Saturday
                return False
            if weekday == 6:  # Sunday
                return now.hour >= 22
            if weekday == 4:  # Friday
                return now.hour < 22
            return True

        # Equities: 9:30-16:00 ET ≈ 14:30-21:00 UTC weekdays
        if weekday >= 5:
            return False
        hour = now.hour
        minute = now.minute
        if hour < 14 or (hour == 14 and minute < 30):
            return False
        if hour >= 21:
            return False
        return True
