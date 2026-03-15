# TASK-012a — Paper Trading: Core Engine and Fill Simulation

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the core paper trading engine: order and fill models, the executor
abstraction, internal fill simulation (slippage + fees), order lifecycle
management, cash management, the background order consumer, and API endpoints.

After this task:
- Risk-approved signals are consumed and turned into PaperOrder records
- Orders are routed to the simulated executor (internal fill simulation)
- Fill simulation applies configurable slippage and fees per market
- PaperFill records are created with full execution audit (reference price,
  slippage amount, fee, gross/net value)
- Options orders are handled (contract multiplier, options-specific fields)
- Cash availability is checked before order execution
- The order lifecycle is tracked (pending → accepted → filled/rejected)
- API endpoints expose orders and fills
- The portfolio module is notified of fills (stub until TASK-013)

This task uses INTERNAL SIMULATION for ALL markets. The forex account pool
(TASK-012b) and Alpaca paper API (TASK-012c) are NOT in scope.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/paper_trading_module_spec.md — PRIMARY SPEC, sections 2-6, 10-12
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, inter-module interfaces
6. /studio/SPECS/risk_engine_module_spec.md — risk-to-paper-trading handoff (section 11)
7. Review TASK-010 and TASK-011 BUILDER_OUTPUT.md — understand signal/risk decision interfaces

## Constraints

- Do NOT implement the forex account pool (TASK-012b)
- Do NOT implement the Alpaca paper trading API integration (TASK-012c)
- Do NOT implement shadow tracking (TASK-012c)
- Do NOT implement BrokerAccount or AccountAllocation models
- Do NOT implement ShadowFill or ShadowPosition models
- Do NOT implement portfolio position tracking (TASK-013)
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- ALL markets use internal simulation in this task (no broker API calls)
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions (envelope, pagination, camelCase)
- All financial values use Decimal
- All timestamps are timezone-aware UTC

---

## Deliverables

### 1. Paper Trading Models (backend/app/paper_trading/models.py)

All models inherit from BaseModel.

**PaperOrder:**
```
PaperOrder:
  - id: UUID (from BaseModel)
  - signal_id: UUID (FK → signals.id, unique)
  - risk_decision_id: UUID (FK → risk_decisions.id)
  - strategy_id: UUID (FK → strategies.id)
  - symbol: str
  - market: str (equities | forex)
  - side: str (buy | sell)
  - order_type: str (market | limit)
  - signal_type: str (entry | exit | scale_in | scale_out)
  - requested_qty: Numeric
  - requested_price: Numeric, nullable (for limit orders)
  - filled_qty: Numeric (default 0)
  - filled_avg_price: Numeric, nullable
  - status: str (default "pending", values: pending | accepted | filled |
                  partially_filled | canceled | rejected)
  - rejection_reason: str, nullable
  - execution_mode: str (default "simulation", values: simulation | paper | live)
  - broker_order_id: str, nullable
  - broker_account_id: str, nullable
  - underlying_symbol: str, nullable (for options)
  - contract_type: str, nullable (call | put)
  - strike_price: Numeric, nullable
  - expiration_date: date, nullable
  - contract_multiplier: int (default 1, options use 100)
  - submitted_at: datetime
  - accepted_at: datetime, nullable
  - filled_at: datetime, nullable
  - created_at, updated_at (from BaseModel)

Indexes:
  UNIQUE (signal_id)
  INDEX (strategy_id, created_at)
  INDEX (symbol, status)
  INDEX (status)
  INDEX (broker_order_id) — partial, WHERE broker_order_id IS NOT NULL
```

**PaperFill:**
```
PaperFill:
  - id: UUID (from BaseModel)
  - order_id: UUID (FK → paper_orders.id)
  - strategy_id: UUID (FK → strategies.id)
  - symbol: str
  - side: str (buy | sell)
  - qty: Numeric
  - reference_price: Numeric (market price before slippage)
  - price: Numeric (execution price after slippage)
  - gross_value: Numeric (qty * price * contract_multiplier)
  - fee: Numeric
  - slippage_bps: Numeric (basis points applied)
  - slippage_amount: Numeric (dollar amount of slippage)
  - net_value: Numeric (gross ± fee)
  - broker_fill_id: str, nullable
  - broker_account_id: str, nullable
  - filled_at: datetime
  - created_at (from BaseModel)

Indexes:
  INDEX (order_id)
  INDEX (strategy_id, filled_at)
  INDEX (symbol, filled_at)
```

**All Numeric columns for financial fields. Never Float.**

### 2. Paper Trading Schemas (backend/app/paper_trading/schemas.py)

Use camelCase aliases (alias_generator=to_camel, populate_by_name=True).
Use by_alias=True on all model_dump() calls in the router.

**Response schemas:**
```python
class PaperOrderResponse(BaseModel):
    id: UUID
    signal_id: UUID
    risk_decision_id: UUID
    strategy_id: UUID
    symbol: str
    market: str
    side: str
    order_type: str
    signal_type: str
    requested_qty: Decimal
    requested_price: Decimal | None
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    status: str
    rejection_reason: str | None
    execution_mode: str
    broker_order_id: str | None
    broker_account_id: str | None
    underlying_symbol: str | None
    contract_type: str | None
    strike_price: Decimal | None
    expiration_date: date | None
    contract_multiplier: int
    submitted_at: datetime
    accepted_at: datetime | None
    filled_at: datetime | None
    created_at: datetime

class PaperFillResponse(BaseModel):
    id: UUID
    order_id: UUID
    strategy_id: UUID
    symbol: str
    side: str
    qty: Decimal
    reference_price: Decimal
    price: Decimal
    gross_value: Decimal
    fee: Decimal
    slippage_bps: Decimal
    slippage_amount: Decimal
    net_value: Decimal
    broker_fill_id: str | None
    broker_account_id: str | None
    filled_at: datetime
    created_at: datetime
```

**Query schemas:**
```python
class OrderQueryParams(BaseModel):
    strategy_id: UUID | None = None
    symbol: str | None = None
    status: str | None = None
    signal_type: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    page: int = 1
    page_size: int = 20

class FillQueryParams(BaseModel):
    strategy_id: UUID | None = None
    symbol: str | None = None
    side: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    page: int = 1
    page_size: int = 20
```

### 3. Executor Abstraction (backend/app/paper_trading/executors/base.py)

```python
from dataclasses import dataclass
from decimal import Decimal
from abc import ABC, abstractmethod

@dataclass
class OrderResult:
    success: bool
    order_id: UUID | None = None
    broker_order_id: str | None = None
    status: str = ""  # accepted | rejected
    rejection_reason: str | None = None

@dataclass
class FillResult:
    order_id: UUID
    qty: Decimal
    reference_price: Decimal
    price: Decimal  # after slippage
    fee: Decimal
    slippage_bps: Decimal
    slippage_amount: Decimal
    gross_value: Decimal
    net_value: Decimal
    filled_at: datetime
    broker_fill_id: str | None = None

class Executor(ABC):
    """Abstract executor interface.
    
    Every execution mode (simulation, Alpaca paper, forex pool)
    implements this interface. The paper trading service routes
    to the correct executor based on market and config.
    """
    
    @property
    @abstractmethod
    def execution_mode(self) -> str:
        """Return the execution mode name (e.g., 'simulation', 'paper')."""
    
    @abstractmethod
    async def submit_order(self, order: 'PaperOrder',
                           reference_price: Decimal) -> OrderResult:
        """Submit an order for execution.
        
        Returns OrderResult with acceptance/rejection status.
        For simulation: processes immediately.
        For broker APIs: submits to broker, returns acceptance.
        """
    
    @abstractmethod
    async def simulate_fill(self, order: 'PaperOrder',
                            reference_price: Decimal) -> FillResult:
        """Simulate or record a fill for an accepted order.
        
        For simulation: calculates fill price with slippage and fees.
        For broker APIs: waits for broker fill notification.
        """
    
    @abstractmethod
    async def cancel_order(self, order: 'PaperOrder') -> bool:
        """Cancel a pending/accepted order. Returns True if successful."""
```

### 4. Slippage Model (backend/app/paper_trading/fill_simulation/slippage.py)

```python
class SlippageModel:
    """Applies slippage to a reference price.
    
    Slippage always works against the trader:
    - Buys: price increases (pay more)
    - Sells: price decreases (receive less)
    """
    
    def apply(self, reference_price: Decimal, side: str,
              slippage_bps: Decimal) -> tuple[Decimal, Decimal]:
        """Apply slippage to a reference price.
        
        Returns: (execution_price, slippage_amount)
        
        For buys:  execution_price = reference * (1 + bps / 10000)
        For sells: execution_price = reference * (1 - bps / 10000)
        slippage_amount = abs(execution_price - reference) * qty
        """
```

### 5. Fee Model (backend/app/paper_trading/fill_simulation/fees.py)

```python
class FeeModel:
    """Calculates trading fees based on market configuration.
    
    Fee types:
    - per_trade: flat amount per order
    - spread_bps: basis points of gross value (forex spread cost)
    """
    
    def calculate(self, gross_value: Decimal, market: str,
                  config: 'PaperTradingConfig') -> Decimal:
        """Calculate the fee for a fill.
        
        Equities: PAPER_TRADING_FEE_PER_TRADE_EQUITIES (default: 0)
        Forex: gross_value * PAPER_TRADING_FEE_SPREAD_BPS_FOREX / 10000
        Options: PAPER_TRADING_FEE_PER_TRADE_OPTIONS (default: 0)
        """
```

### 6. Fill Simulation Engine (backend/app/paper_trading/fill_simulation/engine.py)

```python
class FillSimulationEngine:
    """Orchestrates fill simulation: reference price → slippage → fees → result.
    
    Used by the SimulatedExecutor for all internal simulation fills.
    """
    
    def __init__(self, slippage_model: SlippageModel, fee_model: FeeModel,
                 config: 'PaperTradingConfig'):
        self._slippage = slippage_model
        self._fee = fee_model
        self._config = config
    
    async def simulate(self, order: 'PaperOrder',
                       reference_price: Decimal) -> FillResult:
        """Simulate a fill for an order.
        
        Steps:
        1. Determine slippage BPS from config based on market
           (equities, forex, options — different defaults)
        2. Apply slippage to reference price
        3. Calculate gross value: qty * execution_price * contract_multiplier
        4. Calculate fee based on market
        5. Calculate net value:
           - Buys: gross_value + fee (total cost)
           - Sells: gross_value - fee (net proceeds)
        6. Return FillResult with all values
        """
    
    def _get_slippage_bps(self, order: 'PaperOrder') -> Decimal:
        """Get slippage BPS for this order's market.
        
        Options: use options BPS if underlying_symbol is set
        Equities: use equities BPS
        Forex: use forex BPS
        """
```

### 7. Simulated Executor (backend/app/paper_trading/executors/simulated.py)

```python
class SimulatedExecutor(Executor):
    """Internal fill simulation executor.
    
    Used for: forex paper trading, backtesting, offline testing,
    and as fallback when broker APIs are unavailable.
    
    Processing is synchronous (within an async call) — fills happen
    immediately since there's no broker to wait for.
    """
    
    execution_mode = "simulation"
    
    def __init__(self, fill_engine: FillSimulationEngine):
        self._fill_engine = fill_engine
    
    async def submit_order(self, order, reference_price):
        """Accept the order immediately (simulation has no queue)."""
        return OrderResult(success=True, status="accepted")
    
    async def simulate_fill(self, order, reference_price):
        """Calculate fill using the fill simulation engine."""
        return await self._fill_engine.simulate(order, reference_price)
    
    async def cancel_order(self, order):
        """Cancel is always successful in simulation (no broker state)."""
        return True
```

### 8. Cash Manager (backend/app/paper_trading/cash_manager.py)

```python
class CashManager:
    """Checks cash availability for orders.
    
    Reads cash balance from portfolio module (stubbed until TASK-013).
    Does NOT own cash state — only queries and validates.
    """
    
    async def check_availability(self, db: AsyncSession,
                                 required_cash: Decimal,
                                 market: str,
                                 broker_account_id: str | None = None
                                 ) -> tuple[bool, Decimal]:
        """Check if enough cash is available.
        
        Returns: (is_available: bool, available_cash: Decimal)
        
        For equities: checks total portfolio cash
        For forex with account pool (future): checks specific account cash
        
        NOTE: Until TASK-013, returns (True, initial_cash) as a stub.
        The stub uses PAPER_TRADING_INITIAL_CASH from config.
        """
    
    def calculate_required_cash(self, order: 'PaperOrder',
                                reference_price: Decimal) -> Decimal:
        """Calculate cash required for an order.
        
        For buys: qty * reference_price * contract_multiplier + estimated_fee
        For sells: 0 (closing positions releases cash, doesn't consume it)
        """
```

### 9. Paper Trading Repository (backend/app/paper_trading/repository.py)

```python
class PaperOrderRepository:
    async def create(self, db, order: PaperOrder) -> PaperOrder
    async def get_by_id(self, db, order_id: UUID) -> PaperOrder | None
    async def get_by_signal_id(self, db, signal_id: UUID) -> PaperOrder | None
    async def get_filtered(self, db, strategy_id=None, symbol=None,
                           status=None, signal_type=None,
                           date_start=None, date_end=None,
                           page=1, page_size=20) -> tuple[list, int]
    async def update(self, db, order: PaperOrder) -> PaperOrder
    async def get_pending_for_symbol(self, db, strategy_id: UUID,
                                     symbol: str, side: str) -> PaperOrder | None
        """Used by risk engine's duplicate order check (wired in later)."""

class PaperFillRepository:
    async def create(self, db, fill: PaperFill) -> PaperFill
    async def get_by_id(self, db, fill_id: UUID) -> PaperFill | None
    async def get_by_order_id(self, db, order_id: UUID) -> list[PaperFill]
    async def get_filtered(self, db, strategy_id=None, symbol=None,
                           side=None, date_start=None, date_end=None,
                           page=1, page_size=20) -> tuple[list, int]
    async def get_recent(self, db, limit: int = 20) -> list[PaperFill]
```

### 10. Paper Trading Errors (backend/app/paper_trading/errors.py)

```python
class OrderNotFoundError(DomainError):
    # PAPER_TRADING_ORDER_NOT_FOUND, 404

class OrderRejectedError(DomainError):
    # PAPER_TRADING_ORDER_REJECTED, 400

class InsufficientCashError(DomainError):
    # PAPER_TRADING_INSUFFICIENT_CASH, 400

class FillNotFoundError(DomainError):
    # PAPER_TRADING_FILL_NOT_FOUND, 404

class ExecutionError(DomainError):
    # PAPER_TRADING_EXECUTION_ERROR, 500

class OrderAlreadyFilledError(DomainError):
    # PAPER_TRADING_ORDER_ALREADY_FILLED, 409
```

Register in common/errors.py.

### 11. Paper Trading Config (backend/app/paper_trading/config.py)

```python
class PaperTradingConfig:
    def __init__(self):
        s = get_settings()
        # Execution modes
        self.execution_mode_equities = s.paper_trading_execution_mode_equities
        self.execution_mode_forex = s.paper_trading_execution_mode_forex
        self.broker_fallback = s.paper_trading_broker_fallback
        # Slippage
        self.slippage_bps_equities = Decimal(str(s.paper_trading_slippage_bps_equities))
        self.slippage_bps_forex = Decimal(str(s.paper_trading_slippage_bps_forex))
        self.slippage_bps_options = Decimal(str(s.paper_trading_slippage_bps_options))
        # Fees
        self.fee_per_trade_equities = Decimal(str(s.paper_trading_fee_per_trade_equities))
        self.fee_spread_bps_forex = Decimal(str(s.paper_trading_fee_spread_bps_forex))
        self.fee_per_trade_options = Decimal(str(s.paper_trading_fee_per_trade_options))
        # Options
        self.default_contract_multiplier = s.paper_trading_default_contract_multiplier
        # Cash
        self.initial_cash = Decimal(str(s.paper_trading_initial_cash))
        # Forex pool (used by TASK-012b, included here for config completeness)
        self.forex_account_pool_size = s.paper_trading_forex_account_pool_size
        self.forex_capital_per_account = Decimal(str(s.paper_trading_forex_capital_per_account))
```

All Decimal conversions use `Decimal(str(...))` to avoid float precision issues.

### 12. Paper Trading Service (backend/app/paper_trading/service.py)

```python
class PaperTradingService:
    """Consumes risk-approved signals and produces orders and fills."""
    
    def __init__(self, config: PaperTradingConfig,
                 simulated_executor: SimulatedExecutor,
                 cash_manager: CashManager):
        self._config = config
        self._simulated_executor = simulated_executor
        self._cash_manager = cash_manager
        self._order_repo = PaperOrderRepository()
        self._fill_repo = PaperFillRepository()
    
    async def process_approved_signals(self, db: AsyncSession) -> dict:
        """Process all risk-approved/modified signals.
        
        Called periodically by the background order consumer.
        
        1. Query signals with status in (risk_approved, risk_modified)
        2. For each signal:
           a. Get the risk decision (for modifications if any)
           b. Create a PaperOrder
           c. Route to executor
           d. Process the fill
        3. Return summary: {processed: N, filled: N, rejected: N}
        """
    
    async def process_signal(self, db: AsyncSession,
                             signal: 'Signal') -> PaperOrder:
        """Process a single approved signal into an order and fill.
        
        Steps:
        1. Get the risk decision for this signal
        2. Determine order parameters:
           - If risk_modified: use modifications_json values
           - If risk_approved: use original signal values
        3. Determine requested_qty from strategy config position sizing
        4. Get reference price from MarketDataService
        5. Check cash availability (CashManager)
        6. Create PaperOrder (status: pending)
        7. Get the executor (simulated for now — all markets)
        8. Submit order to executor (→ accepted)
        9. Simulate fill (→ FillResult)
        10. Create PaperFill record
        11. Update PaperOrder (status: filled, filled_qty, filled_avg_price)
        12. Notify portfolio: portfolio_service.process_fill(fill)
            (STUB: log only until TASK-013)
        13. Return the order
        
        On any failure:
        - Update order status to "rejected" with reason
        - Log the failure
        - Do NOT throw exception to caller
        """
    
    async def _determine_qty(self, db: AsyncSession, signal: 'Signal',
                             risk_decision: 'RiskDecision',
                             reference_price: Decimal) -> Decimal:
        """Calculate order quantity from strategy config.
        
        Methods:
        - fixed_qty: use value directly
        - fixed_dollar: value / reference_price
        - percent_equity: (equity * value/100) / reference_price
        - risk_based: (equity * risk_percent/100) / (entry - stop_price)
        
        If risk_modified with qty change: use modified qty instead.
        
        Round to appropriate precision:
        - Equities: whole shares (floor)
        - Forex: no rounding needed (fractional lots)
        - Options: whole contracts (floor)
        
        NOTE: equity is stubbed to INITIAL_CASH until TASK-013.
        """
    
    async def _get_executor(self, market: str) -> Executor:
        """Get the appropriate executor for a market.
        
        For this task: always returns SimulatedExecutor.
        TASK-012b adds ForexPoolExecutor for forex.
        TASK-012c adds AlpacaPaperExecutor for equities.
        """
    
    async def _get_reference_price(self, db: AsyncSession,
                                   symbol: str) -> Decimal | None:
        """Get the reference price for fill simulation.
        
        Uses MarketDataService.get_latest_close(symbol, "1m").
        Falls back to strategy timeframe if 1m not available.
        Returns None if no price available (order will be rejected).
        """
    
    # --- Read Operations ---
    
    async def get_order(self, db, order_id: UUID, user_id: UUID) -> PaperOrder:
        """Get order by ID. Verify ownership through strategy."""
    
    async def list_orders(self, db, user_id: UUID, **filters) -> tuple[list, int]:
        """List orders with filters. Enforce ownership."""
    
    async def get_fill(self, db, fill_id: UUID, user_id: UUID) -> PaperFill:
        """Get fill by ID. Verify ownership."""
    
    async def list_fills(self, db, user_id: UUID, **filters) -> tuple[list, int]:
        """List fills with filters. Enforce ownership."""
    
    async def get_order_fills(self, db, order_id: UUID,
                              user_id: UUID) -> list[PaperFill]:
        """Get all fills for an order."""
    
    async def get_recent_fills(self, db, user_id: UUID,
                               limit: int = 20) -> list[PaperFill]:
        """Get recent fills across all strategies."""
```

### 13. Order Consumer Background Task (backend/app/paper_trading/consumer.py)

```python
class OrderConsumer:
    """Background task that periodically consumes risk-approved signals.
    
    Runs frequently (every few seconds) to minimize latency between
    risk approval and order execution.
    """
    
    def __init__(self, service: PaperTradingService):
        self._service = service
        self._running = False
    
    async def start(self) -> None:
        """Start the consumer loop."""
    
    async def stop(self) -> None:
        """Stop the consumer loop."""
    
    async def _run_loop(self) -> None:
        """Periodically call service.process_approved_signals().
        
        Interval: 2 seconds (fast enough for near-real-time,
        slow enough to not hammer the database).
        """
```

### 14. Paper Trading Router (backend/app/paper_trading/router.py)

Replace the empty stub.

```
# Orders
GET  /api/v1/paper-trading/orders              → list orders (paginated, filtered)
GET  /api/v1/paper-trading/orders/:id          → order detail
GET  /api/v1/paper-trading/orders/:id/fills    → fills for an order

# Fills
GET  /api/v1/paper-trading/fills               → list fills (paginated, filtered)
GET  /api/v1/paper-trading/fills/recent        → recent fills (default 20)
GET  /api/v1/paper-trading/fills/:id           → fill detail
```

All endpoints require auth (get_current_user).
All enforce user ownership through strategy chain.
All responses use standard {"data": ...} envelope with camelCase.
All model_dump() calls use by_alias=True.

### 15. Paper Trading Startup (backend/app/paper_trading/startup.py)

```python
async def start_paper_trading() -> None:
    """Initialize paper trading module.
    
    1. Load config
    2. Create fill simulation components (slippage model, fee model, engine)
    3. Create SimulatedExecutor
    4. Create CashManager
    5. Create PaperTradingService
    6. Create and start OrderConsumer
    """

async def stop_paper_trading() -> None:
    """Stop the order consumer."""

def get_paper_trading_service() -> PaperTradingService:
    """Get the service singleton for inter-module use."""
```

### 16. Register in main.py

Add paper trading startup/shutdown to lifespan, after risk:

```python
await start_market_data(db)
await start_strategies()
await start_signals()
await start_risk()
await start_paper_trading()
# ...
await stop_paper_trading()
await stop_risk()
await stop_signals()
await stop_strategies()
await stop_market_data()
```

### 17. Wire Risk Engine Duplicate Order Check

Update backend/app/risk/checks/duplicate.py to use the PaperOrderRepository
instead of always returning PASS:

```python
class DuplicateOrderCheck(RiskCheck):
    async def evaluate(self, signal, context):
        # Query for pending/accepted order for same strategy + symbol + side
        # If found → reject("duplicate_order", "Order already pending...")
        # If not found → pass
```

This requires importing from paper_trading. Use lazy import to avoid
circular dependencies.

### 18. Alembic Migration

Create migration for paper_orders and paper_fills tables:

```bash
cd backend
alembic revision --autogenerate -m "create_paper_trading_tables"
alembic upgrade head
```

Update migrations/env.py to import paper_trading models.

---

## Acceptance Criteria

### Models and Migration
1. PaperOrder model exists with all fields, all financial fields use Numeric
2. PaperOrder has unique constraint on signal_id
3. PaperFill model exists with all fields, all financial fields use Numeric
4. Alembic migration creates both tables and applies cleanly
5. migrations/env.py imports paper_trading models

### Executor Abstraction
6. Executor abstract base class defines submit_order, simulate_fill, cancel_order
7. OrderResult and FillResult dataclasses exist with all fields
8. SimulatedExecutor implements Executor interface using FillSimulationEngine

### Fill Simulation
9. SlippageModel applies slippage correctly (buys: price up, sells: price down)
10. SlippageModel uses configurable BPS per market (equities, forex, options)
11. FeeModel calculates fees correctly per market
12. Equities: commission-free (default 0)
13. Forex: spread-based fee (BPS of gross value)
14. Options: commission-free (default 0)
15. FillSimulationEngine orchestrates: reference price → slippage → fee → fill result
16. Gross value accounts for contract_multiplier (options: qty * 100 * price)
17. Net value: buys = gross + fee, sells = gross - fee
18. All fill calculations use Decimal arithmetic

### Cash Management
19. CashManager.calculate_required_cash correctly computes cash needed
20. Buy orders require cash (qty * price * multiplier + fee)
21. Sell orders require zero cash (releases, doesn't consume)
22. Cash availability check works (stubbed to initial_cash until TASK-013)

### Order Lifecycle
23. Orders are created with status="pending"
24. Accepted orders transition to status="accepted"
25. Filled orders transition to status="filled" with filled_qty and filled_avg_price
26. Rejected orders transition to status="rejected" with rejection_reason
27. Order rejection does not throw exceptions to the consumer

### Service
28. process_approved_signals() consumes risk_approved and risk_modified signals
29. process_signal() creates PaperOrder and PaperFill in one flow
30. For risk_modified signals: uses modifications_json values (e.g., reduced qty)
31. Position sizing calculation works for all four methods (fixed_qty, fixed_dollar, percent_equity, risk_based)
32. Reference price fetched from MarketDataService
33. Order rejected if no reference price available
34. Order rejected if insufficient cash
35. Portfolio notification is stubbed (TODO TASK-013)

### Order Consumer
36. OrderConsumer runs as a background task
37. Consumer polls at a short interval (~2 seconds)
38. Consumer processes all pending approved signals each cycle

### API
39. GET /paper-trading/orders returns filtered, paginated order list
40. GET /paper-trading/orders/:id returns order detail
41. GET /paper-trading/orders/:id/fills returns fills for an order
42. GET /paper-trading/fills returns filtered, paginated fill list
43. GET /paper-trading/fills/recent returns recent fills
44. GET /paper-trading/fills/:id returns fill detail
45. All endpoints enforce user ownership
46. All responses use standard {"data": ...} envelope with camelCase

### Integration
47. Risk engine duplicate order check wired to query paper_orders table
48. Startup/shutdown registered in main.py lifespan
49. All execution uses SimulatedExecutor (no broker API calls)

### General
50. PaperTradingConfig loads all settings with Decimal conversions
51. Paper trading error classes exist and registered in common/errors.py
52. Options orders use contract_multiplier=100 in value calculations
53. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-012a-paper-core/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
