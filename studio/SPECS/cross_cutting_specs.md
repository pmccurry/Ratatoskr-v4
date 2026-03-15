# CROSS_CUTTING_SPECS — Full Engineering Spec

## Purpose

Define the patterns and conventions every module must follow.
These specs ensure consistency across the entire codebase. When a builder
agent implements any module, these specs tell them HOW to implement,
not just WHAT.

---

## 1. Database and Persistence

### Database Engine

PostgreSQL with SQLAlchemy 2.x async (asyncpg driver).

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trading_platform
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
```

### Session Management

Every API request gets a database session that lives for the request duration.
Created at start, committed on success, rolled back on error, closed at end.

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

Background tasks (strategy runner, mark-to-market, backfill) manage their
own sessions following the same pattern: create, work, commit/rollback, close.

### Repository Pattern

Each module has a repository layer for all database access.
Services call repositories. Services never write SQL directly.

```
Router → Service → Repository → Database
```

Repository naming conventions:

```python
class StrategyRepository:
    async def get_by_id(self, id: UUID) -> Strategy | None
    async def get_by_key(self, key: str) -> Strategy | None
    async def get_by_user(self, user_id: UUID) -> list[Strategy]
    async def get_all(self) -> list[Strategy]
    async def get_by_status(self, status: str) -> list[Strategy]
    async def create(self, entity: Strategy) -> Strategy
    async def update(self, entity: Strategy) -> Strategy
    async def delete(self, id: UUID) -> bool
```

Repository methods take and return domain models or None.
Never raw dicts. Never tuples.

### SQLAlchemy Model Conventions

All models inherit common base fields:

```python
class Base:
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, on_update=utcnow)
```

Column naming rules:

```
snake_case for all columns
_id suffix for foreign keys       (strategy_id, user_id)
_at suffix for timestamps          (created_at, filled_at, opened_at)
_json suffix for JSON columns      (config_json, details_json, payload_json)
_percent suffix for percentages    (drawdown_percent, exposure_percent)
_bps suffix for basis points       (slippage_bps)
```

Data type rules:

```
IDs:         UUID (always)
Timestamps:  datetime, UTC, timezone-aware (always)
Money/Price: Decimal (never float)
Percentages: Decimal (never float)
JSON blobs:  JSONB column type in PostgreSQL
Booleans:    bool (never int 0/1)
Enums:       str with defined allowed values (not Python Enum in DB)
```

### Alembic Migrations

Every schema change goes through an Alembic migration.
No manual DDL. No model changes without a corresponding migration.

Migration file naming:

```
migrations/versions/
  001_create_users_table.py
  002_create_strategies_table.py
  003_create_ohlcv_bars_table.py
```

Rules:
- One migration per logical change (don't combine unrelated changes)
- Migrations must be reversible (include downgrade function)
- Never modify a migration that has been applied — create a new one
- Test migrations against a fresh database before committing

Migration commands:

```bash
alembic revision --autogenerate -m "description_of_change"
alembic upgrade head
alembic downgrade -1
```

### Connection Pooling

```
DATABASE_POOL_SIZE=20         (concurrent connections)
DATABASE_MAX_OVERFLOW=10      (temporary extra connections under load)
DATABASE_POOL_TIMEOUT=30      (seconds to wait for a connection)
```

Pool size of 20 handles API server, background tasks, and strategy
evaluations concurrently without contention.

---

## 2. Error Handling

### Domain Error Base Class

Each module defines its own domain errors inheriting from a common base:

```python
class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
```

Module-specific errors:

```python
class StrategyNotFoundError(DomainError):
    def __init__(self, strategy_id: UUID):
        super().__init__(
            code="STRATEGY_NOT_FOUND",
            message=f"Strategy {strategy_id} not found",
            details={"strategy_id": str(strategy_id)}
        )

class InsufficientCashError(DomainError):
    def __init__(self, required: Decimal, available: Decimal):
        super().__init__(
            code="INSUFFICIENT_CASH",
            message=f"Insufficient cash: need ${required}, have ${available}",
            details={"required": str(required), "available": str(available)}
        )
```

### Error Code Catalog

Every error has a unique code string, namespaced by module:

```
# Auth
AUTH_INVALID_CREDENTIALS
AUTH_ACCOUNT_LOCKED
AUTH_ACCOUNT_SUSPENDED
AUTH_TOKEN_EXPIRED
AUTH_TOKEN_INVALID
AUTH_INSUFFICIENT_PERMISSIONS

# Strategy
STRATEGY_NOT_FOUND
STRATEGY_VALIDATION_FAILED
STRATEGY_NOT_ENABLED
STRATEGY_CONFIG_INVALID
STRATEGY_ALREADY_EXISTS

# Signal
SIGNAL_NOT_FOUND
SIGNAL_VALIDATION_FAILED
SIGNAL_DUPLICATE
SIGNAL_EXPIRED
SIGNAL_CANNOT_CANCEL

# Risk
RISK_KILL_SWITCH_ACTIVE
RISK_EXPOSURE_LIMIT
RISK_DRAWDOWN_LIMIT
RISK_DAILY_LOSS_LIMIT
RISK_NO_AVAILABLE_ACCOUNT
RISK_DUPLICATE_ORDER
RISK_MAX_POSITIONS

# Paper Trading
PAPER_TRADING_INSUFFICIENT_CASH
PAPER_TRADING_BROKER_ERROR
PAPER_TRADING_INVALID_ORDER
PAPER_TRADING_NO_REFERENCE_PRICE

# Portfolio
PORTFOLIO_POSITION_NOT_FOUND
PORTFOLIO_INVALID_OPERATION
PORTFOLIO_NO_OPEN_POSITION

# Market Data
MARKET_DATA_SYMBOL_NOT_FOUND
MARKET_DATA_STALE
MARKET_DATA_BACKFILL_FAILED
MARKET_DATA_CONNECTION_ERROR

# System
INTERNAL_ERROR
VALIDATION_ERROR
NOT_FOUND
```

### API Error Response Format

Every API error returns the same JSON structure:

```json
{
  "error": {
    "code": "STRATEGY_VALIDATION_FAILED",
    "message": "Strategy validation failed",
    "details": {
      "errors": [
        {
          "field": "entry_conditions[2].left.params.period",
          "message": "RSI period must be between 2 and 200, got 500"
        }
      ]
    }
  }
}
```

### HTTP Status Code Mapping

```
400  Bad Request           — validation errors, malformed input
401  Unauthorized          — missing or invalid auth token
403  Forbidden             — valid token but insufficient permissions
404  Not Found             — entity doesn't exist
409  Conflict              — duplicate, state conflict
422  Unprocessable Entity  — business rule violation (valid input, wrong state)
423  Locked                — account locked
429  Too Many Requests     — rate limit exceeded
500  Internal Server Error — unhandled exception
```

### Global Exception Handler

```python
@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError):
    status = map_error_code_to_status(exc.code)
    return JSONResponse(
        status_code=status,
        content={"error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details
        }}
    )

@app.exception_handler(Exception)
async def unhandled_error_handler(request, exc: Exception):
    logger.exception("Unhandled exception")
    # Never expose internals to client
    return JSONResponse(
        status_code=500,
        content={"error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "details": {}
        }}
    )
```

### No Silent Failures in Trading Logic

Critical rule for signals, risk, paper trading, and portfolio modules:

```
- Every error is logged with full context
- Every error produces an audit event
- No except: pass or bare except blocks
- No swallowing errors without logging
- If an error occurs during position management, alert the user
```

Non-trading modules (market data ingestion, metrics collection) can be
more tolerant — a dropped bar is not catastrophic. But anything that
affects positions or money must fail loudly.

---

## 3. Configuration System

### Settings Loading

All configuration loads from environment variables via Pydantic Settings:

```python
class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20

    # Auth
    auth_jwt_secret_key: str
    auth_access_token_expire_minutes: int = 15

    # Market Data
    alpaca_api_key: str
    alpaca_api_secret: str

    # ... all other settings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
```

Settings are loaded once at startup and injected via FastAPI dependency.
Modules never read environment variables directly.

### Environment Files

```
.env.example     — committed to repo, documents all variables with defaults
.env             — local development, NOT committed (.gitignore)
.env.test        — test environment settings
```

### Required vs Optional Settings

Required settings — app refuses to start without them:

```
DATABASE_URL
AUTH_JWT_SECRET_KEY
ALPACA_API_KEY
ALPACA_API_SECRET
```

Optional settings — have sensible defaults:

```
Everything else (pool sizes, intervals, thresholds, etc.)
```

Application validates required settings at startup with a clear error
message listing what's missing.

### Per-Module Config

Each module has its own config class:

```python
class MarketDataConfig:
    alpaca_api_key: str
    alpaca_api_secret: str
    ws_reconnect_initial_delay_sec: int
    ws_reconnect_max_delay_sec: int
```

Modules only see their own config values. The global Settings object is
not passed around directly.

### Runtime-Configurable vs Startup-Only

```
Startup-only (environment variables, read once):
  - Database connection
  - Broker credentials
  - JWT secret
  - Log level
  - Pool sizes

Runtime-configurable (stored in database, editable via admin API):
  - Risk config (max drawdown, exposure limits)
  - Alert rules (thresholds, enabled/disabled)
  - Universe filter parameters
  - Strategy configs
```

Runtime settings take effect immediately without restart.

---

## 4. Inter-Module Interfaces

### Communication Pattern

Modules communicate through service-layer function calls only.
No direct repository access across module boundaries.
No importing models from another module's internals.

```
Allowed:
  strategy_service calls market_data_service.get_bars()
  paper_trading_service calls portfolio_service.process_fill()

Not allowed:
  strategy_service imports market_data.models.OHLCVBar
  paper_trading directly queries the positions table
  risk_service directly modifies the signals table
```

### Service Interface Contracts

**market_data_service (used by: strategies, risk, portfolio):**

```python
async def get_bars(symbol, timeframe, limit=None, start=None, end=None) -> list[Bar]
async def get_latest_close(symbol, timeframe="1m") -> Decimal
async def get_option_chain(underlying_symbol) -> OptionChain
async def get_health() -> MarketDataHealth
async def get_upcoming_dividends(symbol) -> list[DividendAnnouncement]
async def get_dividend_yield(symbol) -> Decimal
async def get_next_ex_date(symbol) -> date | None
async def is_symbol_on_watchlist(symbol) -> bool
async def get_watchlist(market=None) -> list[WatchlistEntry]
```

**strategy_service (used by: API layer, strategy runner):**

```python
async def get_strategies(user) -> list[Strategy]
async def get_strategy(id, user) -> Strategy
async def get_enabled_strategies() -> list[Strategy]
async def get_strategy_config(strategy_id) -> StrategyConfig
```

**signal_service (used by: strategy runner, risk engine):**

```python
async def create_signal(signal_data) -> Signal
async def get_pending_signals() -> list[Signal]
async def update_signal_status(signal_id, status) -> Signal
async def cancel_signal(signal_id) -> Signal
```

**risk_service (used by: paper trading, API layer):**

```python
async def evaluate_signal(signal) -> RiskDecision
async def get_risk_config() -> RiskConfig
async def get_kill_switch_status() -> KillSwitchStatus
async def get_exposure() -> ExposureSnapshot
async def get_drawdown() -> DrawdownState
```

**paper_trading_service (used by: after risk approval, API layer):**

```python
async def process_approved_signal(signal, risk_decision) -> PaperOrder
async def get_forex_pool_status() -> PoolStatus
```

**portfolio_service (used by: strategy runner, risk, paper trading, API):**

```python
async def process_fill(fill) -> Position
async def get_positions(user, strategy_id=None, status="open") -> list[Position]
async def get_equity(user_id=None) -> Decimal
async def get_cash_balance(user_id=None, account_scope=None) -> Decimal
async def get_peak_equity(user_id=None) -> Decimal
async def get_portfolio_summary(user) -> PortfolioSummary
```

**event_service (used by: ALL modules):**

```python
async def emit(event_type, category, severity, summary, ...) -> None
```

### Dependency Direction

```
market_data ← strategies ← signals ← risk ← paper_trading ← portfolio
     ↑                                                           ↑
     └────────── portfolio (for mark-to-market pricing) ─────────┘

observability ← ALL modules (event emission)
auth ← ALL modules (user context from dependencies)
common ← ALL modules (shared utilities, config, base classes)
```

No circular dependencies between domain modules.
Market data depends on nothing.
Portfolio depends on fills from paper trading.
Observability and auth are cross-cutting.

---

## 5. API Conventions

### URL Structure

```
/api/v1/{module}/{resource}
/api/v1/{module}/{resource}/{id}
/api/v1/{module}/{resource}/{id}/{sub-resource}
```

Examples:

```
GET  /api/v1/strategies
GET  /api/v1/strategies/abc-123
GET  /api/v1/strategies/abc-123/versions
GET  /api/v1/portfolio/positions
PUT  /api/v1/risk/config
```

### Response Envelope

All responses use a consistent envelope.

**Single entity:**

```json
{
  "data": {
    "id": "abc-123",
    "key": "rsi_ema_momentum",
    "name": "RSI + EMA Momentum",
    "status": "enabled"
  }
}
```

**List of entities:**

```json
{
  "data": [
    { "id": "abc-123", ... },
    { "id": "def-456", ... }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 47,
    "totalPages": 3
  }
}
```

**Error:**

```json
{
  "error": {
    "code": "STRATEGY_NOT_FOUND",
    "message": "Strategy abc-123 not found",
    "details": {}
  }
}
```

Every response is either `{ "data": ... }` or `{ "error": ... }`.
Never both. Never a bare array. Never a bare object without envelope.

### Pagination

All list endpoints support pagination:

```
GET /api/v1/signals?page=1&pageSize=20
```

Parameters:

```
page:     int (default 1, minimum 1)
pageSize: int (default 20, minimum 1, maximum 100)
```

Response always includes pagination metadata.

### Filtering

List endpoints support filtering via query parameters:

```
GET /api/v1/signals?strategyId=abc-123&status=pending&symbol=AAPL
GET /api/v1/portfolio/positions?status=open&market=equities
GET /api/v1/observability/events?category=risk&severity=error
```

Date range filtering:

```
GET /api/v1/signals?dateStart=2025-03-01T00:00:00Z&dateEnd=2025-03-10T23:59:59Z
```

All date parameters are ISO-8601 UTC.

### Sorting

```
GET /api/v1/signals?sortBy=createdAt&sortOrder=desc
```

Default sort: `createdAt desc` (newest first) for most endpoints.

### JSON Field Naming

```
Request and response JSON: camelCase
  strategyId, avgEntryPrice, createdAt, unrealizedPnl

Python internals: snake_case
  strategy_id, avg_entry_price, created_at, unrealized_pnl

Pydantic handles translation via alias configuration.
```

### Data Type Serialization

```
UUIDs:       strings            "abc-123-def-456"
Decimals:    strings            "187.50" (preserves precision, never float)
Timestamps:  ISO-8601 UTC       "2025-03-10T14:30:00Z"
Booleans:    true/false
Nulls:       null (included in response, not omitted)
Enums:       lowercase strings  "buy", "long", "enabled"
```

### Health Check

```
GET /api/v1/health

Response (always 200 if server is running):
{
  "status": "healthy",
  "version": "1.0.0",
  "uptimeSeconds": 86400
}
```

No auth required. Used by load balancers and monitoring.

---

## 6. Testing Strategy

### Testing Layers

**Unit tests:** Service logic and business rules in isolation.
Mock database and external services. Fast, run on every commit.

```
tests/unit/
    test_strategy_validation.py
    test_condition_engine.py
    test_indicator_library.py
    test_risk_checks.py
    test_fill_simulation.py
    test_pnl_calculation.py
    test_formula_parser.py
    test_signal_dedup.py
    test_forex_pool_allocation.py
```

**Integration tests:** Service + database together.
Real test PostgreSQL database. Test repositories, migrations, cross-table queries.

```
tests/integration/
    test_strategy_crud.py
    test_signal_lifecycle.py
    test_position_management.py
    test_risk_evaluation_flow.py
    test_dividend_processing.py
    test_bar_storage_and_aggregation.py
```

**End-to-end tests:** Full API flows.
Start application, make HTTP requests, verify responses.
Test auth, pagination, error handling, multi-step workflows.

```
tests/e2e/
    test_auth_flow.py
    test_strategy_create_and_evaluate.py
    test_signal_to_fill_pipeline.py
    test_manual_close_flow.py
    test_risk_rejection_flow.py
```

### Critical Paths Requiring Integration Tests

```
- Strategy evaluation producing correct signals
- All condition engine operator types (>, <, crosses_above, between, etc.)
- Formula parser: valid expressions, invalid expressions, edge cases
- Risk check ordering and rejection behavior
- Kill switch blocking entries, allowing exits
- Fill → position → PnL calculation chain (all four fill types)
- Scale-in weighted average entry price calculation
- Scale-out and full exit realized PnL calculation
- Dividend processing (ex-date eligibility, payable date cash credit)
- Stock split position adjustment
- Forex account pool allocation and release
- Shadow tracking: creation, position management, isolation from real
- Signal deduplication (dedup window, exemptions for exits/manual)
- Signal expiration
- Position override (stop loss override on specific position)
- Safety monitor activating on strategy auto-pause
- Options expiration (ITM vs OTM)
- Mark-to-market calculation
- Portfolio snapshot creation
- User data isolation (user A cannot see user B's data)
```

### Test Database

```
DATABASE_URL_TEST=postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test
```

Test database is created fresh before each test run.
Migrations applied, tests run, database dropped.
Tests never share state.

### Test Fixtures

Common test data as pytest fixtures:

```python
@pytest.fixture
async def admin_user(db):
    return await create_user(db, email="admin@test.com", role="admin")

@pytest.fixture
async def regular_user(db):
    return await create_user(db, email="user@test.com", role="user")

@pytest.fixture
async def sample_strategy(db, admin_user):
    return await create_strategy(db, user_id=admin_user.id, key="test_sma")

@pytest.fixture
async def sample_bars(db):
    return await create_bars(db, symbol="AAPL", timeframe="1h", count=200)

@pytest.fixture
async def sample_position(db, admin_user, sample_strategy):
    return await create_position(
        db, user_id=admin_user.id,
        strategy_id=sample_strategy.id,
        symbol="AAPL", side="long", qty=100
    )
```

### Coverage Expectations

```
Indicator library:     high   (math must be correct)
Condition engine:      high   (every operator, crossovers, nesting)
Formula parser:        high   (parsing is error-prone)
Risk checks:           high   (each check independently + ordering)
PnL calculations:      high   (money math must be exact)
Fill simulation:       high   (slippage, fees, all scenarios)
Signal dedup/expiry:   high   (edge cases matter)
Forex pool allocation: high   (contention scenarios)
API routes:            medium (auth, validation, happy path)
Background jobs:       medium (scheduling, error handling)
```

### Test Commands

```bash
# Unit tests (fast, no database)
pytest tests/unit/ -v

# Integration tests (needs test database)
pytest tests/integration/ -v

# E2E tests (needs running application)
pytest tests/e2e/ -v

# All tests
pytest -v

# With coverage
pytest --cov=backend/app --cov-report=html
```

### Frontend Testing

```
vitest:     component and logic unit tests
Playwright: browser-based end-to-end tests (once UI exists)
```

Frontend testing details will be in the frontend spec.

---

## 7. Project Structure Reference

### Complete Backend Structure

```
backend/
    app/
        __init__.py
        main.py                     ← FastAPI app entrypoint
        common/
            __init__.py
            config.py               ← global Settings, per-module configs
            database.py             ← engine, session factory, get_db dependency
            base_model.py           ← SQLAlchemy base with common fields
            errors.py               ← DomainError base class
            schemas.py              ← shared Pydantic schemas (pagination, envelope)
        auth/
            (see auth module spec)
        market_data/
            (see market data module spec)
        strategies/
            (see strategy module spec)
        signals/
            (see signals module spec)
        risk/
            (see risk engine module spec)
        paper_trading/
            (see paper trading module spec)
        portfolio/
            (see portfolio module spec)
        observability/
            (see observability module spec)
    migrations/
        versions/
        env.py
        alembic.ini
```

### Common Module Contents

```
backend/app/common/
    __init__.py
    config.py           ← Settings class, environment loading
    database.py         ← async engine, session factory, get_db
    base_model.py       ← SQLAlchemy declarative base with id, created_at, updated_at
    errors.py           ← DomainError, error code constants
    schemas.py          ← PaginationParams, PaginatedResponse, ErrorResponse
    utils.py            ← utcnow(), safe decimal operations
    types.py            ← shared type aliases if needed
```

---

## 8. Startup Sequence

### Application Boot Order

```
1. Load Settings from environment
   → validate required settings
   → fail fast with clear error if missing

2. Initialize database connection pool
   → verify database is reachable
   → run any pending migrations (optional, can be manual)

3. Initialize auth module
   → verify JWT secret is set

4. Initialize market data module
   → load broker configs
   → run universe filter
   → check backfill status
   → run backfill if needed
   → start WebSocket connections
   → start health monitoring

5. Initialize strategy module
   → load indicator catalog
   → initialize condition engine
   → start strategy runner loop
   → start safety monitor

6. Initialize signal module
   → start expiry checker background task

7. Initialize risk module
   → load risk config from database
   → check kill switch state

8. Initialize paper trading module
   → initialize executor(s)
   → load forex account pool state
   → start approved signal watcher

9. Initialize portfolio module
   → start mark-to-market cycle
   → start snapshot cycle
   → start dividend/split checker

10. Initialize observability module
    → start event batch writer
    → start metric collector
    → start alert evaluation loop

11. Start FastAPI HTTP server
    → register all routers
    → register exception handlers
    → register middleware (logging, CORS)

12. Emit system.ready event
    → "✅ All modules ready — system operational"
```

Each step logs its progress. If any critical step fails, the application
logs the error and exits (does not start in a half-initialized state).

---

## Configuration Variables Summary (All Modules)

```env
# === Database ===
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# === Auth ===
AUTH_JWT_SECRET_KEY=<required>
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7
AUTH_BCRYPT_COST_FACTOR=12
AUTH_MIN_PASSWORD_LENGTH=12
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_DURATION_MINUTES=15

# === Broker Credentials ===
ALPACA_API_KEY=<required>
ALPACA_API_SECRET=<required>
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/sip
OANDA_ACCESS_TOKEN=<required-for-forex>
OANDA_ACCOUNT_ID=<required-for-forex>
OANDA_BASE_URL=https://api-fxpractice.oanda.com
OANDA_STREAM_URL=https://stream-fxpractice.oanda.com

# === Universe Filter ===
UNIVERSE_FILTER_EQUITIES_MIN_VOLUME=500000
UNIVERSE_FILTER_EQUITIES_MIN_PRICE=5.00
UNIVERSE_FILTER_EQUITIES_EXCHANGES=NYSE,NASDAQ,AMEX
UNIVERSE_FILTER_EQUITIES_SCHEDULE=0 9 * * 1-5

# === WebSocket ===
WS_RECONNECT_INITIAL_DELAY_SEC=1
WS_RECONNECT_MAX_DELAY_SEC=60
WS_RECONNECT_BACKOFF_MULTIPLIER=2
WS_HEARTBEAT_INTERVAL_SEC=60
WS_STALE_DATA_THRESHOLD_SEC=120
WS_BAR_QUEUE_MAX_SIZE=10000

# === Bar Storage ===
BAR_BATCH_WRITE_SIZE=100
BAR_BATCH_WRITE_INTERVAL_SEC=3

# === Backfill ===
BACKFILL_1M_DAYS=30
BACKFILL_1H_DAYS=365
BACKFILL_4H_DAYS=365
BACKFILL_1D_DAYS=730
BACKFILL_RATE_LIMIT_BUFFER_PERCENT=10
BACKFILL_MAX_RETRIES=3
BACKFILL_RETRY_DELAY_SEC=30

# === Options ===
OPTION_CACHE_TTL_SEC=60

# === Market Data Health ===
MARKET_DATA_STALE_THRESHOLD_SEC=120
MARKET_DATA_STALE_CHECK_INTERVAL_SEC=60
MARKET_DATA_QUEUE_WARN_PERCENT=20
MARKET_DATA_QUEUE_CRITICAL_PERCENT=80
MARKET_DATA_HEALTH_CHECK_INTERVAL_SEC=30

# === Corporate Actions ===
CORPORATE_ACTIONS_FETCH_SCHEDULE=0 8 * * 1-5
CORPORATE_ACTIONS_LOOKFORWARD_DAYS=30

# === Strategy Runner ===
STRATEGY_RUNNER_CHECK_INTERVAL_SEC=60
STRATEGY_AUTO_PAUSE_ERROR_THRESHOLD=5
STRATEGY_EVALUATION_TIMEOUT_SEC=30
STRATEGY_MAX_CONCURRENT_EVALUATIONS=20

# === Safety Monitor ===
SAFETY_MONITOR_CHECK_INTERVAL_SEC=60
SAFETY_MONITOR_FAILURE_ALERT_THRESHOLD=3
SAFETY_MONITOR_GLOBAL_KILL_SWITCH=false

# === Signals ===
SIGNAL_DEDUP_WINDOW_BARS=1
SIGNAL_EXPIRY_SECONDS=300
SIGNAL_EXPIRY_CHECK_INTERVAL_SEC=60

# === Risk (defaults, overridden by DB config) ===
RISK_DEFAULT_MAX_POSITION_SIZE_PERCENT=10.0
RISK_DEFAULT_MAX_SYMBOL_EXPOSURE_PERCENT=20.0
RISK_DEFAULT_MAX_STRATEGY_EXPOSURE_PERCENT=30.0
RISK_DEFAULT_MAX_TOTAL_EXPOSURE_PERCENT=80.0
RISK_DEFAULT_MAX_DRAWDOWN_PERCENT=10.0
RISK_DEFAULT_MAX_DRAWDOWN_CATASTROPHIC_PERCENT=20.0
RISK_DEFAULT_MAX_DAILY_LOSS_PERCENT=3.0
RISK_DEFAULT_MIN_POSITION_VALUE=100.0
RISK_EVALUATION_TIMEOUT_SEC=5

# === Paper Trading ===
PAPER_TRADING_EXECUTION_MODE_EQUITIES=paper
PAPER_TRADING_EXECUTION_MODE_FOREX=simulation
PAPER_TRADING_BROKER_FALLBACK=simulation
PAPER_TRADING_SLIPPAGE_BPS_EQUITIES=5
PAPER_TRADING_SLIPPAGE_BPS_FOREX=2
PAPER_TRADING_SLIPPAGE_BPS_OPTIONS=10
PAPER_TRADING_FEE_PER_TRADE_EQUITIES=0.00
PAPER_TRADING_FEE_SPREAD_BPS_FOREX=15
PAPER_TRADING_FEE_PER_TRADE_OPTIONS=0.00
PAPER_TRADING_DEFAULT_CONTRACT_MULTIPLIER=100
PAPER_TRADING_INITIAL_CASH=100000.00
PAPER_TRADING_FOREX_ACCOUNT_POOL_SIZE=4
PAPER_TRADING_FOREX_CAPITAL_PER_ACCOUNT=25000.00
FOREX_ACCOUNT_ALLOCATION_PRIORITY=first_come

# === Shadow Tracking ===
SHADOW_TRACKING_ENABLED=true
SHADOW_TRACKING_FOREX_ONLY=true

# === Portfolio ===
PORTFOLIO_MARK_TO_MARKET_INTERVAL_SEC=60
PORTFOLIO_SNAPSHOT_INTERVAL_SEC=300
PORTFOLIO_RISK_FREE_RATE=0.05

# === Observability ===
EVENT_QUEUE_MAX_SIZE=50000
EVENT_BATCH_WRITE_SIZE=100
EVENT_BATCH_WRITE_INTERVAL_SEC=5
EVENT_RETENTION_DAYS=365
METRICS_COLLECTION_INTERVAL_SEC=60
METRICS_RETENTION_DAYS=90
ALERT_EVALUATION_INTERVAL_SEC=30
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_RECIPIENTS=
ALERT_EMAIL_MIN_SEVERITY=error
ALERT_WEBHOOK_ENABLED=false
ALERT_WEBHOOK_URL=
ALERT_WEBHOOK_MIN_SEVERITY=error

# === Logging ===
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Acceptance Criteria

This spec is accepted when:

- Database session management pattern is defined
- Repository pattern with naming conventions is specified
- SQLAlchemy model conventions (naming, types, base class) are documented
- Alembic migration workflow and rules are specified
- Domain error hierarchy with code catalog is defined
- API error response format is standardized
- HTTP status code mapping is explicit
- Global exception handler behavior is specified
- No-silent-failures rule for trading logic is stated
- Configuration loading (Pydantic Settings) is specified
- Required vs optional settings are distinguished
- Runtime-configurable vs startup-only settings are documented
- Inter-module communication rules (service calls only) are specified
- All service interface contracts are listed
- Module dependency direction is documented (no circular dependencies)
- API URL structure is defined
- Response envelope format is standardized (data/error/pagination)
- Pagination, filtering, and sorting conventions are specified
- JSON serialization rules (camelCase, decimal-as-string, etc.) are specified
- Testing layers (unit, integration, e2e) are defined
- Critical paths requiring tests are enumerated
- Test database and fixture patterns are specified
- Project structure is documented
- Application startup sequence is defined
- Complete configuration variable catalog is included
- A builder agent can follow these conventions without inventing patterns
