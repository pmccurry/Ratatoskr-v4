# TASK-012b — Paper Trading: Forex Pool, Alpaca Paper API, and Shadow Tracking

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Complete the paper trading module with three enhancements to the core engine
from TASK-012a: the forex account pool for FIFO netting compliance, the
Alpaca paper trading API executor for equities, and shadow tracking for
contention-blocked forex signals.

After this task:
- Forex signals route through the account pool (one position per pair per account)
- Account allocation and release are tracked in the database
- Contention-blocked signals are rejected with "no_available_account"
- Shadow tracking records what would have happened for blocked signals
- Shadow positions are fully managed (exit conditions, PnL on close)
- Equities orders route through the Alpaca paper trading API
- Alpaca fills are matched to internal orders via broker_order_id
- Alpaca fallback to simulation if broker API is unavailable
- Forex account pool status is visible via API
- Shadow analytics (comparison views) are available via API

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/paper_trading_module_spec.md — PRIMARY SPEC, sections 7-9
5. /studio/SPECS/cross_cutting_specs.md
6. Review TASK-012a BUILDER_OUTPUT.md — understand core engine

## Constraints

- Do NOT modify the fill simulation engine or slippage/fee models from TASK-012a
- Do NOT modify existing Position, CashBalance, or PortfolioMeta models
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern and API conventions
- All financial values use Decimal, all timestamps UTC

---

## Deliverables

### 1. Forex Pool Models (backend/app/paper_trading/forex_pool/models.py)

Wait — models should go in the module's models.py. Add to
backend/app/paper_trading/models.py:

**BrokerAccount:**
```
BrokerAccount:
  - id: UUID (from BaseModel)
  - broker: str (default "oanda")
  - account_id: str (virtual ID for paper, real ID for live)
  - account_type: str (paper_virtual | paper_real | live)
  - label: str (e.g., "Forex Pool Account 1")
  - is_active: bool (default true)
  - capital_allocation: Numeric
  - credentials_env_key: str, nullable
  - created_at, updated_at (from BaseModel)

Indexes:
  INDEX (broker, is_active)
  UNIQUE (account_id)
```

**AccountAllocation:**
```
AccountAllocation:
  - id: UUID (from BaseModel)
  - account_id: UUID (FK → broker_accounts.id)
  - strategy_id: UUID (FK → strategies.id)
  - symbol: str (the pair, e.g., EUR_USD)
  - side: str (long | short)
  - status: str (active | released)
  - allocated_at: datetime
  - released_at: datetime, nullable
  - created_at (from BaseModel)

Indexes:
  INDEX (account_id, symbol, status)
  INDEX (strategy_id, status)
  INDEX (symbol, status)
```

### 2. Shadow Tracking Models (backend/app/paper_trading/shadow/models.py)

Wait — same as above, add to backend/app/paper_trading/models.py:

**ShadowFill:**
```
ShadowFill:
  - id: UUID (from BaseModel)
  - signal_id: UUID (FK → signals.id)
  - strategy_id: UUID (FK → strategies.id)
  - symbol: str
  - side: str (buy | sell)
  - qty: Numeric
  - reference_price: Numeric
  - price: Numeric (after slippage)
  - fee: Numeric
  - slippage_bps: Numeric
  - gross_value: Numeric
  - net_value: Numeric
  - fill_type: str (entry | exit)
  - shadow_position_id: UUID (FK → shadow_positions.id)
  - filled_at: datetime
  - created_at (from BaseModel)

Indexes:
  INDEX (strategy_id, filled_at)
  INDEX (shadow_position_id)
```

**ShadowPosition:**
```
ShadowPosition:
  - id: UUID (from BaseModel)
  - strategy_id: UUID (FK → strategies.id)
  - symbol: str
  - side: str (long | short)
  - qty: Numeric
  - avg_entry_price: Numeric
  - current_price: Numeric
  - unrealized_pnl: Numeric
  - realized_pnl: Numeric (set when closed)
  - status: str (open | closed)
  - stop_loss_price: Numeric, nullable
  - take_profit_price: Numeric, nullable
  - trailing_stop_price: Numeric, nullable
  - highest_price_since_entry: Numeric, nullable
  - opened_at: datetime
  - closed_at: datetime, nullable
  - close_reason: str, nullable
  - entry_signal_id: UUID (FK → signals.id)
  - exit_signal_id: UUID, nullable
  - created_at, updated_at (from BaseModel)

Indexes:
  INDEX (strategy_id, status)
  INDEX (symbol, status)
```

All Numeric fields — never Float.

### 3. Forex Pool Manager (backend/app/paper_trading/forex_pool/pool_manager.py)

```python
class ForexPoolManager:
    """Manages the forex account pool for FIFO netting compliance.
    
    Each virtual account can hold multiple pairs but only ONE position
    per pair. Strategies are allocated accounts per-pair when they
    open positions. Accounts are released when positions close.
    """
    
    async def find_available_account(self, db, symbol: str) -> BrokerAccount | None:
        """Find an account with no active allocation for this pair.
        
        Query: accounts where account_id NOT IN
        (allocations where symbol=pair AND status='active')
        
        Returns first available account (first-come-first-served).
        Returns None if all accounts are occupied for this pair.
        """
    
    async def allocate(self, db, account_id: UUID, strategy_id: UUID,
                       symbol: str, side: str) -> AccountAllocation:
        """Create an active allocation for a strategy on an account.
        
        Creates AccountAllocation with status='active'.
        """
    
    async def release(self, db, strategy_id: UUID, symbol: str) -> None:
        """Release the allocation when a position closes.
        
        Sets status='released', released_at=now() on the matching allocation.
        """
    
    async def get_pool_status(self, db) -> dict:
        """Return current pool status for dashboard.
        
        Returns: {
            "accounts": [
                {"id": UUID, "label": str, "allocations": [
                    {"symbol": str, "side": str, "strategy_name": str, "since": datetime}
                ]}
            ],
            "pair_capacity": {
                "EUR_USD": {"occupied": 3, "total": 4, "available": 1},
                ...
            },
            "total_accounts": 4,
            "fully_empty": 1
        }
        """
    
    async def seed_accounts(self, db) -> int:
        """Create virtual accounts if they don't exist.
        
        Creates FOREX_ACCOUNT_POOL_SIZE accounts with sequential labels.
        Called during startup. Returns count created (0 if already exist).
        """
```

### 4. Forex Pool Allocation Repository (backend/app/paper_trading/forex_pool/allocation.py)

```python
class BrokerAccountRepository:
    async def get_all_active(self, db) -> list[BrokerAccount]
    async def get_available_for_symbol(self, db, symbol: str) -> BrokerAccount | None
    async def create(self, db, account: BrokerAccount) -> BrokerAccount
    async def get_by_id(self, db, account_id: UUID) -> BrokerAccount | None
    async def count(self, db) -> int

class AccountAllocationRepository:
    async def create(self, db, allocation: AccountAllocation) -> AccountAllocation
    async def get_active(self, db, account_id: UUID | None = None,
                         strategy_id: UUID | None = None,
                         symbol: str | None = None) -> list[AccountAllocation]
    async def release(self, db, strategy_id: UUID, symbol: str) -> None
    async def get_all_active(self, db) -> list[AccountAllocation]
```

### 5. Forex Pool Executor (backend/app/paper_trading/executors/forex_pool.py)

```python
class ForexPoolExecutor(Executor):
    """Executor for forex orders that routes through the account pool.
    
    Wraps the SimulatedExecutor (same fill simulation) but adds
    pool allocation before execution and pool release on position close.
    """
    
    execution_mode = "simulation"  # still internal simulation, just pool-managed
    
    def __init__(self, fill_engine: FillSimulationEngine,
                 pool_manager: ForexPoolManager):
        self._fill_engine = fill_engine
        self._pool = pool_manager
    
    async def submit_order(self, order, reference_price, db) -> OrderResult:
        """Submit a forex order with pool allocation.
        
        1. Find available account for this pair
        2. If none available:
           - Return OrderResult(success=False, rejection_reason="no_available_account")
        3. If available:
           - Allocate the account
           - Set order.broker_account_id to the account ID
           - Process fill via SimulatedExecutor
           - Return success
        """
    
    async def release_account(self, db, strategy_id: UUID, symbol: str) -> None:
        """Release the account allocation when a position closes.
        
        Called by the paper trading service after processing an exit fill
        for a forex position.
        """
```

### 6. Alpaca Paper Executor (backend/app/paper_trading/executors/alpaca_paper.py)

```python
class AlpacaPaperExecutor(Executor):
    """Executor that submits orders to the Alpaca paper trading API.
    
    Used for equities and options when execution_mode_equities = "paper".
    Falls back to SimulatedExecutor if the API is unavailable.
    """
    
    execution_mode = "paper"
    
    def __init__(self, config: PaperTradingConfig,
                 simulated_executor: SimulatedExecutor):
        self._config = config
        self._simulated = simulated_executor  # fallback
        self._client: httpx.AsyncClient | None = None
    
    async def submit_order(self, order, reference_price) -> OrderResult:
        """Submit order to Alpaca paper API.
        
        1. Build request: POST {base_url}/v2/orders
           body: {symbol, qty, side, type, time_in_force}
        2. Call Alpaca API with auth headers
        3. On success: return OrderResult with broker_order_id
        4. On failure: fall back to simulated executor, log warning
        """
    
    async def simulate_fill(self, order, reference_price) -> FillResult:
        """Get fill from Alpaca or simulate.
        
        For broker paper trading, the fill comes from Alpaca's response
        or trade_updates WebSocket. For MVP, poll the order status:
        
        1. GET {base_url}/v2/orders/{broker_order_id}
        2. If filled: extract fill price, qty from response
        3. If not filled yet: wait briefly, retry (up to 3 attempts)
        4. If still not filled: fall back to simulation with warning
        
        Return FillResult with broker-reported or simulated values.
        """
    
    async def cancel_order(self, order) -> bool:
        """Cancel via Alpaca API: DELETE {base_url}/v2/orders/{broker_order_id}"""
    
    async def _fallback_to_simulation(self, order, reference_price,
                                      reason: str) -> FillResult:
        """Fall back to internal simulation when broker API fails.
        
        Logs warning with reason. Returns simulated fill.
        """
```

### 7. Shadow Tracker (backend/app/paper_trading/shadow/tracker.py)

```python
class ShadowTracker:
    """Creates and manages shadow fills and positions for contention-blocked signals.
    
    Activated ONLY when:
    - SHADOW_TRACKING_ENABLED = true
    - Signal was blocked with reason_code = "no_available_account"
    - SHADOW_TRACKING_FOREX_ONLY = true (only forex)
    """
    
    def __init__(self, fill_engine: FillSimulationEngine,
                 config: PaperTradingConfig):
        self._fill_engine = fill_engine
        self._config = config
    
    async def create_shadow_entry(self, db, signal: 'Signal',
                                  order: 'PaperOrder',
                                  reference_price: Decimal) -> ShadowPosition:
        """Create a shadow fill and position for a blocked entry signal.
        
        1. Simulate fill using same engine as real fills (slippage + fees)
        2. Create ShadowPosition (open, with SL/TP/trailing from strategy config)
        3. Create ShadowFill (entry, linked to position)
        4. Return the shadow position
        """
    
    async def close_shadow_position(self, db, position: ShadowPosition,
                                    exit_price: Decimal,
                                    close_reason: str) -> ShadowPosition:
        """Close a shadow position with an exit fill.
        
        1. Calculate realized PnL (same formulas as real positions)
        2. Create ShadowFill (exit)
        3. Update ShadowPosition: status=closed, realized_pnl, close_reason
        4. Return updated position
        """
    
    def should_track(self, signal: 'Signal', rejection_reason: str) -> bool:
        """Check if shadow tracking should activate.
        
        True only if:
        - SHADOW_TRACKING_ENABLED
        - rejection_reason == "no_available_account"
        - signal.market == "forex" (if SHADOW_TRACKING_FOREX_ONLY)
        """
```

### 8. Shadow Position Evaluator (backend/app/paper_trading/shadow/evaluator.py)

```python
class ShadowEvaluator:
    """Evaluates exit conditions on open shadow positions.
    
    Called by the strategy runner as step 7b (after real position exits).
    Uses the same price-based exit logic as the safety monitor:
    stop loss, take profit, trailing stop checks.
    """
    
    async def evaluate_shadow_positions(self, db, strategy_id: UUID,
                                        config: dict) -> list[dict]:
        """Evaluate all open shadow positions for a strategy.
        
        For each open shadow position:
        1. Get current price from MarketDataService
        2. Update current_price, unrealized_pnl, highest_price
        3. Check stop loss
        4. Check take profit
        5. Check trailing stop (update trailing price)
        6. Check max hold bars
        7. If any triggered → close shadow position via ShadowTracker
        
        Returns list of closed shadow position summaries.
        """
    
    async def mark_to_market_shadows(self, db) -> int:
        """Update all open shadow positions with current prices.
        
        Called periodically (can piggyback on portfolio MTM cycle).
        Returns count of positions updated.
        """
```

### 9. Shadow Schemas and Repository

**Add to schemas.py:**
```python
class ShadowPositionResponse(BaseModel):
    # all fields from ShadowPosition model

class ShadowFillResponse(BaseModel):
    # all fields from ShadowFill model

class PoolStatusResponse(BaseModel):
    accounts: list[dict]
    pair_capacity: dict
    total_accounts: int
    fully_empty: int

class ShadowComparisonResponse(BaseModel):
    strategy_id: UUID
    strategy_name: str
    real_trades: int
    real_pnl: Decimal
    real_win_rate: Decimal
    shadow_trades: int
    shadow_pnl: Decimal
    shadow_win_rate: Decimal
    blocked_signals: int
    missed_pnl: Decimal
```

**Add to repository.py or create shadow/repository.py:**
```python
class ShadowFillRepository:
    async def create(self, db, fill: ShadowFill) -> ShadowFill
    async def get_by_position(self, db, position_id: UUID) -> list[ShadowFill]
    async def get_by_strategy(self, db, strategy_id: UUID) -> list[ShadowFill]

class ShadowPositionRepository:
    async def create(self, db, position: ShadowPosition) -> ShadowPosition
    async def get_open_by_strategy(self, db, strategy_id: UUID) -> list[ShadowPosition]
    async def get_all_open(self, db) -> list[ShadowPosition]
    async def update(self, db, position: ShadowPosition) -> ShadowPosition
    async def get_comparison_stats(self, db, strategy_id: UUID) -> dict
```

### 10. Update Paper Trading Service — Executor Routing

Update backend/app/paper_trading/service.py _get_executor():

```python
async def _get_executor(self, market: str, db=None) -> Executor:
    """Route to the correct executor based on market and config.
    
    Equities:
      if config.execution_mode_equities == "paper":
        return AlpacaPaperExecutor (with simulation fallback)
      else:
        return SimulatedExecutor
    
    Forex:
      return ForexPoolExecutor (wraps simulated with pool allocation)
    """
```

### 11. Update Paper Trading Service — Shadow Tracking Integration

In process_signal(), after an order is rejected with "no_available_account":

```python
if rejection_reason == "no_available_account" and self._shadow_tracker:
    if self._shadow_tracker.should_track(signal, rejection_reason):
        await self._shadow_tracker.create_shadow_entry(
            db, signal, order, reference_price)
```

### 12. Update Paper Trading Service — Account Release on Exit

When processing an exit fill for a forex position:

```python
if order.market == "forex" and order.signal_type in ("exit", "scale_out"):
    if self._forex_pool:
        await self._forex_pool.release(db, order.strategy_id, order.symbol)
```

### 13. Wire Shadow Evaluation into Strategy Runner

Update backend/app/strategies/runner.py evaluate_strategy():

After step 7 (real position exit evaluation), add step 7b:

```python
# Step 7b: Evaluate shadow position exits
if shadow_evaluator:
    shadow_exits = await shadow_evaluator.evaluate_shadow_positions(
        db, strategy.id, config_dict)
    # Log shadow exits but don't count them as real signals
```

### 14. Update Paper Trading Router

Add new endpoints to backend/app/paper_trading/router.py:

```
# Forex Pool
GET  /api/v1/paper-trading/forex-pool/status    → pool status dashboard
GET  /api/v1/paper-trading/forex-pool/accounts   → list all accounts with allocations

# Shadow Tracking
GET  /api/v1/paper-trading/shadow/positions      → list shadow positions (open/closed)
GET  /api/v1/paper-trading/shadow/positions/:id  → shadow position detail with fills
GET  /api/v1/paper-trading/shadow/comparison     → strategy comparison (real vs shadow)
```

All require auth, enforce ownership, use envelope + camelCase.

### 15. Update Startup

Update backend/app/paper_trading/startup.py:

```python
async def start_paper_trading() -> None:
    # ... existing setup ...
    # Add:
    # 1. Seed forex pool accounts if they don't exist
    # 2. Create ForexPoolExecutor
    # 3. Create AlpacaPaperExecutor (if API keys configured)
    # 4. Create ShadowTracker
    # 5. Update service with new executors and shadow tracker
```

### 16. Alembic Migration

Create migration for the four new tables: broker_accounts,
account_allocations, shadow_fills, shadow_positions.

Update migrations/env.py if models are in a new file.

---

## Acceptance Criteria

### Forex Pool Models and Migration
1. BrokerAccount model exists with all fields, unique account_id
2. AccountAllocation model exists with all fields and three indexes
3. All financial fields use Numeric
4. Alembic migration creates tables and applies cleanly

### Forex Pool Logic
5. find_available_account correctly queries for unoccupied accounts per pair
6. An account with EUR_USD occupied but GBP_USD free IS available for GBP_USD
7. An account with EUR_USD occupied is NOT available for another EUR_USD
8. allocate() creates an active allocation record
9. release() sets status=released and released_at on the allocation
10. seed_accounts() creates virtual accounts from config on startup
11. Pool status returns per-account allocations and per-pair capacity

### Forex Pool Integration
12. Forex orders route through ForexPoolExecutor
13. ForexPoolExecutor allocates an account before filling
14. ForexPoolExecutor rejects with "no_available_account" when pool is full for pair
15. Account released when forex exit fill is processed
16. broker_account_id set on PaperOrder and PaperFill for forex orders

### Alpaca Paper Executor
17. AlpacaPaperExecutor submits orders to Alpaca paper API
18. Alpaca auth headers sent correctly (APCA-API-KEY-ID, APCA-API-SECRET-KEY)
19. broker_order_id stored on PaperOrder from Alpaca response
20. Fill data extracted from Alpaca order status (price, qty, timestamp)
21. Fallback to SimulatedExecutor if Alpaca API unavailable
22. Fallback logs a warning with reason
23. Equities route through AlpacaPaperExecutor when config mode = "paper"
24. Equities route through SimulatedExecutor when config mode = "simulation"

### Shadow Tracking Models
25. ShadowFill model exists with all fields, all Numeric
26. ShadowPosition model exists with all fields including SL/TP/trailing
27. Migration creates both shadow tables

### Shadow Tracking Logic
28. Shadow tracking only activates for "no_available_account" rejections
29. Shadow tracking does NOT activate for risk rejections or other reasons
30. Shadow tracking is configurable (SHADOW_TRACKING_ENABLED, FOREX_ONLY)
31. Shadow entry fill uses same slippage/fee models as real fills
32. Shadow position created with SL/TP/trailing from strategy config
33. Shadow position exit conditions evaluated by ShadowEvaluator
34. Shadow position closes with realized PnL on exit
35. Shadow positions are marked to market (current_price, unrealized_pnl updated)

### Shadow Isolation
36. Shadow fills never affect real positions
37. Shadow positions never affect real portfolio equity
38. Shadow PnL never included in real performance metrics
39. Shadow positions never trigger real risk checks
40. Shadow positions never consume account pool allocations

### Runner Integration
41. Strategy runner evaluates shadow position exits (step 7b)

### API
42. GET /paper-trading/forex-pool/status returns pool dashboard data
43. GET /paper-trading/forex-pool/accounts returns account list with allocations
44. GET /paper-trading/shadow/positions returns shadow positions
45. GET /paper-trading/shadow/positions/:id returns detail with fills
46. GET /paper-trading/shadow/comparison returns real vs shadow performance
47. All new endpoints use {"data": ...} envelope with camelCase

### General
48. Startup seeds forex accounts and initializes new executors
49. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-012b-forex-shadow-alpaca/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
