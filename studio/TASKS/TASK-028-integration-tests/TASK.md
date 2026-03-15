# TASK-028 — Integration Tests (Database-Backed)

## Goal

Write integration tests that exercise service + repository + database together. These tests use a real PostgreSQL test database, run migrations, and verify multi-step workflows end-to-end within the backend.

## Depends On

TASK-026 (test infrastructure), TASK-027 (unit tests)

## Scope

**In scope:**
- `tests/integration/conftest.py` — test database setup, session fixtures, cleanup
- `tests/integration/test_strategy_crud.py`
- `tests/integration/test_signal_lifecycle.py`
- `tests/integration/test_position_management.py`
- `tests/integration/test_risk_evaluation_flow.py`
- `tests/integration/test_bar_storage_and_aggregation.py`
- `tests/integration/test_dividend_processing.py`

**Out of scope:**
- E2E tests (full HTTP API tests — separate task)
- Frontend tests
- Application code changes
- Broker-connected tests

---

## Deliverables

### D1 — Integration test conftest (`tests/integration/conftest.py`)

Set up a real test database for integration tests:

```python
"""
Integration test conftest — real PostgreSQL database.

Requires DATABASE_URL_TEST env var or defaults to:
postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.app.common.base_model import Base

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test"
)

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create engine, create all tables, yield, drop all tables."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()

@pytest.fixture
async def db(engine):
    """Per-test session with rollback for isolation."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()  # each test gets clean state
```

**Entity fixtures:**

```python
@pytest.fixture
async def admin_user(db):
    """Create admin user for tests."""
    from backend.app.auth.models import User
    user = User(email="admin@test.com", password_hash="$2b$12$test", role="admin", status="active")
    db.add(user)
    await db.flush()
    return user

@pytest.fixture
async def regular_user(db):
    """Create regular user for isolation tests."""
    from backend.app.auth.models import User
    user = User(email="user@test.com", password_hash="$2b$12$test", role="user", status="active")
    db.add(user)
    await db.flush()
    return user

@pytest.fixture
async def sample_strategy(db, admin_user):
    """Create a basic enabled strategy."""
    from backend.app.strategies.models import Strategy
    strategy = Strategy(
        user_id=admin_user.id,
        name="Test SMA Crossover",
        key="test_sma_crossover",
        market="equities",
        timeframe="1h",
        status="enabled",
        config_json={...}  # minimal valid config
    )
    db.add(strategy)
    await db.flush()
    return strategy

@pytest.fixture
async def sample_position(db, admin_user, sample_strategy):
    """Create a long AAPL position."""
    from backend.app.portfolio.models import Position
    position = Position(
        user_id=admin_user.id,
        strategy_id=sample_strategy.id,
        symbol="AAPL",
        side="long",
        qty=Decimal("100"),
        avg_entry_price=Decimal("150.00"),
        status="open",
    )
    db.add(position)
    await db.flush()
    return position
```

Also create `backend/tests/integration/__init__.py`.

### D2 — `tests/integration/test_strategy_crud.py`

Test strategy creation, reading, updating, and lifecycle transitions through the service layer.

```python
class TestStrategyCreate:
    async def test_create_strategy_returns_draft(self, db, admin_user):
        """New strategy starts as draft"""

    async def test_create_strategy_generates_version(self, db, admin_user):
        """First version is 1"""

    async def test_create_duplicate_key_fails(self, db, admin_user):
        """Two strategies with same key → conflict error"""

class TestStrategyLifecycle:
    async def test_enable_draft(self, db, sample_strategy):
        """draft → enabled succeeds"""

    async def test_pause_enabled(self, db, sample_strategy):
        """enabled → paused succeeds"""

    async def test_resume_paused(self, db, sample_strategy):
        """paused → enabled succeeds"""

    async def test_disable_enabled(self, db, sample_strategy):
        """enabled → disabled succeeds"""

    async def test_invalid_transition_fails(self, db, sample_strategy):
        """draft → paused → error (invalid transition)"""

class TestStrategyUpdate:
    async def test_update_draft_no_new_version(self, db, sample_strategy):
        """Updating a draft does not increment version"""

    async def test_update_enabled_creates_new_version(self, db, sample_strategy):
        """Updating enabled strategy increments version"""

class TestStrategyQuery:
    async def test_list_by_user(self, db, admin_user, regular_user):
        """Admin sees all, regular user sees only own"""

    async def test_get_by_key(self, db, sample_strategy):
        """Retrieve strategy by unique key"""
```

### D3 — `tests/integration/test_signal_lifecycle.py`

Test the full signal lifecycle from creation through status transitions.

```python
class TestSignalCreation:
    async def test_create_signal_pending(self, db, sample_strategy, admin_user):
        """New signal starts as 'pending'"""

    async def test_signal_has_expires_at(self, db, sample_strategy, admin_user):
        """Signal created with expires_at based on config"""

    async def test_signal_dedup_rejects_duplicate(self, db, sample_strategy, admin_user):
        """Second identical signal within window → rejected"""

class TestSignalTransitions:
    async def test_pending_to_risk_approved(self, db):
        """Valid transition: pending → risk_approved"""

    async def test_pending_to_risk_rejected(self, db):
        """Valid transition: pending → risk_rejected"""

    async def test_risk_approved_to_order_filled(self, db):
        """Valid transition: risk_approved → order_filled"""

    async def test_invalid_transition_raises(self, db):
        """pending → order_filled (skipping risk) → error"""

class TestSignalExpiry:
    async def test_expired_signal_marked(self, db, sample_strategy, admin_user):
        """Signal past expires_at gets marked expired"""

    async def test_processed_signal_not_expired(self, db):
        """Signal in risk_approved not expired even if past TTL"""
```

### D4 — `tests/integration/test_position_management.py`

Test the full fill-to-position lifecycle through the portfolio service with real database writes.

```python
class TestNewPosition:
    async def test_buy_fill_creates_position(self, db, admin_user, sample_strategy):
        """Process a buy fill → new open position created with correct fields"""

    async def test_sell_fill_creates_short(self, db, admin_user, sample_strategy):
        """Process a sell fill → short position with negative qty convention"""

class TestScaleIn:
    async def test_second_buy_updates_position(self, db, sample_position):
        """Second buy fill → qty increases, avg_entry recalculated"""

    async def test_weighted_average_is_correct(self, db, sample_position):
        """100@150 + 50@160 = 150 @ $153.33"""

class TestScaleOut:
    async def test_partial_sell_records_pnl(self, db, sample_position):
        """Sell 50 of 100 → realized PnL recorded, position qty=50"""

    async def test_realized_pnl_entry_created(self, db, sample_position):
        """RealizedPnlEntry row created with correct gross and net PnL"""

class TestFullClose:
    async def test_full_close_zeros_position(self, db, sample_position):
        """Sell all 100 → position.qty=0, position.status=closed"""

    async def test_full_close_records_total_pnl(self, db, sample_position):
        """Total realized PnL matches (exit - entry) * qty - fees"""

class TestUserIsolation:
    async def test_user_a_cannot_see_user_b_positions(self, db, admin_user, regular_user):
        """Query positions for user B returns empty when only user A has positions"""

    async def test_user_a_cannot_close_user_b_position(self, db, admin_user, regular_user):
        """Attempting to close another user's position → error"""
```

### D5 — `tests/integration/test_risk_evaluation_flow.py`

Test the full risk evaluation pipeline with real risk config and position data.

```python
class TestRiskApproval:
    async def test_clean_signal_approved(self, db, admin_user, sample_strategy):
        """Signal with no risk violations → approved"""

    async def test_kill_switch_blocks_entry(self, db, admin_user, sample_strategy):
        """Activate kill switch → entry signal rejected"""

    async def test_kill_switch_allows_exit(self, db, admin_user, sample_strategy, sample_position):
        """Kill switch active → exit signal approved"""

class TestExposureLimits:
    async def test_symbol_exposure_rejection(self, db, admin_user, sample_strategy):
        """Signal that would exceed symbol exposure limit → rejected"""

    async def test_portfolio_exposure_rejection(self, db, admin_user):
        """Signal that would exceed total portfolio exposure → rejected"""

class TestDrawdownCheck:
    async def test_drawdown_within_limit_passes(self, db, admin_user):
        """Current drawdown under limit → pass"""

    async def test_drawdown_exceeds_limit_rejects(self, db, admin_user):
        """Current drawdown over limit → reject"""

    async def test_catastrophic_drawdown_activates_kill_switch(self, db, admin_user):
        """Drawdown exceeds catastrophic threshold → kill switch activated"""

class TestRiskModification:
    async def test_position_size_reduced_to_fit(self, db, admin_user, sample_strategy):
        """Signal qty too large → modified to fit within limits, status=risk_modified"""
```

### D6 — `tests/integration/test_bar_storage_and_aggregation.py`

Test bar ingestion, storage, and timeframe aggregation.

```python
class TestBarStorage:
    async def test_insert_bar(self, db):
        """Insert a single 1m bar → retrievable by symbol and timeframe"""

    async def test_batch_insert_bars(self, db):
        """Insert 100 bars in batch → all retrievable"""

    async def test_duplicate_bar_upsert(self, db):
        """Same symbol+timeframe+timestamp → update, not duplicate"""

    async def test_query_bars_by_range(self, db):
        """Query bars between start and end timestamp → correct subset"""

class TestBarAggregation:
    async def test_1m_to_1h_aggregation(self, db):
        """60 x 1m bars → 1 x 1h bar with correct OHLCV"""

    async def test_aggregation_open_is_first(self, db):
        """Aggregated open = first bar's open"""

    async def test_aggregation_close_is_last(self, db):
        """Aggregated close = last bar's close"""

    async def test_aggregation_high_is_max(self, db):
        """Aggregated high = max of all highs"""

    async def test_aggregation_low_is_min(self, db):
        """Aggregated low = min of all lows"""

    async def test_aggregation_volume_is_sum(self, db):
        """Aggregated volume = sum of all volumes"""

    async def test_incomplete_period_not_aggregated(self, db):
        """Only 45 of 60 1m bars → no 1h bar produced (partial)"""
```

### D7 — `tests/integration/test_dividend_processing.py`

Test dividend processing and stock split adjustment.

```python
class TestDividendProcessing:
    async def test_eligible_position_receives_dividend(self, db, sample_position):
        """Position held on ex-date → dividend payment created"""

    async def test_ineligible_position_no_dividend(self, db, sample_position):
        """Position opened after ex-date → no dividend"""

    async def test_dividend_credits_cash(self, db, sample_position):
        """Dividend processed on payable date → cash credited"""

    async def test_dividend_amount_correct(self, db, sample_position):
        """100 shares × $0.50 dividend = $50.00"""

class TestStockSplit:
    async def test_forward_split_adjusts_qty_and_price(self, db, sample_position):
        """2:1 split: qty 100→200, avg_entry $150→$75"""

    async def test_reverse_split_adjusts_qty_and_price(self, db, sample_position):
        """1:2 reverse split: qty 100→50, avg_entry $150→$300"""

    async def test_split_preserves_total_value(self, db, sample_position):
        """Pre-split value = post-split value (qty * price unchanged)"""

    async def test_split_adjusts_open_orders(self, db, sample_position):
        """Open limit orders adjusted for split ratio"""
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Integration conftest creates test database engine and per-test session with rollback |
| AC2 | Entity fixtures (admin_user, regular_user, sample_strategy, sample_position) work correctly |
| AC3 | Strategy CRUD tests cover create, lifecycle transitions, update versioning, and query by user |
| AC4 | Signal lifecycle tests cover creation, valid/invalid transitions, dedup, and expiry |
| AC5 | Position management tests cover all 4 fill types (new_open, scale_in, scale_out, full_close) |
| AC6 | User isolation test verifies user A cannot see/modify user B's data |
| AC7 | Risk evaluation tests cover approval, kill switch (entry blocked, exit allowed), exposure rejection, drawdown |
| AC8 | Bar storage tests cover insert, batch, upsert, and range query |
| AC9 | Bar aggregation tests verify OHLCV aggregation rules (open=first, close=last, high=max, low=min, volume=sum) |
| AC10 | Dividend tests cover eligibility, cash credit, and correct amount |
| AC11 | Stock split tests verify qty and price adjustment preserving total value |
| AC12 | All tests use `Decimal` for financial values |
| AC13 | All tests clean up after themselves (session rollback or explicit cleanup) |
| AC14 | `pytest tests/integration/ -v` runs without import errors (tests may fail if they find real bugs — that's acceptable) |
| AC15 | No application code modified |
| AC16 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/tests/integration/__init__.py` | Package marker |
| `backend/tests/integration/conftest.py` | Test DB setup, entity fixtures |
| `backend/tests/integration/test_strategy_crud.py` | Strategy service integration tests |
| `backend/tests/integration/test_signal_lifecycle.py` | Signal lifecycle integration tests |
| `backend/tests/integration/test_position_management.py` | Position/PnL integration tests |
| `backend/tests/integration/test_risk_evaluation_flow.py` | Risk pipeline integration tests |
| `backend/tests/integration/test_bar_storage_and_aggregation.py` | Bar storage integration tests |
| `backend/tests/integration/test_dividend_processing.py` | Dividend/split integration tests |

## Files NOT to Touch

Everything outside `backend/tests/`.

## Builder Notes

- Integration tests need a running PostgreSQL instance. If the builder environment doesn't have one, the tests can be written correctly but will fail to connect — note this in BUILDER_OUTPUT.md.
- Use the actual service classes from the application code. Don't re-implement logic in tests.
- The `db` fixture uses session rollback for isolation. Each test starts with a clean slate.
- If a model import fails (wrong path, missing field), document the actual import path in BUILDER_OUTPUT.md.
- The `config_json` for `sample_strategy` should be a minimal valid strategy config. Check `test_strategy_validation.py` from TASK-026 for what constitutes a valid config.

## References

- cross_cutting_specs.md §6 — Testing Strategy (integration test files, test database, fixtures)
- cross_cutting_specs.md §6 — Critical Paths Requiring Integration Tests (full list)
- portfolio_module_spec.md §Fill Processing (4 fill types, weighted avg, PnL)
- portfolio_module_spec.md §Dividends and Stock Splits
- signals_module_spec.md §Signal Lifecycle (transitions, dedup, expiry)
- risk_engine_module_spec.md §Risk Check Sequence
- market_data_module_spec.md §Bar Storage (upsert, aggregation)
