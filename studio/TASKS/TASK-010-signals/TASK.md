# TASK-010 — Signals Module Implementation

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the complete signals module: the persistence layer, validation,
deduplication, expiration, lifecycle management, analytics, and the integration
point that connects the strategy runner to the risk engine.

After this task:
- The signals database table exists with all fields and indexes
- Signals are created programmatically (by strategy runner, manual close, safety monitor, system)
- Signal validation checks required fields and logical consistency
- Signal deduplication prevents duplicate entry/scale-in signals within a configurable window
- Signal expiration runs as a background job, marking stale pending signals as expired
- Signal lifecycle transitions are enforced (pending → approved/rejected/modified/expired/canceled)
- The strategy runner from TASK-009 is wired to create real signals (replacing the stub)
- Signal analytics queries are available via API
- The signal-to-risk handoff contract is implemented (risk module consumes pending signals)

This task also wires the signal creation into the strategy runner,
replacing the TASK-010 TODO stubs from TASK-009.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/signals_module_spec.md — PRIMARY SPEC, read completely
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, inter-module interfaces
6. Review TASK-009 BUILDER_OUTPUT.md — understand runner signal_intent stubs

## Constraints

- Do NOT implement the risk engine (TASK-011) — signals are created as "pending"
  and stay pending until risk processes them
- Do NOT implement paper trading or order creation
- Do NOT create models for risk, paper_trading, or portfolio modules
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions (envelope, pagination, camelCase)
- All financial values use Decimal
- All timestamps are timezone-aware UTC
- Signal creation is programmatic (not via API) — the API is read-only plus cancel

---

## Deliverables

### 1. Signal Model (backend/app/signals/models.py)

Inherits from BaseModel.

```
Signal:
  - id: UUID (from BaseModel)
  - strategy_id: UUID (FK → strategies.id)
  - strategy_version: str
  - symbol: str
  - market: str (equities | forex)
  - timeframe: str
  - side: str (buy | sell)
  - signal_type: str (entry | exit | scale_in | scale_out)
  - source: str (strategy | manual | safety | system)
  - confidence: Numeric, nullable (0.0 to 1.0)
  - status: str (default "pending", values: pending | risk_approved |
                  risk_rejected | risk_modified | expired | canceled)
  - payload_json: JSON, nullable (strategy reasoning, indicator values)
  - position_id: UUID, nullable (for exit signals — no FK yet, portfolio doesn't exist)
  - exit_reason: str, nullable (stop_loss | take_profit | trailing_stop |
                                 max_hold | condition | manual | safety | system)
  - ts: datetime (evaluation timestamp, UTC)
  - expires_at: datetime, nullable (UTC)
  - created_at, updated_at (from BaseModel)

Indexes:
  INDEX (strategy_id, created_at)
  INDEX (symbol, created_at)
  INDEX (status)
  INDEX (strategy_id, symbol, status)
```

### 2. Signal Schemas (backend/app/signals/schemas.py)

Use camelCase aliases (alias_generator=to_camel, populate_by_name=True).

**Response schemas:**
```python
class SignalResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    strategy_version: str
    symbol: str
    market: str
    timeframe: str
    side: str
    signal_type: str
    source: str
    confidence: Decimal | None
    status: str
    payload_json: dict | None
    position_id: UUID | None
    exit_reason: str | None
    ts: datetime
    expires_at: datetime | None
    created_at: datetime

class SignalStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_strategy: dict[str, int]   # strategy_id → count
    by_symbol: dict[str, int]
    by_signal_type: dict[str, int]
    by_source: dict[str, int]
```

**Query schemas:**
```python
class SignalQueryParams(BaseModel):
    strategy_id: UUID | None = None
    symbol: str | None = None
    status: str | None = None
    signal_type: str | None = None
    source: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    page: int = 1
    page_size: int = 20
```

### 3. Signal Config (backend/app/signals/config.py)

```python
class SignalConfig:
    def __init__(self):
        s = get_settings()
        self.dedup_window_bars = s.signal_dedup_window_bars
        self.default_expiry_seconds = s.signal_expiry_seconds
        self.expiry_check_interval = s.signal_expiry_check_interval_sec
    
    def get_expiry_duration(self, timeframe: str) -> int:
        """Get expiry duration in seconds based on strategy timeframe.
        
        1m → 120s, 5m → 600s, 15m → 1800s, 1h → 3600s, 4h → 14400s
        Falls back to SIGNAL_EXPIRY_SECONDS if timeframe unknown.
        """
```

### 4. Signal Errors (backend/app/signals/errors.py)

```python
class SignalNotFoundError(DomainError):
    # code: SIGNAL_NOT_FOUND, status: 404

class SignalValidationError(DomainError):
    # code: SIGNAL_VALIDATION_FAILED, status: 400

class SignalTransitionError(DomainError):
    # code: SIGNAL_INVALID_TRANSITION, status: 400

class SignalDuplicateError(DomainError):
    # code: SIGNAL_DUPLICATE, status: 409

class SignalExpiredError(DomainError):
    # code: SIGNAL_EXPIRED, status: 410
```

Register in common/errors.py.

### 5. Signal Repository (backend/app/signals/repository.py)

```python
class SignalRepository:
    async def create(self, db, signal: Signal) -> Signal
    
    async def get_by_id(self, db, signal_id: UUID) -> Signal | None
    
    async def get_filtered(self, db, strategy_id: UUID | None = None,
                           symbol: str | None = None, status: str | None = None,
                           signal_type: str | None = None, source: str | None = None,
                           date_start: datetime | None = None,
                           date_end: datetime | None = None,
                           page: int = 1, page_size: int = 20
                           ) -> tuple[list[Signal], int]
    
    async def get_recent(self, db, limit: int = 20) -> list[Signal]
    
    async def get_pending(self, db) -> list[Signal]:
        """Get all pending signals for risk engine consumption."""
    
    async def update_status(self, db, signal_id: UUID, new_status: str) -> Signal:
        """Update signal status. Validates transition is legal."""
    
    async def find_duplicate(self, db, strategy_id: UUID, symbol: str,
                             side: str, signal_type: str,
                             window_start: datetime) -> Signal | None:
        """Find an existing pending/approved signal matching dedup criteria."""
    
    async def expire_stale(self, db) -> int:
        """Mark all pending signals past expires_at as expired. Returns count."""
    
    async def cancel_by_strategy(self, db, strategy_id: UUID) -> int:
        """Cancel all pending signals for a strategy. Returns count."""
    
    async def get_stats(self, db, strategy_id: UUID | None = None,
                        date_start: datetime | None = None,
                        date_end: datetime | None = None) -> dict:
        """Get signal analytics: counts by status, strategy, symbol, type, source."""
```

### 6. Signal Deduplication (backend/app/signals/dedup.py)

```python
class SignalDeduplicator:
    """Checks whether a signal is a duplicate of an existing pending/approved signal.
    
    Dedup rules:
    - Only applies to source="strategy" with signal_type in ("entry", "scale_in")
    - Exit signals are NEVER deduplicated
    - Manual, safety, and system signals are NEVER deduplicated
    - A signal is duplicate if an existing pending/approved signal matches:
      same strategy_id, symbol, side, signal_type, within dedup window
    """
    
    def __init__(self, config: SignalConfig):
        self._config = config
    
    async def is_duplicate(self, db: AsyncSession, strategy_id: UUID,
                           symbol: str, side: str, signal_type: str,
                           source: str, timeframe: str,
                           ts: datetime) -> tuple[bool, UUID | None]:
        """Check if a signal is a duplicate.
        
        Returns (is_duplicate: bool, existing_signal_id: UUID | None)
        
        1. If source != "strategy" → not duplicate
        2. If signal_type in ("exit", "scale_out") → not duplicate
        3. Calculate dedup window: ts - (dedup_window_bars * timeframe_minutes)
        4. Query for existing signal matching criteria within window
        5. Return result
        """
    
    def _get_window_start(self, ts: datetime, timeframe: str,
                          window_bars: int) -> datetime:
        """Calculate the dedup window start timestamp."""
```

### 7. Signal Validation (within service.py or separate validation.py)

Implement validation as part of the service's create_signal method:

```python
async def _validate_signal(self, db: AsyncSession, signal_data: dict) -> list[str]:
    """Validate a signal before creation.
    
    Required field checks:
    - strategy_id exists and references a valid strategy
    - symbol is on the active watchlist (via MarketDataService)
    - side is "buy" or "sell"
    - signal_type is entry | exit | scale_in | scale_out
    - source is strategy | manual | safety | system
    - ts is not in the future
    - ts is not more than 5 minutes in the past
    
    Logical checks:
    - Entry signal: stub check for existing position (TODO TASK-013)
    - Exit signal: position_id provided (if available)
    
    Returns list of validation errors. Empty = valid.
    """
```

### 8. Signal Expiry Background Job (backend/app/signals/expiry.py)

```python
class SignalExpiryChecker:
    """Background job that marks stale pending signals as expired.
    
    Runs every SIGNAL_EXPIRY_CHECK_INTERVAL_SEC.
    """
    
    def __init__(self, config: SignalConfig):
        self._config = config
        self._running = False
    
    async def start(self) -> None:
        """Start the expiry checker loop as a background task."""
    
    async def stop(self) -> None:
        """Stop the expiry checker."""
    
    async def _run_loop(self) -> None:
        """Periodically check for and expire stale signals."""
    
    async def run_check(self, db: AsyncSession) -> int:
        """Run one expiry check cycle. Returns count of expired signals."""
```

### 9. Signal Service (backend/app/signals/service.py)

The main entry point for signal creation and management.

```python
class SignalService:
    """Signal creation, validation, deduplication, lifecycle, and analytics.
    
    This is the inter-module interface. Other modules call:
    - create_signal() — strategy runner, manual close, safety monitor, system
    - get_pending_signals() — risk engine
    - update_signal_status() — risk engine (after evaluation)
    """
    
    def __init__(self, config: SignalConfig, deduplicator: SignalDeduplicator):
        self._config = config
        self._dedup = deduplicator
        self._repo = SignalRepository()
    
    async def create_signal(self, db: AsyncSession, signal_data: dict) -> Signal | None:
        """Create a signal with validation and deduplication.
        
        Steps:
        1. Validate the signal data
        2. If validation fails → log warning, return None (no error thrown)
        3. Check deduplication
        4. If duplicate → log info, return None
        5. Calculate expires_at from timeframe
        6. Create Signal model instance
        7. Persist via repository
        8. Return the created signal
        
        This method never raises exceptions. Validation and dedup failures
        are logged but don't propagate — the caller (strategy runner) should
        not be disrupted by signal-layer issues.
        """
    
    async def get_signal(self, db, signal_id: UUID, user_id: UUID) -> Signal:
        """Get signal by ID. Verify ownership through strategy's user_id."""
    
    async def list_signals(self, db, user_id: UUID, **filters) -> tuple[list[Signal], int]:
        """List signals with filters, enforcing user ownership."""
    
    async def get_recent(self, db, user_id: UUID, limit: int = 20) -> list[Signal]:
        """Get recent signals across all of user's strategies."""
    
    async def cancel_signal(self, db, signal_id: UUID, user_id: UUID) -> Signal:
        """Cancel a pending signal.
        
        Only valid for status="pending". Returns updated signal.
        """
    
    async def get_pending_signals(self, db) -> list[Signal]:
        """Get all pending signals for risk engine consumption.
        
        This is the risk handoff read interface. Returns signals
        ordered by created_at (oldest first — FIFO processing).
        """
    
    async def update_signal_status(self, db, signal_id: UUID,
                                   new_status: str) -> Signal:
        """Update signal status (called by risk engine).
        
        Validates transition:
          pending → risk_approved | risk_rejected | risk_modified | expired | canceled
        
        No other transitions are valid.
        """
    
    async def cancel_strategy_signals(self, db, strategy_id: UUID) -> int:
        """Cancel all pending signals for a strategy.
        
        Called when a strategy is paused or disabled.
        Returns count of canceled signals.
        """
    
    async def get_stats(self, db, user_id: UUID, strategy_id: UUID | None = None,
                        date_start: datetime | None = None,
                        date_end: datetime | None = None) -> dict:
        """Get signal analytics summary."""
```

### 10. Signal Router (backend/app/signals/router.py)

Replace the empty stub with the read-only + cancel API.

```
GET  /api/v1/signals                  → list signals with filters (paginated)
GET  /api/v1/signals/recent           → last N signals (default 20)
GET  /api/v1/signals/stats            → signal analytics summary
GET  /api/v1/signals/:id              → signal detail
POST /api/v1/signals/:id/cancel       → cancel a pending signal
```

All endpoints require authentication (get_current_user).
All enforce user ownership through strategy_id → strategy.user_id chain.
All use standard envelope format.
Stats endpoint accepts optional strategy_id, date_start, date_end query params.

### 11. Wire Signal Creation into Strategy Runner

Update backend/app/strategies/runner.py to replace the TASK-010 TODO stubs
with actual signal creation calls.

**In evaluate_strategy():**
Where the runner currently produces signal_intent dicts, instead call:

```python
signal = await signal_service.create_signal(db, {
    "strategy_id": strategy.id,
    "strategy_version": strategy.current_version,
    "symbol": symbol,
    "market": config.get("market", "equities"),
    "timeframe": config.get("timeframe"),
    "side": intent["side"],
    "signal_type": intent["type"],  # entry, exit, scale_in, scale_out
    "source": "strategy",
    "confidence": Decimal("1.0"),
    "payload_json": intent.get("payload"),
    "position_id": intent.get("position_id"),
    "exit_reason": intent.get("exit_reason"),
    "ts": utcnow(),
})
```

Also wire signal creation into:
- Safety monitor (source="safety")
- Update the evaluation record's signals_emitted count

**In change_status() (strategy service):**
When a strategy is paused or disabled, cancel its pending signals:

```python
await signal_service.cancel_strategy_signals(db, strategy.id)
```

### 12. Signal Module Startup (backend/app/signals/startup.py)

```python
_expiry_checker: SignalExpiryChecker | None = None
_signal_service: SignalService | None = None

async def start_signals() -> None:
    """Initialize and start the signal module.
    Create the SignalService singleton and start the expiry checker.
    """

async def stop_signals() -> None:
    """Stop the expiry checker."""

def get_signal_service() -> SignalService:
    """Get the signal service singleton for inter-module use."""
```

### 13. Register in main.py

Add signal startup/shutdown to lifespan, after strategies:

```python
await start_market_data(db)
await start_strategies()
await start_signals()
# ...
await stop_signals()
await stop_strategies()
await stop_market_data()
```

### 14. Alembic Migration

Create migration for the signals table:

```bash
cd backend
alembic revision --autogenerate -m "create_signals_table"
alembic upgrade head
```

Update migrations/env.py to import signal models.

---

## Acceptance Criteria

### Model and Migration
1. Signal model exists with all fields, correct types, and all four indexes
2. confidence field uses Numeric (not Float)
3. payload_json uses JSON/JSONB column type
4. Alembic migration creates the signals table and applies cleanly
5. migrations/env.py imports signal models

### Validation
6. Required field validation checks all fields listed in the spec
7. Timestamp validation: ts not in future, not more than 5 minutes old
8. Symbol validation checks watchlist via MarketDataService
9. Validation failures are logged but do NOT throw exceptions to callers
10. Validation failure does NOT prevent the strategy evaluation from being counted as successful

### Deduplication
11. Dedup only applies to source="strategy" with signal_type in (entry, scale_in)
12. Exit signals are never deduplicated
13. Manual, safety, and system signals are never deduplicated
14. Dedup checks same strategy_id + symbol + side + signal_type within window
15. Dedup window is configurable (SIGNAL_DEDUP_WINDOW_BARS)
16. Duplicate detection is logged

### Lifecycle
17. Signals are created with status="pending"
18. Valid transitions: pending → risk_approved/risk_rejected/risk_modified/expired/canceled
19. Invalid transitions raise SignalTransitionError
20. No reverse transitions (rejected cannot become approved)

### Expiration
21. expires_at is calculated from strategy timeframe at creation time
22. Expiry durations match spec (1m→120s, 5m→600s, 15m→1800s, 1h→3600s, 4h→14400s)
23. Background job runs periodically and marks expired signals
24. Expiry checker is started/stopped via startup module

### Service Interface
25. create_signal() validates, deduplicates, and persists in one call
26. create_signal() returns None (not exception) on validation/dedup failure
27. get_pending_signals() returns signals ordered by created_at (FIFO)
28. update_signal_status() validates transition legality
29. cancel_strategy_signals() cancels all pending signals for a strategy

### Strategy Integration
30. Strategy runner creates real signals via SignalService (TASK-010 stubs replaced)
31. Safety monitor creates signals via SignalService with source="safety"
32. Strategy pause/disable cancels pending signals
33. Evaluation record signals_emitted count is accurate

### API
34. GET /signals returns filtered, paginated signal list
35. GET /signals/recent returns last N signals
36. GET /signals/stats returns analytics summary (counts by status/strategy/symbol/type/source)
37. GET /signals/:id returns signal detail
38. POST /signals/:id/cancel cancels a pending signal (only valid for pending)
39. All endpoints enforce user ownership through strategy chain
40. All responses use standard envelope format with camelCase

### General
41. Signal error classes exist and registered in common/errors.py
42. SignalConfig extracts settings from global Settings
43. No risk, paper_trading, or portfolio logic created
44. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-010-signals/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
