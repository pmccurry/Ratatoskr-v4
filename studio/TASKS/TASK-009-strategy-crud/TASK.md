# TASK-009 — Strategy: CRUD, Validation, Lifecycle, Runner, and Safety Monitor

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement everything in the strategy module that TASK-008 didn't cover:
database models, CRUD operations, comprehensive config validation, lifecycle
management, versioning, the strategy runner, and the safety monitor.

After this task:
- Strategy database tables exist (Strategy, StrategyConfig, StrategyState,
  StrategyEvaluation, PositionOverride)
- Users can create, read, update, and delete strategies via API
- Strategy configs are comprehensively validated at save time
- Strategies have a lifecycle (draft → enabled → paused → disabled)
- Config changes on enabled strategies create new versions
- The strategy runner evaluates enabled strategies on schedule using
  the indicator library and condition engine from TASK-008
- The safety monitor watches orphaned positions on a 1-minute cycle
- Auto-pause triggers after consecutive errors

This task builds the COMPLETE strategy module. However, two integration
points are stubbed because their modules don't exist yet:
- **Signal emission** — the runner produces evaluation results but
  cannot persist signals (signals module = TASK-010)
- **Position queries** — the runner and safety monitor cannot query
  live positions (portfolio module = TASK-013)

These stubs are clearly marked and will be wired in by their respective tasks.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/strategy_module_spec.md — PRIMARY SPEC, sections 5-14
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, inter-module interfaces
6. /studio/SPECS/market_data_module_spec.md — MarketDataService interface (get_bars, get_watchlist)
7. Review TASK-008 BUILDER_OUTPUT.md — understand existing indicator/condition/formula code

## Constraints

- Do NOT modify indicator library, condition engine, or formula parser from TASK-008
- Do NOT implement the signals module (no Signal model, no signal persistence)
- Do NOT implement portfolio models (no Position model)
- Do NOT create models or logic for risk, paper_trading, or observability
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions from cross_cutting_specs (envelope, pagination, camelCase)
- All financial values use Decimal
- All timestamps are timezone-aware UTC

---

## Deliverables

### 1. Strategy Models (backend/app/strategies/models.py)

All models inherit from BaseModel.

**Strategy:**
```
Strategy:
  - id: UUID (from BaseModel)
  - key: str (unique)
  - name: str
  - description: str (default "")
  - type: str (default "config")
  - status: str (default "draft", values: draft | enabled | paused | disabled)
  - current_version: str (default "1.0.0")
  - market: str (equities | forex | both)
  - auto_pause_error_count: int (default 0)
  - last_evaluated_at: datetime, nullable
  - user_id: UUID (FK → users.id, for row-level security)
  - created_at, updated_at (from BaseModel)

Indexes:
  UNIQUE (key)
  INDEX (status)
  INDEX (market, status)
  INDEX (user_id)
```

**StrategyConfig:**
```
StrategyConfig:
  - id: UUID (from BaseModel)
  - strategy_id: UUID (FK → strategies.id)
  - version: str
  - config_json: JSON (full strategy definition — use SQLAlchemy JSON type)
  - is_active: bool (default true)
  - created_at (from BaseModel)
  - updated_at (from BaseModel)

Indexes:
  INDEX (strategy_id, is_active)
  UNIQUE (strategy_id, version)
```

**StrategyState:**
```
StrategyState:
  - id: UUID (from BaseModel)
  - strategy_id: UUID (FK → strategies.id, unique — one row per strategy)
  - state_json: JSON (runtime state: trailing stop highs, cooldowns, etc.)
  - updated_at (from BaseModel)

Indexes:
  UNIQUE (strategy_id)
```

**StrategyEvaluation:**
```
StrategyEvaluation:
  - id: UUID (from BaseModel)
  - strategy_id: UUID (FK → strategies.id)
  - strategy_version: str
  - evaluated_at: datetime
  - symbols_evaluated: int (default 0)
  - signals_emitted: int (default 0)
  - exits_triggered: int (default 0)
  - errors: int (default 0)
  - duration_ms: int
  - status: str (success | partial_success | error | skipped)
  - skip_reason: str, nullable
  - details_json: JSON, nullable
  - created_at (from BaseModel)

Indexes:
  INDEX (strategy_id, evaluated_at)
  INDEX (status)
```

**PositionOverride:**
```
PositionOverride:
  - id: UUID (from BaseModel)
  - position_id: UUID (no FK yet — portfolio module doesn't exist)
  - strategy_id: UUID (FK → strategies.id)
  - override_type: str (stop_loss | take_profit | trailing_stop)
  - original_value_json: JSON
  - override_value_json: JSON
  - reason: str, nullable
  - created_by: str (user | system)
  - is_active: bool (default true)
  - created_at, updated_at (from BaseModel)

Indexes:
  INDEX (position_id, is_active)
  INDEX (strategy_id)
```

### 2. Strategy Schemas (backend/app/strategies/schemas.py)

Pydantic models for the API. Use camelCase aliases.

**Request schemas:**
```python
class CreateStrategyRequest(BaseModel):
    key: str
    name: str
    description: str = ""
    market: str  # equities | forex | both
    config: dict  # full strategy definition (validated separately)

class UpdateStrategyConfigRequest(BaseModel):
    config: dict  # full strategy definition

class UpdateStrategyMetaRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class StrategyStatusRequest(BaseModel):
    status: str  # enabled | paused | disabled

class PositionOverrideRequest(BaseModel):
    position_id: UUID
    override_type: str  # stop_loss | take_profit | trailing_stop
    value: dict  # override value (e.g., {"type": "percent", "value": 1.5})
    reason: str | None = None
```

**Response schemas:**
```python
class StrategyResponse(BaseModel):
    id: UUID
    key: str
    name: str
    description: str
    type: str
    status: str
    current_version: str
    market: str
    auto_pause_error_count: int
    last_evaluated_at: datetime | None
    created_at: datetime
    updated_at: datetime

class StrategyDetailResponse(StrategyResponse):
    config: dict  # current active config

class StrategyEvaluationResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    strategy_version: str
    evaluated_at: datetime
    symbols_evaluated: int
    signals_emitted: int
    exits_triggered: int
    errors: int
    duration_ms: int
    status: str
    skip_reason: str | None
    created_at: datetime

class StrategyValidationResponse(BaseModel):
    valid: bool
    errors: list[dict]   # {"field": str, "message": str, "severity": "error"}
    warnings: list[dict] # {"field": str, "message": str, "severity": "warning"}
```

### 3. Strategy Repository (backend/app/strategies/repository.py)

```python
class StrategyRepository:
    async def create(self, db, strategy: Strategy) -> Strategy
    async def get_by_id(self, db, strategy_id: UUID) -> Strategy | None
    async def get_by_key(self, db, key: str) -> Strategy | None
    async def get_by_user(self, db, user_id: UUID, status: str | None,
                          page: int, page_size: int) -> tuple[list[Strategy], int]
    async def get_enabled(self, db) -> list[Strategy]
    async def update(self, db, strategy: Strategy) -> Strategy
    async def delete(self, db, strategy_id: UUID) -> None

class StrategyConfigRepository:
    async def create(self, db, config: StrategyConfig) -> StrategyConfig
    async def get_active(self, db, strategy_id: UUID) -> StrategyConfig | None
    async def get_version(self, db, strategy_id: UUID, version: str) -> StrategyConfig | None
    async def get_history(self, db, strategy_id: UUID) -> list[StrategyConfig]
    async def deactivate_all(self, db, strategy_id: UUID) -> None

class StrategyStateRepository:
    async def get_or_create(self, db, strategy_id: UUID) -> StrategyState
    async def update(self, db, state: StrategyState) -> StrategyState

class StrategyEvaluationRepository:
    async def create(self, db, evaluation: StrategyEvaluation) -> StrategyEvaluation
    async def get_recent(self, db, strategy_id: UUID, limit: int = 20) -> list[StrategyEvaluation]
    async def get_error_count(self, db, strategy_id: UUID) -> int

class PositionOverrideRepository:
    async def create(self, db, override: PositionOverride) -> PositionOverride
    async def get_active_for_position(self, db, position_id: UUID) -> list[PositionOverride]
    async def deactivate(self, db, override_id: UUID) -> None
    async def get_by_strategy(self, db, strategy_id: UUID) -> list[PositionOverride]
```

### 4. Strategy Validator (backend/app/strategies/validation.py)

Comprehensive config validation at save time.

```python
class StrategyValidator:
    """Validates strategy configuration at save time.
    
    Uses the indicator registry from TASK-008 and the formula parser.
    """
    
    def __init__(self, registry: IndicatorRegistry, formula_parser: FormulaParser):
        self._registry = registry
        self._parser = formula_parser
    
    def validate(self, config: dict) -> StrategyValidationResponse:
        """Run all validation checks.
        
        Returns StrategyValidationResponse with errors and warnings.
        Errors block saving. Warnings are informational.
        """
    
    def _validate_completeness(self, config: dict, errors: list, warnings: list):
        """Check config completeness:
        - At least one entry condition exists
        - At least one exit mechanism (exit conditions, stop loss, OR take profit)
        - Position sizing defined
        - At least one symbol (or mode is watchlist/filtered)
        - Timeframe set
        - Lookback bars >= max indicator period in any condition
        """
    
    def _validate_indicators(self, config: dict, errors: list, warnings: list):
        """Check indicator validity:
        - Every indicator key exists in the catalog
        - Every parameter within catalog min/max range
        - Parameter types match
        - Multi-output indicators have output field specified
        """
    
    def _validate_formulas(self, config: dict, errors: list, warnings: list):
        """Check formula validity:
        - Expression parses without syntax errors
        - All functions in whitelist
        - Argument counts correct
        """
    
    def _validate_symbols(self, config: dict, errors: list, warnings: list):
        """Check symbol validity:
        - mode = explicit: all symbols listed (non-empty)
        - mode = watchlist: market specified
        - mode = filtered: filter criteria present
        """
    
    def _validate_risk_sanity(self, config: dict, errors: list, warnings: list):
        """Risk sanity checks:
        - Stop loss: 0.1% to 50% (prevent typos)
        - Position size: <= 100% of equity
        - Max positions: >= 1
        - High values generate warnings (not errors)
        """
    
    def _validate_conditions(self, conditions: dict, path: str,
                             errors: list, warnings: list):
        """Recursively validate condition groups:
        - logic is "and" or "or"
        - Each condition has valid operator
        - Operand types are valid
        - Nested groups are valid
        """
```

### 5. Strategy Service (backend/app/strategies/service.py)

Business logic. Note: this file may already have router.py context from TASK-008.
Create a new service file or extend the module as appropriate.

```python
class StrategyService:
    """Strategy CRUD, validation, lifecycle, and versioning."""
    
    # --- CRUD ---
    
    async def create_strategy(self, db, user_id: UUID,
                              data: CreateStrategyRequest) -> Strategy:
        """
        1. Validate key uniqueness
        2. Validate config
        3. Create Strategy record (status=draft)
        4. Create StrategyConfig record (version=1.0.0, is_active=True)
        5. Create StrategyState record (empty state)
        6. Return strategy
        """
    
    async def get_strategy(self, db, strategy_id: UUID,
                           user_id: UUID) -> StrategyDetailResponse:
        """Get strategy with active config. Enforce user ownership."""
    
    async def list_strategies(self, db, user_id: UUID, status: str | None,
                              page: int, page_size: int) -> tuple[list, int]:
        """List user's strategies with pagination."""
    
    async def update_config(self, db, strategy_id: UUID, user_id: UUID,
                            data: UpdateStrategyConfigRequest) -> Strategy:
        """
        1. Verify ownership
        2. Validate new config
        3. If strategy is enabled:
           a. Create new version (increment minor)
           b. Deactivate old config
           c. Create new StrategyConfig (is_active=True)
           d. Update strategy.current_version
        4. If strategy is draft:
           a. Update existing config in place (no new version)
        5. Return strategy
        """
    
    async def update_meta(self, db, strategy_id: UUID, user_id: UUID,
                          data: UpdateStrategyMetaRequest) -> Strategy:
        """Update name/description only. No versioning needed."""
    
    async def delete_strategy(self, db, strategy_id: UUID,
                              user_id: UUID) -> None:
        """Delete a draft strategy. Cannot delete enabled/paused."""
    
    # --- Lifecycle ---
    
    async def change_status(self, db, strategy_id: UUID, user_id: UUID,
                            new_status: str) -> Strategy:
        """
        Validate transition:
          draft → enabled
          enabled → paused, disabled
          paused → enabled, disabled
          disabled → enabled
        
        On enable: reset error count
        On pause/disable: positions transfer to safety monitor (stub)
        """
    
    # --- Versioning ---
    
    def _next_version(self, current: str) -> str:
        """Increment minor version: 1.0.0 → 1.1.0 → 1.2.0"""
    
    async def get_version_history(self, db, strategy_id: UUID,
                                  user_id: UUID) -> list[StrategyConfig]:
        """Get all config versions for a strategy."""
    
    # --- Validation ---
    
    def validate_config(self, config: dict) -> StrategyValidationResponse:
        """Validate a strategy config without saving."""
    
    # --- Position Overrides ---
    
    async def create_override(self, db, strategy_id: UUID, user_id: UUID,
                              data: PositionOverrideRequest) -> PositionOverride:
        """Create a position-level exit rule override."""
    
    async def remove_override(self, db, override_id: UUID,
                              user_id: UUID) -> None:
        """Deactivate a position override."""
```

### 6. Strategy Runner (backend/app/strategies/runner.py)

The main evaluation loop.

```python
class StrategyRunner:
    """Runs strategy evaluations on schedule.
    
    Called periodically (every minute). Checks which strategies need
    evaluation based on their timeframe, then evaluates each one.
    """
    
    def __init__(self, config: StrategyConfig, condition_engine: ConditionEngine):
        self._config = config
        self._engine = condition_engine
        self._running = False
    
    async def start(self) -> None:
        """Start the runner loop as a background task."""
    
    async def stop(self) -> None:
        """Stop the runner loop gracefully."""
    
    async def _run_loop(self) -> None:
        """Main loop: every RUNNER_CHECK_INTERVAL_SEC, check and evaluate."""
    
    async def run_evaluation_cycle(self, db: AsyncSession) -> dict:
        """Run one evaluation cycle.
        
        1. Get all enabled strategies
        2. Filter to those whose timeframe aligns with current time
        3. Evaluate each in parallel (asyncio.gather with return_exceptions)
        4. Handle results: log success, count errors, auto-pause if needed
        5. Return summary: {"evaluated": N, "signals": N, "errors": N}
        """
    
    def _is_due(self, strategy: Strategy, config: dict, now: datetime) -> bool:
        """Check if a strategy's timeframe aligns with current time.
        
        1m: always True
        5m: minute % 5 == 0
        15m: minute % 15 == 0
        1h: minute == 0
        4h: hour % 4 == 0 and minute == 0
        """
    
    def _is_market_open(self, market: str, trading_hours: dict,
                        now: datetime) -> bool:
        """Check if the market is open for this strategy's configuration."""
    
    async def evaluate_strategy(self, db: AsyncSession, strategy: Strategy,
                                active_config: StrategyConfig) -> dict:
        """Evaluate a single strategy.
        
        1. Pre-checks (enabled, market data healthy, market open)
        2. Resolve symbols (explicit, watchlist, filtered)
        3. Fetch bar data for each symbol
        4. Load strategy state
        5. For each symbol:
           a. If no position → evaluate entry conditions
           b. If position exists → evaluate exit conditions + SL/TP/trailing
              (STUB: position check returns empty — no portfolio module yet)
        6. Collect evaluation results (would-be signals)
        7. Persist StrategyEvaluation record
        8. Update strategy state (trailing stop highs, etc.)
        9. Return evaluation summary
        
        NOTE: Signal creation is stubbed. The runner produces a list of
        "evaluation results" with signal_intent dicts. When the signals
        module (TASK-010) is built, it will wire into this point.
        """
    
    async def _resolve_symbols(self, db: AsyncSession, config: dict) -> list[str]:
        """Resolve symbol list based on config mode.
        
        - explicit: return config.symbols.list
        - watchlist: query MarketDataService.get_watchlist(market)
        - filtered: query watchlist with additional filters
        """
    
    async def _evaluate_entry(self, config: dict, bars: list[dict]) -> dict | None:
        """Evaluate entry conditions for a symbol.
        
        Returns signal_intent dict or None:
        {"symbol": str, "side": str, "type": "entry", "reason": "conditions_met",
         "strategy_id": UUID, "strategy_version": str}
        """
    
    async def _evaluate_exit(self, config: dict, bars: list[dict],
                             position: dict | None, state: dict) -> dict | None:
        """Evaluate exit conditions for a symbol with a position.
        
        Checks in order:
        1. Position overrides (if any active)
        2. Condition-based exit (exit_conditions from config)
        3. Stop loss
        4. Take profit
        5. Trailing stop (update highest_price in state)
        6. Max hold bars
        
        Returns signal_intent dict or None.
        
        NOTE: position parameter is currently always None (stub).
        When portfolio module exists, real position data flows here.
        """
    
    async def _handle_auto_pause(self, db: AsyncSession,
                                 strategy: Strategy) -> None:
        """Auto-pause a strategy after too many errors.
        
        1. Set status to 'paused'
        2. Reset error count
        3. Log the auto-pause event
        4. (Future: trigger alert via observability)
        """
```

### 7. Safety Monitor (backend/app/strategies/custom/safety_monitor.py)

Wait — per the folder structure, use the main strategies directory,
not `custom/`. Place at: `backend/app/strategies/safety_monitor.py`

```python
class SafetyMonitor:
    """Monitors orphaned positions (strategy paused/disabled/errored).
    
    Evaluates ONLY price-based exit rules:
    - Stop loss vs current price
    - Take profit vs current price
    - Trailing stop vs current price
    
    Does NOT evaluate indicator-based exit conditions.
    Runs every 1 minute regardless of strategy timeframe.
    """
    
    def __init__(self, config: StrategyConfig):
        self._config = config
        self._running = False
    
    async def start(self) -> None:
        """Start the safety monitor loop."""
    
    async def stop(self) -> None:
        """Stop the safety monitor loop."""
    
    async def _run_loop(self) -> None:
        """Main loop: every SAFETY_MONITOR_CHECK_INTERVAL_SEC, check positions."""
    
    async def run_check(self, db: AsyncSession) -> dict:
        """Run one safety check cycle.
        
        1. Find all strategies in paused/disabled state
        2. For each, get open positions
           (STUB: returns empty list — no portfolio module yet)
        3. For each position:
           a. Get current price from MarketDataService.get_latest_close()
           b. Get strategy config (for exit rules)
           c. Check position overrides
           d. Evaluate: stop loss, take profit, trailing stop
           e. If triggered → create signal_intent (stub, same as runner)
        4. Return summary: {"strategies_checked": N, "positions_checked": N, "exits_triggered": N}
        """
    
    async def _check_stop_loss(self, position: dict, config: dict,
                               current_price: Decimal) -> bool:
        """Check if stop loss is hit.
        
        For long: current_price <= stop_price
        For short: current_price >= stop_price
        
        stop_price computed from:
        - percent: avg_entry * (1 - value/100) for long
        - atr_multiple: avg_entry - (atr * value) for long
        - fixed: avg_entry - value for long
        """
    
    async def _check_take_profit(self, position: dict, config: dict,
                                 current_price: Decimal) -> bool:
        """Check if take profit is hit. Same structure as stop loss, inverted."""
    
    async def _check_trailing_stop(self, position: dict, config: dict,
                                   state: dict, current_price: Decimal) -> bool:
        """Check trailing stop.
        
        1. Get highest_price_since_entry from state
        2. Update if current_price > highest
        3. trail_price = highest * (1 - value/100) for long
        4. Return True if current_price <= trail_price
        """
    
    async def _handle_failure(self, error: Exception) -> None:
        """Handle safety monitor failure.
        
        1. Log critical error
        2. Increment consecutive failure count
        3. If failures >= FAILURE_ALERT_THRESHOLD → trigger alert (stub)
        4. If GLOBAL_KILL_SWITCH enabled → create kill signal (stub)
        """
```

### 8. Strategy Startup (backend/app/strategies/startup.py)

Register the runner and safety monitor with the application lifecycle.

```python
_runner: StrategyRunner | None = None
_safety_monitor: SafetyMonitor | None = None

async def start_strategies() -> None:
    """Start the strategy runner and safety monitor."""
    # Create ConditionEngine with registry and formula parser
    # Create StrategyRunner
    # Create SafetyMonitor
    # Start both as background tasks

async def stop_strategies() -> None:
    """Stop the runner and safety monitor."""

def get_runner() -> StrategyRunner | None:
    return _runner

def get_safety_monitor() -> SafetyMonitor | None:
    return _safety_monitor
```

### 9. Register Strategy Startup in main.py

Add strategy startup/shutdown to the FastAPI lifespan, after market data:

```python
# In lifespan:
await start_market_data(db)
await start_strategies()
# ...
await stop_strategies()
await stop_market_data()
```

Same pattern as market data: wrap in try/except, log errors, don't crash.

### 10. Strategy Router — Full CRUD (backend/app/strategies/router.py)

Extend the existing router (which has indicator and formula endpoints from TASK-008)
with full CRUD and lifecycle endpoints.

```
Strategy CRUD (requires auth, enforces user ownership):
  POST   /api/v1/strategies                       → create strategy
  GET    /api/v1/strategies                       → list user's strategies (paginated)
  GET    /api/v1/strategies/:id                   → get strategy detail with config
  PUT    /api/v1/strategies/:id/config            → update strategy config
  PUT    /api/v1/strategies/:id/meta              → update name/description
  DELETE /api/v1/strategies/:id                   → delete draft strategy
  POST   /api/v1/strategies/:id/validate          → validate config without saving

Lifecycle:
  POST   /api/v1/strategies/:id/enable            → enable strategy
  POST   /api/v1/strategies/:id/pause             → pause strategy
  POST   /api/v1/strategies/:id/disable           → disable strategy

Versioning:
  GET    /api/v1/strategies/:id/versions          → config version history

Evaluation History:
  GET    /api/v1/strategies/:id/evaluations       → recent evaluation logs

Position Overrides:
  POST   /api/v1/strategies/:id/overrides         → create position override
  DELETE /api/v1/strategies/overrides/:override_id → remove override

Existing (from TASK-008):
  GET    /api/v1/strategies/indicators             → indicator catalog
  POST   /api/v1/strategies/formulas/validate      → formula validation
```

All responses use standard envelope format.
All endpoints enforce user ownership (except indicator catalog which is global).

### 11. Alembic Migration

Create migration for all five strategy tables.

```bash
cd backend
alembic revision --autogenerate -m "create_strategy_tables"
alembic upgrade head
```

Update migrations/env.py to import strategy models.

---

## Acceptance Criteria

### Models and Migration
1. Strategy model exists with all fields, unique constraint on key, user_id FK
2. StrategyConfig model exists with config_json (JSON type), unique on (strategy_id, version)
3. StrategyState model exists with state_json, unique on strategy_id (one per strategy)
4. StrategyEvaluation model exists with all tracking fields
5. PositionOverride model exists with override_type and value JSONs
6. Alembic migration creates all five tables and applies cleanly

### CRUD
7. POST /strategies creates strategy with config validation, returns 201
8. GET /strategies returns paginated list for the authenticated user
9. GET /strategies/:id returns strategy detail with active config (user ownership enforced)
10. PUT /strategies/:id/config updates config, creates new version if enabled
11. PUT /strategies/:id/meta updates name/description without versioning
12. DELETE /strategies/:id only works for draft strategies
13. Row-level security: users can only see/modify their own strategies

### Validation
14. Validator checks config completeness (entry conditions, exit mechanism, sizing, symbols, timeframe)
15. Validator checks all indicator keys exist in registry
16. Validator checks indicator parameters are within valid ranges
17. Validator checks formula expressions parse correctly
18. Validator checks risk sanity (stop loss range, position size range)
19. Validation errors are returned with field paths and messages
20. Warnings are returned separately from errors (don't block saving)
21. POST /strategies/:id/validate runs validation without saving

### Lifecycle
22. Status transitions are enforced (draft→enabled, enabled→paused/disabled, etc.)
23. Invalid transitions return appropriate errors
24. Enable resets error count
25. Pause/disable is always allowed from enabled state

### Versioning
26. Config changes on enabled strategies create new version (1.0.0 → 1.1.0)
27. Config changes on draft strategies update in place (no new version)
28. Old versions are retained (is_active=false) for audit
29. GET /strategies/:id/versions returns version history

### Runner
30. Runner loop runs periodically and checks timeframe alignment
31. Timeframe alignment is correct (5m at :00/:05/:10, 1h at :00, etc.)
32. Runner resolves symbols correctly for all three modes (explicit, watchlist, filtered)
33. Runner fetches bars from MarketDataService
34. Runner evaluates entry conditions using ConditionEngine from TASK-008
35. Runner evaluates exit conditions (condition-based + SL/TP/trailing)
36. Stop loss, take profit, trailing stop calculations are correct
37. Runner persists StrategyEvaluation records
38. Runner handles per-strategy exceptions without affecting other strategies
39. Auto-pause triggers after STRATEGY_AUTO_PAUSE_ERROR_THRESHOLD consecutive errors
40. Runner is registered in main.py lifespan

### Safety Monitor
41. Safety monitor runs on 1-minute cycle
42. Safety monitor evaluates only price-based exits (SL/TP/trailing, not indicator conditions)
43. Safety monitor checks position overrides before strategy config
44. Safety monitor handles its own failures (logs, counts, alerts stub)
45. Safety monitor is registered in main.py lifespan

### Integration Points (Stubbed)
46. Signal emission is clearly stubbed with TODO/comment pointing to TASK-010
47. Position queries are clearly stubbed with TODO/comment pointing to TASK-013
48. Stubs return empty/None and don't break the evaluation flow

### General
49. All new error codes registered in common/errors.py
50. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-009-strategy-crud/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
