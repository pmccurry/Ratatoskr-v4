"""Portfolio repository — all database access."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import CashBalance, PortfolioMeta, Position


class PositionRepository:
    async def create(self, db: AsyncSession, position: Position) -> Position:
        db.add(position)
        await db.flush()
        return position

    async def get_by_id(self, db: AsyncSession, position_id: UUID) -> Position | None:
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        return result.scalar_one_or_none()

    async def get_open_by_strategy_symbol(
        self, db: AsyncSession, strategy_id: UUID, symbol: str
    ) -> Position | None:
        result = await db.execute(
            select(Position).where(
                Position.strategy_id == strategy_id,
                Position.symbol == symbol,
                Position.status == "open",
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_open_by_strategy(
        self, db: AsyncSession, strategy_id: UUID
    ) -> list[Position]:
        result = await db.execute(
            select(Position).where(
                Position.strategy_id == strategy_id,
                Position.status == "open",
            ).order_by(Position.opened_at.asc())
        )
        return list(result.scalars().all())

    async def get_all_open(self, db: AsyncSession, user_id: UUID) -> list[Position]:
        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.status == "open",
            ).order_by(Position.opened_at.asc())
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        status: str | None = None,
        market: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Position], int]:
        query = select(Position).where(Position.user_id == user_id)
        count_query = select(func.count()).select_from(Position).where(Position.user_id == user_id)

        filters = []
        if strategy_id:
            filters.append(Position.strategy_id == strategy_id)
        if symbol:
            filters.append(Position.symbol == symbol)
        if status:
            filters.append(Position.status == status)
        if market:
            filters.append(Position.market == market)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(Position.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        positions = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return positions, total

    async def get_open_positions_count(
        self, db: AsyncSession, strategy_id: UUID
    ) -> int:
        result = await db.execute(
            select(func.count()).select_from(Position).where(
                Position.strategy_id == strategy_id,
                Position.status == "open",
            )
        )
        return result.scalar_one()

    async def get_open_by_symbol(
        self, db: AsyncSession, symbol: str
    ) -> list[Position]:
        """All open positions for a symbol across ALL strategies (for exposure calc)."""
        result = await db.execute(
            select(Position).where(
                Position.symbol == symbol,
                Position.status == "open",
            )
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, position: Position) -> Position:
        await db.flush()
        return position

    async def get_all_open_for_user(
        self, db: AsyncSession, user_id: UUID
    ) -> list[Position]:
        """All open positions for a user (for portfolio-level calculations)."""
        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.status == "open",
            ).order_by(Position.opened_at.asc())
        )
        return list(result.scalars().all())

    async def get_closed_filtered(
        self,
        db: AsyncSession,
        user_id: UUID,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Position], int]:
        query = select(Position).where(
            Position.user_id == user_id,
            Position.status == "closed",
        )
        count_query = select(func.count()).select_from(Position).where(
            Position.user_id == user_id,
            Position.status == "closed",
        )

        if date_start:
            query = query.where(Position.closed_at >= date_start)
            count_query = count_query.where(Position.closed_at >= date_start)
        if date_end:
            query = query.where(Position.closed_at <= date_end)
            count_query = count_query.where(Position.closed_at <= date_end)

        query = query.order_by(Position.closed_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        positions = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return positions, total

    async def get_today_closed_losses(
        self, db: AsyncSession, user_id: UUID
    ) -> Decimal:
        """Sum of realized losses today (where realized_pnl < 0)."""
        now = datetime.now(timezone.utc)
        # Approximate ET midnight as 05:00 UTC
        today_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now.hour < 5:
            today_start -= timedelta(days=1)

        result = await db.execute(
            select(func.coalesce(func.sum(Position.realized_pnl), Decimal("0")))
            .where(
                Position.user_id == user_id,
                Position.status == "closed",
                Position.closed_at >= today_start,
                Position.realized_pnl < 0,
            )
        )
        return abs(result.scalar_one())


class CashBalanceRepository:
    async def get_by_scope(
        self, db: AsyncSession, account_scope: str, user_id: UUID
    ) -> CashBalance | None:
        result = await db.execute(
            select(CashBalance).where(
                CashBalance.account_scope == account_scope,
                CashBalance.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession, user_id: UUID) -> list[CashBalance]:
        result = await db.execute(
            select(CashBalance).where(CashBalance.user_id == user_id)
            .order_by(CashBalance.account_scope.asc())
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, cash: CashBalance) -> CashBalance:
        db.add(cash)
        await db.flush()
        return cash

    async def update_balance(
        self, db: AsyncSession, account_scope: str,
        user_id: UUID, delta: Decimal
    ) -> CashBalance:
        """Atomically adjust balance by delta (positive=credit, negative=debit)."""
        cash = await self.get_by_scope(db, account_scope, user_id)
        if cash is None:
            cash = CashBalance(
                account_scope=account_scope,
                balance=delta,
                user_id=user_id,
            )
            db.add(cash)
            await db.flush()
            return cash

        cash.balance = cash.balance + delta
        await db.flush()
        return cash

    async def get_total_cash(self, db: AsyncSession, user_id: UUID) -> Decimal:
        result = await db.execute(
            select(func.coalesce(func.sum(CashBalance.balance), Decimal("0")))
            .where(CashBalance.user_id == user_id)
        )
        return result.scalar_one()


class PortfolioMetaRepository:
    async def get(self, db: AsyncSession, key: str, user_id: UUID) -> str | None:
        result = await db.execute(
            select(PortfolioMeta.value).where(
                PortfolioMeta.key == key,
                PortfolioMeta.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def set(
        self, db: AsyncSession, key: str, value: str, user_id: UUID
    ) -> None:
        result = await db.execute(
            select(PortfolioMeta).where(
                PortfolioMeta.key == key,
                PortfolioMeta.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            meta = PortfolioMeta(key=key, value=value, user_id=user_id)
            db.add(meta)
        await db.flush()

    async def get_all(self, db: AsyncSession, user_id: UUID) -> dict[str, str]:
        result = await db.execute(
            select(PortfolioMeta).where(PortfolioMeta.user_id == user_id)
        )
        return {m.key: m.value for m in result.scalars().all()}
