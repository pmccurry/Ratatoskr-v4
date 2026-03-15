"""Integration test conftest — real PostgreSQL database.

Requires DATABASE_URL_TEST env var or defaults to:
postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test
"""

import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.base_model import Base

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test",
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create engine, create all tables, yield, drop all tables."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Per-test session with rollback for isolation."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# Entity fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def admin_user(db):
    """Create admin user for tests."""
    from app.auth.models import User

    user = User(
        email=f"admin-{uuid4().hex[:8]}@test.com",
        username=f"admin_{uuid4().hex[:8]}",
        password_hash="$2b$12$testhashedpassword000000000000000000000000000000",
        role="admin",
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def regular_user(db):
    """Create regular user for isolation tests."""
    from app.auth.models import User

    user = User(
        email=f"user-{uuid4().hex[:8]}@test.com",
        username=f"user_{uuid4().hex[:8]}",
        password_hash="$2b$12$testhashedpassword000000000000000000000000000000",
        role="user",
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


def _minimal_strategy_config() -> dict:
    """Return a minimal valid strategy config for tests."""
    return {
        "timeframe": "1h",
        "symbols": {"mode": "explicit", "list": ["AAPL"]},
        "entry_conditions": {
            "logic": "and",
            "conditions": [
                {
                    "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
                    "operator": "less_than",
                    "right": {"type": "value", "value": 30},
                }
            ],
        },
        "stop_loss": {"type": "percent", "value": 2.0},
        "position_sizing": {"method": "percent_equity", "value": 5, "max_positions": 3},
    }


@pytest_asyncio.fixture
async def sample_strategy(db, admin_user):
    """Create a basic enabled strategy with config version."""
    from app.strategies.models import Strategy, StrategyConfigVersion

    strategy = Strategy(
        user_id=admin_user.id,
        key=f"test_sma_{uuid4().hex[:8]}",
        name="Test SMA Crossover",
        description="Test strategy",
        market="equities",
        status="enabled",
    )
    db.add(strategy)
    await db.flush()

    config_version = StrategyConfigVersion(
        strategy_id=strategy.id,
        version="1.0.0",
        config_json=_minimal_strategy_config(),
        is_active=True,
    )
    db.add(config_version)
    await db.flush()

    return strategy


@pytest_asyncio.fixture
async def draft_strategy(db, admin_user):
    """Create a draft strategy."""
    from app.strategies.models import Strategy, StrategyConfigVersion

    strategy = Strategy(
        user_id=admin_user.id,
        key=f"test_draft_{uuid4().hex[:8]}",
        name="Test Draft Strategy",
        market="equities",
        status="draft",
    )
    db.add(strategy)
    await db.flush()

    config_version = StrategyConfigVersion(
        strategy_id=strategy.id,
        version="1.0.0",
        config_json=_minimal_strategy_config(),
        is_active=True,
    )
    db.add(config_version)
    await db.flush()

    return strategy


@pytest_asyncio.fixture
async def sample_position(db, admin_user, sample_strategy):
    """Create a long AAPL position."""
    from app.portfolio.models import Position

    now = datetime.now(timezone.utc)
    position = Position(
        user_id=admin_user.id,
        strategy_id=sample_strategy.id,
        symbol="AAPL",
        market="equities",
        side="long",
        qty=Decimal("100"),
        avg_entry_price=Decimal("150.00000000"),
        cost_basis=Decimal("15000.00"),
        current_price=Decimal("150.00000000"),
        market_value=Decimal("15000.00"),
        unrealized_pnl=Decimal("0.00"),
        unrealized_pnl_percent=Decimal("0.0000"),
        realized_pnl=Decimal("0.00"),
        total_fees=Decimal("1.00"),
        total_dividends_received=Decimal("0.00"),
        total_return=Decimal("0.00"),
        total_return_percent=Decimal("0.0000"),
        status="open",
        opened_at=now,
        highest_price_since_entry=Decimal("150.00000000"),
        lowest_price_since_entry=Decimal("150.00000000"),
        bars_held=0,
        contract_multiplier=1,
    )
    db.add(position)
    await db.flush()
    return position
