"""Forex account pool manager — FIFO netting compliance."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.forex_pool.allocation import (
    AccountAllocationRepository,
    BrokerAccountRepository,
)
from app.paper_trading.models import AccountAllocation, BrokerAccount

logger = logging.getLogger(__name__)


class ForexPoolManager:
    """Manages the forex account pool for FIFO netting compliance.

    Each virtual account can hold multiple pairs but only ONE position
    per pair. Strategies are allocated accounts per-pair when they
    open positions. Accounts are released when positions close.
    """

    def __init__(self, pool_size: int, capital_per_account: Decimal):
        self._pool_size = pool_size
        self._capital_per_account = capital_per_account
        self._account_repo = BrokerAccountRepository()
        self._allocation_repo = AccountAllocationRepository()

    async def find_available_account(
        self, db: AsyncSession, symbol: str
    ) -> BrokerAccount | None:
        """Find an account with no active allocation for this pair."""
        return await self._account_repo.get_available_for_symbol(db, symbol)

    async def allocate(
        self,
        db: AsyncSession,
        account_id: UUID,
        strategy_id: UUID,
        symbol: str,
        side: str,
    ) -> AccountAllocation:
        """Create an active allocation for a strategy on an account."""
        now = datetime.now(timezone.utc)
        allocation = AccountAllocation(
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            status="active",
            allocated_at=now,
        )
        result = await self._allocation_repo.create(db, allocation)
        logger.info(
            "Account %s allocated to strategy %s for %s (%s)",
            account_id, strategy_id, symbol, side,
        )
        return result

    async def release(
        self, db: AsyncSession, strategy_id: UUID, symbol: str
    ) -> None:
        """Release the allocation when a position closes."""
        await self._allocation_repo.release(db, strategy_id, symbol)
        logger.info(
            "Account released for strategy %s symbol %s",
            strategy_id, symbol,
        )

    async def get_pool_status(self, db: AsyncSession) -> dict:
        """Return current pool status for dashboard."""
        accounts = await self._account_repo.get_all_active(db)
        all_allocations = await self._allocation_repo.get_all_active(db)

        # Build per-account allocation map
        account_allocs: dict[UUID, list[dict]] = {}
        for alloc in all_allocations:
            if alloc.account_id not in account_allocs:
                account_allocs[alloc.account_id] = []
            account_allocs[alloc.account_id].append({
                "symbol": alloc.symbol,
                "side": alloc.side,
                "strategy_id": str(alloc.strategy_id),
                "since": alloc.allocated_at.isoformat(),
            })

        # Build per-pair capacity
        pair_capacity: dict[str, dict] = {}
        for alloc in all_allocations:
            if alloc.symbol not in pair_capacity:
                pair_capacity[alloc.symbol] = {
                    "occupied": 0,
                    "total": len(accounts),
                    "available": len(accounts),
                }
            pair_capacity[alloc.symbol]["occupied"] += 1
            pair_capacity[alloc.symbol]["available"] = (
                pair_capacity[alloc.symbol]["total"]
                - pair_capacity[alloc.symbol]["occupied"]
            )

        account_list = []
        fully_empty = 0
        for acct in accounts:
            allocs = account_allocs.get(acct.id, [])
            account_list.append({
                "id": str(acct.id),
                "label": acct.label,
                "account_id": acct.account_id,
                "allocations": allocs,
            })
            if not allocs:
                fully_empty += 1

        return {
            "accounts": account_list,
            "pair_capacity": pair_capacity,
            "total_accounts": len(accounts),
            "fully_empty": fully_empty,
        }

    async def seed_accounts(self, db: AsyncSession) -> int:
        """Create or update pool accounts by slot number.

        Uses the virtual ID pattern `forex_pool_{N}` as the stable slot
        identifier. When a real OANDA account mapping is configured, the
        virtual record is updated in-place (account_id, type, credentials).
        This prevents orphaned records on virtual-to-real transitions.
        """
        from app.common.config import get_settings
        settings = get_settings()

        created = 0
        for i in range(1, self._pool_size + 1):
            slot_id = f"forex_pool_{i}"
            real_account_id = getattr(settings, f"oanda_pool_account_{i}", "")
            real_token = getattr(settings, f"oanda_pool_token_{i}", "")

            if real_account_id:
                target_account_id = real_account_id
                account_type = "paper_live"
                creds_key = f"OANDA_POOL_TOKEN_{i}" if real_token else None
                label = f"Forex Pool Account {i} (OANDA)"
            else:
                target_account_id = slot_id
                account_type = "paper_virtual"
                creds_key = None
                label = f"Forex Pool Account {i}"

            # Look up by the stable slot ID first
            existing = await self._account_repo.get_by_account_id(db, slot_id)

            # Also check if a real-mapped version already exists
            if not existing and real_account_id:
                existing = await self._account_repo.get_by_account_id(db, real_account_id)

            if existing:
                # Update in-place if anything changed
                changed = False
                if existing.account_id != target_account_id:
                    existing.account_id = target_account_id
                    changed = True
                if existing.account_type != account_type:
                    existing.account_type = account_type
                    changed = True
                if existing.credentials_env_key != creds_key:
                    existing.credentials_env_key = creds_key
                    changed = True
                if existing.label != label:
                    existing.label = label
                    changed = True
                if changed:
                    logger.info("Pool slot %d updated: %s (%s)", i, target_account_id, account_type)
                continue

            account = BrokerAccount(
                broker="oanda",
                account_id=target_account_id,
                account_type=account_type,
                label=label,
                is_active=True,
                capital_allocation=self._capital_per_account,
                credentials_env_key=creds_key,
            )
            await self._account_repo.create(db, account)
            created += 1

            if real_account_id:
                logger.info("Pool slot %d mapped to OANDA: %s", i, target_account_id)
            else:
                logger.info("Pool slot %d using virtual mode", i)

        logger.info("Seeded %d forex pool accounts (pool_size=%d)", created, self._pool_size)
        return created
