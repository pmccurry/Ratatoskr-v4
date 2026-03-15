"""Forex pool allocation repository — database access for accounts and allocations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.models import AccountAllocation, BrokerAccount


class BrokerAccountRepository:
    async def get_all_active(self, db: AsyncSession) -> list[BrokerAccount]:
        result = await db.execute(
            select(BrokerAccount).where(BrokerAccount.is_active == True)
            .order_by(BrokerAccount.account_id.asc())
        )
        return list(result.scalars().all())

    async def get_available_for_symbol(
        self, db: AsyncSession, symbol: str
    ) -> BrokerAccount | None:
        """Find an active account with no active allocation for this symbol."""
        # Subquery: account IDs that have an active allocation for this symbol
        occupied_subq = (
            select(AccountAllocation.account_id)
            .where(
                AccountAllocation.symbol == symbol,
                AccountAllocation.status == "active",
            )
        ).scalar_subquery()

        result = await db.execute(
            select(BrokerAccount)
            .where(
                BrokerAccount.is_active == True,
                BrokerAccount.id.not_in(
                    select(AccountAllocation.account_id)
                    .where(
                        AccountAllocation.symbol == symbol,
                        AccountAllocation.status == "active",
                    )
                ),
            )
            .order_by(BrokerAccount.account_id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, account: BrokerAccount) -> BrokerAccount:
        db.add(account)
        await db.flush()
        return account

    async def get_by_id(self, db: AsyncSession, account_id: UUID) -> BrokerAccount | None:
        result = await db.execute(
            select(BrokerAccount).where(BrokerAccount.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_account_id(self, db: AsyncSession, account_id: str) -> BrokerAccount | None:
        """Get by the string account_id (e.g., 'forex_pool_1')."""
        result = await db.execute(
            select(BrokerAccount).where(BrokerAccount.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count()).select_from(BrokerAccount)
        )
        return result.scalar_one()


class AccountAllocationRepository:
    async def create(
        self, db: AsyncSession, allocation: AccountAllocation
    ) -> AccountAllocation:
        db.add(allocation)
        await db.flush()
        return allocation

    async def get_active(
        self,
        db: AsyncSession,
        account_id: UUID | None = None,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
    ) -> list[AccountAllocation]:
        query = select(AccountAllocation).where(
            AccountAllocation.status == "active"
        )
        if account_id:
            query = query.where(AccountAllocation.account_id == account_id)
        if strategy_id:
            query = query.where(AccountAllocation.strategy_id == strategy_id)
        if symbol:
            query = query.where(AccountAllocation.symbol == symbol)

        result = await db.execute(query.order_by(AccountAllocation.allocated_at.asc()))
        return list(result.scalars().all())

    async def release(
        self, db: AsyncSession, strategy_id: UUID, symbol: str
    ) -> None:
        """Release the active allocation for a strategy+symbol."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(AccountAllocation).where(
                AccountAllocation.strategy_id == strategy_id,
                AccountAllocation.symbol == symbol,
                AccountAllocation.status == "active",
            )
        )
        allocation = result.scalar_one_or_none()
        if allocation:
            allocation.status = "released"
            allocation.released_at = now
            await db.flush()

    async def get_all_active(self, db: AsyncSession) -> list[AccountAllocation]:
        result = await db.execute(
            select(AccountAllocation).where(AccountAllocation.status == "active")
            .order_by(AccountAllocation.allocated_at.asc())
        )
        return list(result.scalars().all())
