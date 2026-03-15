"""Signal module repository — all database access."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.signals.models import Signal


class SignalRepository:
    async def create(self, db: AsyncSession, signal: Signal) -> Signal:
        db.add(signal)
        await db.flush()
        return signal

    async def get_by_id(self, db: AsyncSession, signal_id: UUID) -> Signal | None:
        result = await db.execute(select(Signal).where(Signal.id == signal_id))
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        db: AsyncSession,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        status: str | None = None,
        signal_type: str | None = None,
        source: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Signal], int]:
        query = select(Signal)
        count_query = select(func.count()).select_from(Signal)

        filters = []
        if strategy_id:
            filters.append(Signal.strategy_id == strategy_id)
        if symbol:
            filters.append(Signal.symbol == symbol)
        if status:
            filters.append(Signal.status == status)
        if signal_type:
            filters.append(Signal.signal_type == signal_type)
        if source:
            filters.append(Signal.source == source)
        if date_start:
            filters.append(Signal.created_at >= date_start)
        if date_end:
            filters.append(Signal.created_at <= date_end)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(Signal.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        signals = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return signals, total

    async def get_recent(self, db: AsyncSession, limit: int = 20) -> list[Signal]:
        result = await db.execute(
            select(Signal).order_by(Signal.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending(self, db: AsyncSession) -> list[Signal]:
        result = await db.execute(
            select(Signal)
            .where(Signal.status == "pending")
            .order_by(Signal.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_status(
        self, db: AsyncSession, signal_id: UUID, new_status: str
    ) -> Signal | None:
        signal = await self.get_by_id(db, signal_id)
        if signal is None:
            return None
        signal.status = new_status
        await db.flush()
        return signal

    async def find_duplicate(
        self,
        db: AsyncSession,
        strategy_id: UUID,
        symbol: str,
        side: str,
        signal_type: str,
        window_start: datetime,
    ) -> Signal | None:
        result = await db.execute(
            select(Signal).where(
                Signal.strategy_id == strategy_id,
                Signal.symbol == symbol,
                Signal.side == side,
                Signal.signal_type == signal_type,
                Signal.status.in_(["pending", "risk_approved"]),
                Signal.created_at >= window_start,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def expire_stale(self, db: AsyncSession) -> int:
        from datetime import timezone

        now = datetime.now(timezone.utc)
        result = await db.execute(
            update(Signal)
            .where(
                Signal.status == "pending",
                Signal.expires_at != None,  # noqa: E711
                Signal.expires_at < now,
            )
            .values(status="expired")
        )
        await db.flush()
        return result.rowcount

    async def cancel_by_strategy(self, db: AsyncSession, strategy_id: UUID) -> int:
        result = await db.execute(
            update(Signal)
            .where(
                Signal.strategy_id == strategy_id,
                Signal.status == "pending",
            )
            .values(status="canceled")
        )
        await db.flush()
        return result.rowcount

    async def get_stats(
        self,
        db: AsyncSession,
        strategy_id: UUID | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
    ) -> dict:
        filters = []
        if strategy_id:
            filters.append(Signal.strategy_id == strategy_id)
        if date_start:
            filters.append(Signal.created_at >= date_start)
        if date_end:
            filters.append(Signal.created_at <= date_end)

        def _apply_filters(q):
            for f in filters:
                q = q.where(f)
            return q

        # Total count
        total_q = _apply_filters(select(func.count()).select_from(Signal))
        total = (await db.execute(total_q)).scalar_one()

        # By status
        status_q = _apply_filters(
            select(Signal.status, func.count()).group_by(Signal.status)
        )
        by_status = {row[0]: row[1] for row in (await db.execute(status_q)).all()}

        # By strategy
        strat_q = _apply_filters(
            select(Signal.strategy_id, func.count()).group_by(Signal.strategy_id)
        )
        by_strategy = {
            str(row[0]): row[1] for row in (await db.execute(strat_q)).all()
        }

        # By symbol
        sym_q = _apply_filters(
            select(Signal.symbol, func.count()).group_by(Signal.symbol)
        )
        by_symbol = {row[0]: row[1] for row in (await db.execute(sym_q)).all()}

        # By signal_type
        type_q = _apply_filters(
            select(Signal.signal_type, func.count()).group_by(Signal.signal_type)
        )
        by_signal_type = {row[0]: row[1] for row in (await db.execute(type_q)).all()}

        # By source
        src_q = _apply_filters(
            select(Signal.source, func.count()).group_by(Signal.source)
        )
        by_source = {row[0]: row[1] for row in (await db.execute(src_q)).all()}

        return {
            "total": total,
            "by_status": by_status,
            "by_strategy": by_strategy,
            "by_symbol": by_symbol,
            "by_signal_type": by_signal_type,
            "by_source": by_source,
        }
