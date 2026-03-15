"""Realized PnL ledger — append-only record of closed trades."""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import RealizedPnlEntry

logger = logging.getLogger(__name__)


class PnlLedger:
    """Manages the append-only realized PnL ledger."""

    async def record_close(
        self,
        db: AsyncSession,
        position: object,
        fill: object,
        exit_price: Decimal,
        qty_closed: Decimal,
        gross_pnl: Decimal,
        fees: Decimal,
        net_pnl: Decimal,
    ) -> RealizedPnlEntry:
        """Record a realized PnL entry when a position is partially or fully closed."""
        pnl_percent = Decimal("0")
        if position.avg_entry_price > 0 and qty_closed > 0:
            cost = position.avg_entry_price * qty_closed
            if cost > 0:
                pnl_percent = net_pnl / cost * 100

        entry = RealizedPnlEntry(
            position_id=position.id,
            strategy_id=position.strategy_id,
            user_id=position.user_id,
            symbol=position.symbol,
            market=position.market,
            side=position.side,
            qty_closed=qty_closed,
            entry_price=position.avg_entry_price,
            exit_price=exit_price,
            gross_pnl=gross_pnl,
            fees=fees,
            net_pnl=net_pnl,
            pnl_percent=pnl_percent,
            holding_period_bars=position.bars_held,
            closed_at=fill.filled_at,
        )
        db.add(entry)
        await db.flush()

        logger.info(
            "PnL entry: %s %s qty=%s net_pnl=%s",
            position.symbol, position.side, qty_closed, net_pnl,
        )
        return entry

    async def get_entries(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[RealizedPnlEntry], int]:
        """Query PnL entries with filters."""
        query = select(RealizedPnlEntry).where(
            RealizedPnlEntry.user_id == user_id
        )
        count_query = select(func.count()).select_from(RealizedPnlEntry).where(
            RealizedPnlEntry.user_id == user_id
        )

        if strategy_id:
            query = query.where(RealizedPnlEntry.strategy_id == strategy_id)
            count_query = count_query.where(
                RealizedPnlEntry.strategy_id == strategy_id
            )
        if symbol:
            query = query.where(RealizedPnlEntry.symbol == symbol)
            count_query = count_query.where(RealizedPnlEntry.symbol == symbol)
        if start:
            query = query.where(RealizedPnlEntry.closed_at >= start)
            count_query = count_query.where(RealizedPnlEntry.closed_at >= start)
        if end:
            query = query.where(RealizedPnlEntry.closed_at <= end)
            count_query = count_query.where(RealizedPnlEntry.closed_at <= end)

        query = query.order_by(RealizedPnlEntry.closed_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        entries = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return entries, total

    async def get_summary(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
    ) -> dict:
        """PnL summary with period breakdowns."""
        now = datetime.now(timezone.utc)

        # Today boundary
        today_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now.hour < 5:
            today_start -= timedelta(days=1)

        # Week start (Monday 05:00 UTC)
        days_since_monday = now.weekday()
        week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=5, minute=0, second=0, microsecond=0
        )

        # Month start
        month_start = now.replace(day=1, hour=5, minute=0, second=0, microsecond=0)

        base_filter = [RealizedPnlEntry.user_id == user_id]
        if strategy_id:
            base_filter.append(RealizedPnlEntry.strategy_id == strategy_id)

        async def _sum_period(after: datetime) -> Decimal:
            result = await db.execute(
                select(
                    func.coalesce(func.sum(RealizedPnlEntry.net_pnl), Decimal("0"))
                ).where(*base_filter, RealizedPnlEntry.closed_at >= after)
            )
            return result.scalar_one()

        today = await _sum_period(today_start)
        this_week = await _sum_period(week_start)
        this_month = await _sum_period(month_start)

        # Total
        total_result = await db.execute(
            select(
                func.coalesce(func.sum(RealizedPnlEntry.net_pnl), Decimal("0"))
            ).where(*base_filter)
        )
        total = total_result.scalar_one()

        # By strategy
        by_strategy_result = await db.execute(
            select(
                RealizedPnlEntry.strategy_id,
                func.sum(RealizedPnlEntry.net_pnl),
                func.count(),
            )
            .where(RealizedPnlEntry.user_id == user_id)
            .group_by(RealizedPnlEntry.strategy_id)
        )
        by_strategy = {
            str(row[0]): {"total": row[1], "count": row[2]}
            for row in by_strategy_result.all()
        }

        # By symbol
        by_symbol_result = await db.execute(
            select(
                RealizedPnlEntry.symbol,
                func.sum(RealizedPnlEntry.net_pnl),
                func.count(),
            )
            .where(RealizedPnlEntry.user_id == user_id)
            .group_by(RealizedPnlEntry.symbol)
        )
        by_symbol = {
            row[0]: {"total": row[1], "count": row[2]}
            for row in by_symbol_result.all()
        }

        return {
            "today": today,
            "this_week": this_week,
            "this_month": this_month,
            "total": total,
            "by_strategy": by_strategy,
            "by_symbol": by_symbol,
        }

    async def get_daily_loss(
        self, db: AsyncSession, user_id: UUID
    ) -> Decimal:
        """Sum of negative net_pnl entries closed today."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now.hour < 5:
            today_start -= timedelta(days=1)

        result = await db.execute(
            select(
                func.coalesce(func.sum(RealizedPnlEntry.net_pnl), Decimal("0"))
            ).where(
                RealizedPnlEntry.user_id == user_id,
                RealizedPnlEntry.closed_at >= today_start,
                RealizedPnlEntry.net_pnl < 0,
            )
        )
        return abs(result.scalar_one())
