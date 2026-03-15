"""Unit tests for forex account pool allocation logic."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.paper_trading.forex_pool.pool_manager import ForexPoolManager


# ---------------------------------------------------------------------------
# Mock objects
# ---------------------------------------------------------------------------

@dataclass
class MockBrokerAccount:
    id: object = None
    broker: str = "oanda"
    account_id: str = "forex_pool_1"
    is_active: bool = True
    capital_allocation: Decimal = Decimal("25000")

    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()


@dataclass
class MockAllocation:
    id: object = None
    account_id: object = None
    strategy_id: object = None
    symbol: str = "EUR_USD"
    side: str = "buy"
    status: str = "active"
    allocated_at: datetime = None

    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()
        if self.account_id is None:
            self.account_id = uuid4()
        if self.strategy_id is None:
            self.strategy_id = uuid4()
        if self.allocated_at is None:
            self.allocated_at = datetime.now(timezone.utc)


def _pool(pool_size: int = 4) -> ForexPoolManager:
    return ForexPoolManager(
        pool_size=pool_size,
        capital_per_account=Decimal("25000"),
    )


# ---------------------------------------------------------------------------
# Allocation tests
# ---------------------------------------------------------------------------

class TestForexPoolAllocation:
    @pytest.mark.asyncio
    async def test_allocate_available_account(self):
        """4 accounts, none allocated for EUR_USD → allocate first available."""
        pool = _pool()
        account = MockBrokerAccount(account_id="forex_pool_1")
        pool._account_repo = MagicMock()
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=account)

        db = MagicMock()
        result = await pool.find_available_account(db, "EUR_USD")
        assert result is not None
        assert result.account_id == "forex_pool_1"

    @pytest.mark.asyncio
    async def test_reject_when_all_accounts_busy(self):
        """All accounts have active EUR_USD allocations → no account available."""
        pool = _pool()
        pool._account_repo = MagicMock()
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=None)

        db = MagicMock()
        result = await pool.find_available_account(db, "EUR_USD")
        assert result is None

    @pytest.mark.asyncio
    async def test_same_account_different_pair(self):
        """Account allocated for EUR_USD can also take GBP_USD."""
        pool = _pool()
        account = MockBrokerAccount(account_id="forex_pool_1")
        # Account is available for GBP_USD (even if occupied for EUR_USD)
        pool._account_repo = MagicMock()
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=account)

        db = MagicMock()
        result = await pool.find_available_account(db, "GBP_USD")
        assert result is not None

    @pytest.mark.asyncio
    async def test_allocate_records_strategy(self):
        """Allocation records which strategy allocated the account."""
        pool = _pool()
        allocation = MockAllocation()
        pool._allocation_repo = MagicMock()
        pool._allocation_repo.create = AsyncMock(return_value=allocation)

        db = MagicMock()
        account_id = uuid4()
        strategy_id = uuid4()
        result = await pool.allocate(db, account_id, strategy_id, "EUR_USD", "buy")
        assert result is not None
        pool._allocation_repo.create.assert_called_once()
        # Verify the allocation object passed to create
        call_args = pool._allocation_repo.create.call_args
        alloc = call_args[0][1]  # Second positional arg (db, allocation)
        assert alloc.strategy_id == strategy_id
        assert alloc.symbol == "EUR_USD"
        assert alloc.side == "buy"
        assert alloc.status == "active"

    @pytest.mark.asyncio
    async def test_release_on_position_close(self):
        """Close position → release allocation."""
        pool = _pool()
        pool._allocation_repo = MagicMock()
        pool._allocation_repo.release = AsyncMock()

        db = MagicMock()
        strategy_id = uuid4()
        await pool.release(db, strategy_id, "EUR_USD")
        pool._allocation_repo.release.assert_called_once_with(db, strategy_id, "EUR_USD")

    @pytest.mark.asyncio
    async def test_pool_size_configuration(self):
        """Pool of 4 accounts is created with correct size."""
        pool = _pool(pool_size=4)
        assert pool._pool_size == 4

    @pytest.mark.asyncio
    async def test_capital_per_account(self):
        """Each account has correct capital allocation."""
        pool = _pool()
        assert pool._capital_per_account == Decimal("25000")


# ---------------------------------------------------------------------------
# Contention scenarios
# ---------------------------------------------------------------------------

class TestForexPoolContention:
    @pytest.mark.asyncio
    async def test_sequential_allocations_same_pair(self):
        """Two strategies requesting same pair → second may fail if pool full."""
        pool = _pool(pool_size=2)

        # First allocation succeeds
        account1 = MockBrokerAccount(account_id="forex_pool_1")
        pool._account_repo = MagicMock()
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=account1)

        db = MagicMock()
        result1 = await pool.find_available_account(db, "EUR_USD")
        assert result1 is not None

        # Second allocation: mock returns account2
        account2 = MockBrokerAccount(account_id="forex_pool_2")
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=account2)
        result2 = await pool.find_available_account(db, "EUR_USD")
        assert result2 is not None
        assert result2.account_id != result1.account_id

        # Third allocation: pool full for EUR_USD
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=None)
        result3 = await pool.find_available_account(db, "EUR_USD")
        assert result3 is None

    @pytest.mark.asyncio
    async def test_release_makes_account_available_again(self):
        """After release, the account can be allocated again."""
        pool = _pool()
        pool._allocation_repo = MagicMock()
        pool._allocation_repo.release = AsyncMock()

        # Release an allocation
        strategy_id = uuid4()
        db = MagicMock()
        await pool.release(db, strategy_id, "EUR_USD")

        # Now the account should be available again
        account = MockBrokerAccount()
        pool._account_repo = MagicMock()
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=account)
        result = await pool.find_available_account(db, "EUR_USD")
        assert result is not None

    @pytest.mark.asyncio
    async def test_different_pairs_dont_contend(self):
        """Two strategies trading different pairs don't contend for accounts."""
        pool = _pool(pool_size=1)
        account = MockBrokerAccount(account_id="forex_pool_1")
        pool._account_repo = MagicMock()
        pool._account_repo.get_available_for_symbol = AsyncMock(return_value=account)

        db = MagicMock()
        # Both EUR_USD and GBP_USD can use the same account
        result1 = await pool.find_available_account(db, "EUR_USD")
        assert result1 is not None
        result2 = await pool.find_available_account(db, "GBP_USD")
        assert result2 is not None
