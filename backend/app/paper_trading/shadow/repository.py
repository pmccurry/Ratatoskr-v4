"""Shadow tracking repository — database access for shadow fills and positions."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.models import ShadowFill, ShadowPosition


class ShadowFillRepository:
    async def create(self, db: AsyncSession, fill: ShadowFill) -> ShadowFill:
        db.add(fill)
        await db.flush()
        return fill

    async def get_by_position(
        self, db: AsyncSession, position_id: UUID
    ) -> list[ShadowFill]:
        result = await db.execute(
            select(ShadowFill)
            .where(ShadowFill.shadow_position_id == position_id)
            .order_by(ShadowFill.filled_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_strategy(
        self, db: AsyncSession, strategy_id: UUID
    ) -> list[ShadowFill]:
        result = await db.execute(
            select(ShadowFill)
            .where(ShadowFill.strategy_id == strategy_id)
            .order_by(ShadowFill.filled_at.desc())
        )
        return list(result.scalars().all())


class ShadowPositionRepository:
    async def create(
        self, db: AsyncSession, position: ShadowPosition
    ) -> ShadowPosition:
        db.add(position)
        await db.flush()
        return position

    async def get_open_by_strategy(
        self, db: AsyncSession, strategy_id: UUID
    ) -> list[ShadowPosition]:
        result = await db.execute(
            select(ShadowPosition)
            .where(
                ShadowPosition.strategy_id == strategy_id,
                ShadowPosition.status == "open",
            )
            .order_by(ShadowPosition.opened_at.asc())
        )
        return list(result.scalars().all())

    async def get_all_open(self, db: AsyncSession) -> list[ShadowPosition]:
        result = await db.execute(
            select(ShadowPosition)
            .where(ShadowPosition.status == "open")
            .order_by(ShadowPosition.opened_at.asc())
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        db: AsyncSession,
        strategy_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ShadowPosition], int]:
        query = select(ShadowPosition)
        count_query = select(func.count()).select_from(ShadowPosition)

        if strategy_id:
            query = query.where(ShadowPosition.strategy_id == strategy_id)
            count_query = count_query.where(ShadowPosition.strategy_id == strategy_id)
        if status:
            query = query.where(ShadowPosition.status == status)
            count_query = count_query.where(ShadowPosition.status == status)

        query = query.order_by(ShadowPosition.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        positions = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return positions, total

    async def get_by_id(
        self, db: AsyncSession, position_id: UUID
    ) -> ShadowPosition | None:
        result = await db.execute(
            select(ShadowPosition).where(ShadowPosition.id == position_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, db: AsyncSession, position: ShadowPosition
    ) -> ShadowPosition:
        await db.flush()
        return position

    async def get_comparison_stats(
        self, db: AsyncSession, strategy_id: UUID
    ) -> dict:
        """Get shadow vs real comparison stats for a strategy."""
        # Count closed shadow positions
        total_result = await db.execute(
            select(func.count()).select_from(ShadowPosition).where(
                ShadowPosition.strategy_id == strategy_id,
                ShadowPosition.status == "closed",
            )
        )
        shadow_trades = total_result.scalar_one()

        # Sum shadow PnL
        pnl_result = await db.execute(
            select(func.coalesce(func.sum(ShadowPosition.realized_pnl), Decimal("0")))
            .where(
                ShadowPosition.strategy_id == strategy_id,
                ShadowPosition.status == "closed",
            )
        )
        shadow_pnl = pnl_result.scalar_one()

        # Shadow wins
        wins_result = await db.execute(
            select(func.count()).select_from(ShadowPosition).where(
                ShadowPosition.strategy_id == strategy_id,
                ShadowPosition.status == "closed",
                ShadowPosition.realized_pnl > 0,
            )
        )
        shadow_wins = wins_result.scalar_one()

        shadow_win_rate = Decimal("0")
        if shadow_trades > 0:
            shadow_win_rate = Decimal(str(shadow_wins)) / Decimal(str(shadow_trades)) * 100

        return {
            "shadow_trades": shadow_trades,
            "shadow_pnl": shadow_pnl,
            "shadow_win_rate": shadow_win_rate,
        }
