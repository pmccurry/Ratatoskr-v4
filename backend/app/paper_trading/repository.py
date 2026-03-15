"""Paper trading repository — all database access."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.models import PaperFill, PaperOrder


class PaperOrderRepository:
    async def create(self, db: AsyncSession, order: PaperOrder) -> PaperOrder:
        db.add(order)
        await db.flush()
        return order

    async def get_by_id(self, db: AsyncSession, order_id: UUID) -> PaperOrder | None:
        result = await db.execute(
            select(PaperOrder).where(PaperOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_signal_id(self, db: AsyncSession, signal_id: UUID) -> PaperOrder | None:
        result = await db.execute(
            select(PaperOrder).where(PaperOrder.signal_id == signal_id)
        )
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        db: AsyncSession,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        status: str | None = None,
        signal_type: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PaperOrder], int]:
        query = select(PaperOrder)
        count_query = select(func.count()).select_from(PaperOrder)

        filters = []
        if strategy_id:
            filters.append(PaperOrder.strategy_id == strategy_id)
        if symbol:
            filters.append(PaperOrder.symbol == symbol)
        if status:
            filters.append(PaperOrder.status == status)
        if signal_type:
            filters.append(PaperOrder.signal_type == signal_type)
        if date_start:
            filters.append(PaperOrder.created_at >= date_start)
        if date_end:
            filters.append(PaperOrder.created_at <= date_end)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(PaperOrder.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        orders = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return orders, total

    async def update(self, db: AsyncSession, order: PaperOrder) -> PaperOrder:
        await db.flush()
        return order

    async def get_pending_for_symbol(
        self,
        db: AsyncSession,
        strategy_id: UUID,
        symbol: str,
        side: str,
    ) -> PaperOrder | None:
        """Used by risk engine's duplicate order check."""
        result = await db.execute(
            select(PaperOrder).where(
                PaperOrder.strategy_id == strategy_id,
                PaperOrder.symbol == symbol,
                PaperOrder.side == side,
                PaperOrder.status.in_(["pending", "accepted"]),
            ).limit(1)
        )
        return result.scalar_one_or_none()


class PaperFillRepository:
    async def create(self, db: AsyncSession, fill: PaperFill) -> PaperFill:
        db.add(fill)
        await db.flush()
        return fill

    async def get_by_id(self, db: AsyncSession, fill_id: UUID) -> PaperFill | None:
        result = await db.execute(
            select(PaperFill).where(PaperFill.id == fill_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, db: AsyncSession, order_id: UUID) -> list[PaperFill]:
        result = await db.execute(
            select(PaperFill)
            .where(PaperFill.order_id == order_id)
            .order_by(PaperFill.filled_at.asc())
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        db: AsyncSession,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        side: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PaperFill], int]:
        query = select(PaperFill)
        count_query = select(func.count()).select_from(PaperFill)

        filters = []
        if strategy_id:
            filters.append(PaperFill.strategy_id == strategy_id)
        if symbol:
            filters.append(PaperFill.symbol == symbol)
        if side:
            filters.append(PaperFill.side == side)
        if date_start:
            filters.append(PaperFill.filled_at >= date_start)
        if date_end:
            filters.append(PaperFill.filled_at <= date_end)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(PaperFill.filled_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        fills = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return fills, total

    async def get_recent(self, db: AsyncSession, limit: int = 20) -> list[PaperFill]:
        result = await db.execute(
            select(PaperFill).order_by(PaperFill.filled_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
