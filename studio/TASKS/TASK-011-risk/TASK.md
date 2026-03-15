# TASK-011 — Risk Engine Implementation

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the complete risk engine: 12 ordered risk checks, risk decision
persistence, kill switch management, risk configuration, drawdown monitoring,
daily loss tracking, exposure calculations, and the risk evaluation pipeline
that consumes pending signals.

After this task:
- Pending signals are consumed by the risk engine and evaluated
- Each signal passes through 12 ordered checks (cheapest → most complex)
- Exit signals receive lighter evaluation (never blocked)
- Risk decisions are persisted with full context (checks passed, portfolio snapshot)
- Signal statuses are updated (risk_approved/risk_rejected/risk_modified)
- Kill switch (global and per-strategy) blocks entries but always allows exits
- Risk config is stored in the database (single row, editable via admin API)
- Config changes are audited (who changed what, when)
- Drawdown is tracked against peak equity with three threshold levels
- Daily loss is tracked with auto-reset at trading day boundaries
- Exposure calculations work per-symbol, per-strategy, and portfolio-wide
- The risk dashboard overview endpoint returns current risk state

Two integration points are stubbed because downstream modules don't exist:
- **Position/portfolio queries** — exposure/drawdown calculations use stubs
  that return zero/empty until TASK-013 (portfolio module) wires in real data
- **Paper trading handoff** — approved signals sit in risk_approved status
  until TASK-012 (paper trading) picks them up

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/risk_engine_module_spec.md — PRIMARY SPEC, read completely
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, inter-module interfaces
6. /studio/SPECS/signals_module_spec.md — signal-to-risk handoff contract (section 7)
7. Review TASK-010 BUILDER_OUTPUT.md — understand SignalService interface

## Constraints

- Do NOT implement paper trading or order creation
- Do NOT implement portfolio models (Position, PortfolioSnapshot)
- Do NOT create models for paper_trading or portfolio modules
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions (envelope, pagination, camelCase)
- All financial values use Decimal
- All timestamps are timezone-aware UTC
- Core principle: **default to rejection** — if uncertain, reject

---

## Deliverables

### 1. Risk Models (backend/app/risk/models.py)

All models inherit from BaseModel.

**RiskDecision:**
```
RiskDecision:
  - id: UUID (from BaseModel)
  - signal_id: UUID (FK → signals.id, unique — one decision per signal)
  - status: str (approved | rejected | modified)
  - checks_passed: JSON (list of check names that passed)
  - failed_check: str, nullable (name of check that caused rejection)
  - reason_code: str
  - reason_text: str
  - modifications_json: JSON, nullable (what changed if modified)
  - portfolio_state_snapshot: JSON (portfolio state at decision time)
  - ts: datetime (UTC)
  - created_at (from BaseModel)

Indexes:
  UNIQUE (signal_id)
  INDEX (status, created_at)
  INDEX (reason_code)
  INDEX (ts)
```

**KillSwitch:**
```
KillSwitch:
  - id: UUID (from BaseModel)
  - scope: str (global | strategy)
  - strategy_id: UUID, nullable (FK → strategies.id, required if scope=strategy)
  - is_active: bool (default false)
  - activated_by: str, nullable (user | system | safety_monitor)
  - activated_at: datetime, nullable
  - deactivated_at: datetime, nullable
  - reason: str, nullable
  - created_at, updated_at (from BaseModel)

Indexes:
  INDEX (scope, is_active)
  INDEX (strategy_id, is_active)
```

**RiskConfig:**
```
RiskConfig:
  - id: UUID (from BaseModel)
  - max_position_size_percent: Numeric (default 10.0)
  - max_symbol_exposure_percent: Numeric (default 20.0)
  - max_strategy_exposure_percent: Numeric (default 30.0)
  - max_total_exposure_percent: Numeric (default 80.0)
  - max_drawdown_percent: Numeric (default 10.0)
  - max_drawdown_catastrophic_percent: Numeric (default 20.0)
  - max_daily_loss_percent: Numeric (default 3.0)
  - max_daily_loss_amount: Numeric, nullable
  - min_position_value: Numeric (default 100.0)
  - updated_by: str, nullable
  - created_at, updated_at (from BaseModel)

Single row table — one active config.
All Numeric fields (never Float).
```

**RiskConfigAudit:**
```
RiskConfigAudit:
  - id: UUID (from BaseModel)
  - field_changed: str
  - old_value: str
  - new_value: str
  - changed_by: str
  - changed_at: datetime
  - created_at (from BaseModel)

Indexes:
  INDEX (changed_at)
```

### 2. Risk Check Interface (backend/app/risk/checks/base.py)

```python
from dataclasses import dataclass
from enum import Enum

class CheckOutcome(Enum):
    PASS = "pass"
    REJECT = "reject"
    MODIFY = "modify"

@dataclass
class CheckResult:
    outcome: CheckOutcome
    reason_code: str = ""
    reason_text: str = ""
    modifications: dict | None = None

class RiskCheck(ABC):
    """Base class for all risk checks."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Check name for logging and audit (e.g., 'symbol_exposure_limit')."""
    
    @property
    @abstractmethod
    def applies_to_exits(self) -> bool:
        """Whether this check runs for exit signals."""
    
    @abstractmethod
    async def evaluate(self, signal: Signal, context: 'RiskContext') -> CheckResult:
        """Evaluate the signal against this check.
        
        Returns CheckResult with outcome, reason, and optional modifications.
        """
```

### 3. Risk Context (backend/app/risk/checks/base.py or separate file)

Shared context passed to all checks to avoid redundant DB queries:

```python
@dataclass
class RiskContext:
    """Shared context for risk evaluation. Loaded once, used by all checks."""
    risk_config: RiskConfig
    strategy: Strategy
    strategy_config: dict
    portfolio_equity: Decimal
    portfolio_cash: Decimal
    peak_equity: Decimal
    current_drawdown_percent: Decimal
    daily_realized_loss: Decimal
    symbol_exposure: dict[str, Decimal]  # symbol → total value
    strategy_exposure: dict[str, Decimal]  # strategy_id → total value
    total_exposure: Decimal
    open_positions_count: int
    strategy_positions_count: int
    current_price: Decimal | None
    kill_switch_global: bool
    kill_switch_strategy: bool
    
    # NOTE: Most portfolio-related fields are stubbed (return 0/empty)
    # until TASK-013 (portfolio module) provides real data.
```

### 4. Individual Risk Checks (backend/app/risk/checks/)

Create one file per check (or group closely related ones):

**kill_switch.py:**
```python
class KillSwitchCheck(RiskCheck):
    name = "kill_switch"
    applies_to_exits = False  # exits always allowed
    
    async def evaluate(self, signal, context):
        if context.kill_switch_global or context.kill_switch_strategy:
            if signal.signal_type in ("entry", "scale_in"):
                return CheckResult(REJECT, "global_kill_switch",
                                   "Trading is halted")
        return CheckResult(PASS)
```

**strategy_enable.py:**
```python
class StrategyEnableCheck(RiskCheck):
    name = "strategy_enable"
    applies_to_exits = False
    
    async def evaluate(self, signal, context):
        # Bypass for manual, safety, system sources
        if signal.source in ("manual", "safety", "system"):
            return CheckResult(PASS)
        if context.strategy.status != "enabled":
            return CheckResult(REJECT, "strategy_not_enabled", ...)
        return CheckResult(PASS)
```

**symbol.py:**
```python
class SymbolTradabilityCheck(RiskCheck):
    name = "symbol_tradability"
    applies_to_exits = True  # applies but lenient for exits
    
class MarketHoursCheck(RiskCheck):
    name = "market_hours"
    applies_to_exits = True  # exits queued, not rejected
```

**duplicate.py:**
```python
class DuplicateOrderCheck(RiskCheck):
    name = "duplicate_order"
    applies_to_exits = False
    # Check pending/open orders for same strategy + symbol + side
    # NOTE: stubbed until paper trading module (TASK-012) — always passes
```

**position_limit.py:**
```python
class PositionLimitCheck(RiskCheck):
    name = "position_limit"
    applies_to_exits = False
    # Check current_positions >= max_positions from strategy config
    # NOTE: positions count stubbed to 0 until TASK-013
```

**position_sizing.py:**
```python
class PositionSizingCheck(RiskCheck):
    name = "position_sizing"
    applies_to_exits = False
    # Calculate requested size based on strategy config method
    # Cap at max_position_size_percent from risk config
    # Can return MODIFY with reduced qty
```

**exposure.py:**
```python
class SymbolExposureCheck(RiskCheck):
    name = "symbol_exposure_limit"
    applies_to_exits = False
    # Check combined exposure to symbol across all strategies
    # Can return MODIFY with reduced size if remaining capacity exists

class StrategyExposureCheck(RiskCheck):
    name = "strategy_exposure_limit"
    applies_to_exits = False
    # Check total exposure for this strategy

class PortfolioExposureCheck(RiskCheck):
    name = "portfolio_exposure_limit"
    applies_to_exits = False
    # Check total exposure across all strategies
```

**drawdown.py:**
```python
class DrawdownCheck(RiskCheck):
    name = "drawdown_limit"
    applies_to_exits = False
    # Check current drawdown against max_drawdown_percent
    # Only blocks entries
```

**daily_loss.py:**
```python
class DailyLossCheck(RiskCheck):
    name = "daily_loss_limit"
    applies_to_exits = False
    # Check daily realized loss against limit
    # Only blocks entries
```

### 5. Risk Check Registry (backend/app/risk/checks/__init__.py)

Register all checks in the correct order:

```python
def get_risk_checks() -> list[RiskCheck]:
    """Return all risk checks in evaluation order."""
    return [
        KillSwitchCheck(),
        StrategyEnableCheck(),
        SymbolTradabilityCheck(),
        MarketHoursCheck(),
        DuplicateOrderCheck(),
        PositionLimitCheck(),
        PositionSizingCheck(),
        SymbolExposureCheck(),
        StrategyExposureCheck(),
        PortfolioExposureCheck(),
        DrawdownCheck(),
        DailyLossCheck(),
    ]
```

### 6. Risk Schemas (backend/app/risk/schemas.py)

Use camelCase aliases (alias_generator=to_camel, populate_by_name=True, by_alias=True on all model_dump calls).

```python
class RiskDecisionResponse(BaseModel):
    id, signal_id, status, checks_passed, failed_check,
    reason_code, reason_text, modifications_json,
    portfolio_state_snapshot, ts, created_at

class KillSwitchStatusResponse(BaseModel):
    global_active: bool
    strategies: list[dict]  # [{strategy_id, is_active, reason}]

class RiskConfigResponse(BaseModel):
    # all config fields as Decimal
    updated_at, updated_by

class UpdateRiskConfigRequest(BaseModel):
    # all config fields as optional Decimal

class KillSwitchRequest(BaseModel):
    scope: str  # global | strategy
    strategy_id: UUID | None = None
    reason: str | None = None

class RiskOverviewResponse(BaseModel):
    kill_switch: KillSwitchStatusResponse
    drawdown: dict  # current_percent, peak_equity, current_equity, threshold_status
    daily_loss: dict  # current_loss, limit, percent_used
    total_exposure: dict  # current_percent, limit_percent
    symbol_exposure: list[dict]  # [{symbol, current_percent, limit_percent}]
    strategy_exposure: list[dict]  # [{strategy_id, strategy_name, current_percent, limit_percent}]
    recent_decisions: list[dict]  # last N decisions summary

class RiskConfigAuditResponse(BaseModel):
    id, field_changed, old_value, new_value, changed_by, changed_at

class ExposureResponse(BaseModel):
    total_exposure_percent: Decimal
    total_exposure_value: Decimal
    by_symbol: list[dict]
    by_strategy: list[dict]

class DrawdownResponse(BaseModel):
    peak_equity: Decimal
    current_equity: Decimal
    drawdown_percent: Decimal
    threshold_status: str  # normal | warning | breach | catastrophic
    max_drawdown_percent: Decimal
    catastrophic_percent: Decimal
```

### 7. Risk Repository (backend/app/risk/repository.py)

```python
class RiskDecisionRepository:
    async def create(self, db, decision: RiskDecision) -> RiskDecision
    async def get_by_id(self, db, decision_id: UUID) -> RiskDecision | None
    async def get_by_signal_id(self, db, signal_id: UUID) -> RiskDecision | None
    async def get_filtered(self, db, status=None, reason_code=None,
                           date_start=None, date_end=None,
                           page=1, page_size=20) -> tuple[list, int]
    async def get_recent(self, db, limit: int = 10) -> list[RiskDecision]

class KillSwitchRepository:
    async def get_global(self, db) -> KillSwitch | None
    async def get_for_strategy(self, db, strategy_id: UUID) -> KillSwitch | None
    async def get_all_active(self, db) -> list[KillSwitch]
    async def upsert(self, db, kill_switch: KillSwitch) -> KillSwitch

class RiskConfigRepository:
    async def get_active(self, db) -> RiskConfig | None
    async def create_or_update(self, db, config: RiskConfig) -> RiskConfig
    async def seed_defaults(self, db) -> RiskConfig

class RiskConfigAuditRepository:
    async def create(self, db, audit: RiskConfigAudit) -> RiskConfigAudit
    async def get_history(self, db, page=1, page_size=20) -> tuple[list, int]
```

### 8. Risk Errors (backend/app/risk/errors.py)

```python
class RiskEvaluationError(DomainError):
    # RISK_EVALUATION_ERROR, 500

class RiskConfigNotFoundError(DomainError):
    # RISK_CONFIG_NOT_FOUND, 404

class KillSwitchAlreadyActiveError(DomainError):
    # RISK_KILL_SWITCH_ALREADY_ACTIVE, 409

class KillSwitchNotActiveError(DomainError):
    # RISK_KILL_SWITCH_NOT_ACTIVE, 409

class RiskDecisionNotFoundError(DomainError):
    # RISK_DECISION_NOT_FOUND, 404
```

Register in common/errors.py.

### 9. Risk Config Module (backend/app/risk/config.py)

```python
class RiskModuleConfig:
    def __init__(self):
        s = get_settings()
        self.default_max_position_size_percent = Decimal(str(s.risk_default_max_position_size_percent))
        self.default_max_symbol_exposure_percent = Decimal(str(s.risk_default_max_symbol_exposure_percent))
        # ... all defaults as Decimal
        self.evaluation_timeout = s.risk_evaluation_timeout_sec
```

### 10. Drawdown Monitor (backend/app/risk/monitoring/drawdown.py)

```python
class DrawdownMonitor:
    """Tracks peak equity and calculates current drawdown.
    
    NOTE: Until TASK-013 provides real portfolio data, equity values
    are stubbed. The monitor's logic is complete — it just needs
    real numbers flowing in.
    """
    
    async def get_current_drawdown(self, db) -> dict:
        """Return current drawdown state.
        
        Returns: {
            "peak_equity": Decimal,
            "current_equity": Decimal,
            "drawdown_percent": Decimal,
            "threshold_status": "normal" | "warning" | "breach" | "catastrophic"
        }
        """
    
    async def get_peak_equity(self, db) -> Decimal:
        """Get the current peak equity (high-water mark)."""
    
    async def reset_peak_equity(self, db, admin_user: str) -> None:
        """Manual peak equity reset (admin only). Logged."""
    
    def _get_threshold_status(self, drawdown_pct: Decimal,
                              config: RiskConfig) -> str:
        """Determine threshold level.
        
        normal: drawdown < max * 0.7
        warning: drawdown >= max * 0.7
        breach: drawdown >= max
        catastrophic: drawdown >= catastrophic threshold
        """
```

### 11. Daily Loss Monitor (backend/app/risk/monitoring/daily_loss.py)

```python
class DailyLossMonitor:
    """Tracks daily realized losses.
    
    NOTE: Until TASK-013 provides real realized PnL data,
    daily loss is stubbed to zero.
    """
    
    async def get_daily_loss(self, db) -> dict:
        """Return current daily loss state.
        
        Returns: {
            "current_loss": Decimal,
            "limit": Decimal,
            "percent_used": Decimal,
            "threshold_status": "normal" | "warning" | "breach",
            "resets_at": datetime
        }
        """
    
    def _get_trading_day_boundaries(self, market: str) -> tuple[datetime, datetime]:
        """Get start/end of current trading day.
        
        Equities: midnight to midnight ET
        Forex: 5 PM ET to 5 PM ET
        """
```

### 12. Exposure Calculator (backend/app/risk/monitoring/exposure.py)

```python
class ExposureCalculator:
    """Calculates exposure per-symbol, per-strategy, and portfolio-wide.
    
    NOTE: Until TASK-013, all exposure values return zero.
    """
    
    async def get_exposure(self, db, risk_config: RiskConfig) -> dict:
        """Calculate all exposure metrics.
        
        Returns: {
            "total_percent": Decimal,
            "total_value": Decimal,
            "by_symbol": {symbol: Decimal},
            "by_strategy": {strategy_id: Decimal},
            "portfolio_equity": Decimal
        }
        """
    
    async def get_symbol_exposure(self, db, symbol: str) -> Decimal:
        """Total value of positions in a symbol across all strategies."""
    
    async def get_strategy_exposure(self, db, strategy_id: UUID) -> Decimal:
        """Total value of positions for a strategy."""
```

### 13. Risk Service (backend/app/risk/service.py)

Main orchestration layer.

```python
class RiskService:
    """Risk evaluation pipeline and management."""
    
    def __init__(self, checks: list[RiskCheck]):
        self._checks = checks
    
    # --- Evaluation Pipeline ---
    
    async def evaluate_signal(self, db, signal: Signal) -> RiskDecision:
        """Evaluate a single signal through all risk checks.
        
        Steps:
        1. Load strategy and config for this signal
        2. Build RiskContext (portfolio state, exposure, kill switch, etc.)
        3. Check if signal is an exit → use fast path
        4. Run each check in order:
           a. Skip checks that don't apply to exits (if exit signal)
           b. If check returns REJECT → stop, create rejected decision
           c. If check returns MODIFY → record modification, continue
           d. If check returns PASS → record in checks_passed, continue
        5. If all checks pass (or modify) → create approved/modified decision
        6. Update signal status via SignalService
        7. Return the decision
        """
    
    async def evaluate_pending_signals(self, db) -> dict:
        """Evaluate all pending signals (called periodically).
        
        1. Get pending signals via SignalService.get_pending_signals()
        2. Evaluate each signal
        3. Return summary: {"evaluated": N, "approved": N, "rejected": N, "modified": N}
        """
    
    async def _build_context(self, db, signal: Signal,
                             strategy: Strategy) -> RiskContext:
        """Build the shared evaluation context.
        
        Loads: risk config, portfolio state, exposure data,
        kill switch state, positions count, current price.
        
        NOTE: Portfolio-related fields are stubbed until TASK-013.
        """
    
    async def _evaluate_exit_fast_path(self, db, signal: Signal,
                                       context: RiskContext) -> RiskDecision:
        """Fast path for exit signals.
        
        Only checks symbol tradability and market hours.
        Almost always approves. Never blocks exits.
        """
    
    # --- Kill Switch ---
    
    async def activate_kill_switch(self, db, scope: str,
                                   strategy_id: UUID | None,
                                   activated_by: str,
                                   reason: str | None) -> KillSwitch:
        """Activate global or strategy kill switch."""
    
    async def deactivate_kill_switch(self, db, scope: str,
                                     strategy_id: UUID | None) -> KillSwitch:
        """Deactivate kill switch."""
    
    async def get_kill_switch_status(self, db) -> dict:
        """Return current kill switch state for all scopes."""
    
    # --- Risk Config ---
    
    async def get_risk_config(self, db) -> RiskConfig:
        """Get active risk config. Seed defaults if none exists."""
    
    async def update_risk_config(self, db, updates: dict,
                                 changed_by: str) -> RiskConfig:
        """Update risk config fields. Log each change to audit table."""
    
    async def get_config_audit(self, db, page: int, page_size: int) -> tuple[list, int]:
        """Get risk config change history."""
    
    # --- Risk Overview ---
    
    async def get_overview(self, db) -> dict:
        """Get complete risk overview for dashboard.
        
        Combines: kill switch status, drawdown state, daily loss,
        exposure breakdown, recent decisions.
        """
    
    # --- Exposure ---
    
    async def get_exposure(self, db) -> dict:
        """Get current exposure breakdown."""
    
    # --- Drawdown ---
    
    async def get_drawdown(self, db) -> dict:
        """Get current drawdown state."""
    
    async def reset_peak_equity(self, db, admin_user: str) -> None:
        """Admin: manually reset peak equity."""
```

### 14. Risk Evaluation Background Task (backend/app/risk/evaluator.py)

```python
class RiskEvaluator:
    """Background task that periodically evaluates pending signals.
    
    Runs every N seconds, picks up pending signals, evaluates each.
    """
    
    def __init__(self, service: RiskService):
        self._service = service
        self._running = False
    
    async def start(self) -> None:
        """Start the evaluation loop."""
    
    async def stop(self) -> None:
        """Stop the evaluation loop."""
    
    async def _run_loop(self) -> None:
        """Periodically evaluate pending signals."""
```

### 15. Risk Router (backend/app/risk/router.py)

Replace the empty stub with full risk endpoints.

```
# Risk Decisions
GET  /api/v1/risk/decisions                → list decisions (paginated, filtered)
GET  /api/v1/risk/decisions/:id            → decision detail

# Risk Overview
GET  /api/v1/risk/overview                 → current risk state dashboard

# Kill Switch (admin only)
POST /api/v1/risk/kill-switch/activate     → activate kill switch
POST /api/v1/risk/kill-switch/deactivate   → deactivate kill switch
GET  /api/v1/risk/kill-switch/status       → current kill switch state

# Risk Configuration (admin only for PUT)
GET  /api/v1/risk/config                   → current risk configuration
PUT  /api/v1/risk/config                   → update risk configuration
GET  /api/v1/risk/config/audit             → config change history

# Exposure
GET  /api/v1/risk/exposure                 → current exposure breakdown

# Drawdown
GET  /api/v1/risk/drawdown                 → current drawdown state
POST /api/v1/risk/drawdown/reset-peak      → reset peak equity (admin only)
```

All GET endpoints require auth (get_current_user).
All POST/PUT endpoints require admin (require_admin).
All responses use standard {"data": ...} envelope with camelCase.

### 16. Risk Module Startup (backend/app/risk/startup.py)

```python
async def start_risk() -> None:
    """Initialize risk module.
    
    1. Seed risk config defaults if none exist
    2. Create RiskService with ordered checks
    3. Create RiskEvaluator (background task)
    4. Start the evaluator
    """

async def stop_risk() -> None:
    """Stop the risk evaluator."""

def get_risk_service() -> RiskService:
    """Get the risk service singleton."""
```

### 17. Register in main.py

Add risk startup/shutdown to lifespan, after signals:

```python
await start_market_data(db)
await start_strategies()
await start_signals()
await start_risk()
# ...
await stop_risk()
await stop_signals()
await stop_strategies()
await stop_market_data()
```

### 18. Alembic Migration

Create migration for all four risk tables (risk_decisions, kill_switches,
risk_config, risk_config_audit).

Update migrations/env.py to import risk models.

---

## Acceptance Criteria

### Models and Migration
1. RiskDecision model exists with all fields, unique constraint on signal_id
2. KillSwitch model exists with scope/strategy_id fields and indexes
3. RiskConfig model exists with all Numeric fields (never Float)
4. RiskConfigAudit model exists for change tracking
5. Alembic migration creates all four tables and applies cleanly

### Check Pipeline
6. RiskCheck base class defines name, applies_to_exits, and evaluate interface
7. CheckResult supports PASS, REJECT, and MODIFY outcomes
8. RiskContext is loaded once and shared across all checks
9. All 12 checks are implemented as separate classes
10. Checks execute in the correct order (kill switch first, daily loss last)
11. First rejection stops evaluation (remaining checks skipped)
12. MODIFY outcome records changes and continues to next check
13. Exit signals skip non-applicable checks (kill switch, limits, exposure, drawdown, daily loss)
14. Exit signals only check symbol tradability and market hours
15. Exit signals are almost always approved (never blocked for risk reasons)

### Individual Checks
16. Kill switch check blocks entries when active, allows exits
17. Strategy enable check allows manual/safety/system source signals to bypass
18. Symbol tradability checks watchlist
19. Market hours check queues exits (modify), rejects entries
20. Duplicate order check exists (stubbed — always passes until TASK-012)
21. Position limit check uses strategy config max_positions
22. Position sizing validates and caps at risk config max
23. Per-symbol exposure check can modify (reduce size) or reject
24. Per-strategy exposure check rejects when exceeded
25. Portfolio exposure check rejects when exceeded
26. Drawdown check only blocks entries
27. Daily loss check only blocks entries

### Risk Decisions
28. Every evaluation creates a RiskDecision record
29. Decision includes checks_passed list showing evaluation progress
30. Decision includes portfolio_state_snapshot at decision time
31. Modified decisions include modifications_json with original and adjusted values
32. Signal status is updated after decision (risk_approved/rejected/modified)

### Kill Switch
33. Global kill switch can be activated and deactivated via API
34. Strategy-specific kill switch works independently
35. Kill switch state persists across restarts (stored in database)
36. Kill switch activation/deactivation is logged

### Risk Configuration
37. Risk config is loaded from database (seeded with defaults on first run)
38. Risk config is editable via admin API
39. Every config change creates an audit record (field, old value, new value, who)
40. All config values are Decimal (never Float)

### Monitoring
41. Drawdown monitor calculates drawdown from peak equity
42. Drawdown threshold status is correct (normal/warning/breach/catastrophic)
43. Catastrophic drawdown auto-activates global kill switch
44. Peak equity can be manually reset (admin only, logged)
45. Daily loss monitor tracks realized losses (stubbed to zero until TASK-013)
46. Daily loss resets at trading day boundaries

### API
47. GET /risk/overview returns complete risk dashboard data
48. GET /risk/decisions returns paginated, filtered decision list
49. GET /risk/config returns current config
50. PUT /risk/config updates config with audit trail (admin only)
51. Kill switch endpoints work (activate, deactivate, status)
52. GET /risk/exposure returns exposure breakdown
53. GET /risk/drawdown returns drawdown state with threshold status
54. POST /risk/drawdown/reset-peak resets peak equity (admin only)
55. All responses use standard {"data": ...} envelope with camelCase

### Integration
56. RiskEvaluator runs as background task consuming pending signals
57. Approved signals have status updated to "risk_approved"
58. Rejected signals have status updated to "risk_rejected"
59. Modified signals have status updated to "risk_modified"
60. Risk module registered in main.py lifespan (start after signals, stop before signals)

### Stubs
61. Portfolio-related values in RiskContext are stubbed (zero/empty until TASK-013)
62. Duplicate order check is stubbed (always passes until TASK-012)
63. Stubs are clearly marked with TODO comments referencing future tasks

### General
64. Risk error classes exist and registered in common/errors.py
65. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-011-risk/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
