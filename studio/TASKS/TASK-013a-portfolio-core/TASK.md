# TASK-013a — Portfolio: Positions, Cash, Fill Processing, and Mark-to-Market

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the core portfolio module and wire it into every module that
currently has portfolio-related stubs. This is the "unstubbing" task —
after it completes, the entire system works with real numbers.

After this task:
- Positions are created/updated when fills are processed
- Cash balances are tracked per account scope (equities + forex pool accounts)
- Mark-to-market runs periodically, updating position values
- Equity is calculated from cash + positions value
- Peak equity is persisted to the database (not in-memory)
- The risk engine gets real exposure, drawdown, and cash values
- The strategy runner queries real positions for exit evaluation
- The safety monitor queries real positions for price-based exits
- The paper trading service's process_fill stub is replaced with real logic
- The cash manager reads real cash balances

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/portfolio_module_spec.md — PRIMARY SPEC, sections 1-5, 8
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, inter-module interfaces
6. /studio/SPECS/paper_trading_module_spec.md — fill model fields for processing
7. /studio/SPECS/risk_engine_module_spec.md — what risk needs from portfolio (section 4 checks)
8. Review TASK-012a, TASK-011, TASK-009 BUILDER_OUTPUT.md — understand current stubs

## Constraints

- Do NOT implement portfolio snapshots (TASK-013b)
- Do NOT implement the realized PnL ledger as a separate table (TASK-013b)
  (track realized_pnl on the Position model for now)
- Do NOT implement dividend processing (TASK-013b)
- Do NOT implement stock split adjustment (TASK-013b)
- Do NOT implement options expiration handling (TASK-013b)
- Do NOT implement performance metrics calculations (TASK-013b)
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions (envelope, pagination, camelCase)
- All financial values use Decimal
- All timestamps are timezone-aware UTC

---

## Deliverables

### 1. Portfolio Models (backend/app/portfolio/models.py)

All models inherit from BaseModel.

**Position:**
```
Position:
  - id: UUID (from BaseModel)
  - strategy_id: UUID (FK → strategies.id)
  - symbol: str
  - market: str (equities | forex)
  - side: str (long | short)
  - qty: Numeric
  - avg_entry_price: Numeric
  - cost_basis: Numeric (total cost including fees at entry)
  - current_price: Numeric
  - market_value: Numeric (qty * current_price * contract_multiplier)
  - unrealized_pnl: Numeric
  - unrealized_pnl_percent: Numeric
  - realized_pnl: Numeric (accumulated from partial closes on this position)
  - total_fees: Numeric
  - total_dividends_received: Numeric (default 0)
  - total_return: Numeric (unrealized + realized + dividends)
  - total_return_percent: Numeric
  - status: str (open | closed)
  - opened_at: datetime
  - closed_at: datetime, nullable
  - close_reason: str, nullable (stop_loss | take_profit | trailing_stop |
                                  max_hold | condition | manual | safety |
                                  system | expiration)
  - highest_price_since_entry: Numeric
  - lowest_price_since_entry: Numeric
  - bars_held: int (default 0)
  - broker_account_id: str, nullable (for forex pool tracking)
  - underlying_symbol: str, nullable (for options)
  - contract_type: str, nullable (call | put)
  - strike_price: Numeric, nullable
  - expiration_date: date, nullable
  - contract_multiplier: int (default 1, options = 100)
  - user_id: UUID (FK → users.id, for row-level security)
  - created_at, updated_at (from BaseModel)

Indexes:
  INDEX (strategy_id, status)
  INDEX (symbol, status)
  INDEX (status)
  INDEX (strategy_id, symbol, status)
  INDEX (user_id, status)
  INDEX (broker_account_id, status) — partial, WHERE broker_account_id IS NOT NULL
  INDEX (expiration_date) — partial, WHERE expiration_date IS NOT NULL
```

**CashBalance:**
```
CashBalance:
  - id: UUID (from BaseModel)
  - account_scope: str
      "equities" — single equity account
      "forex_pool_1" through "forex_pool_N" — per virtual forex account
  - balance: Numeric
  - user_id: UUID (FK → users.id)
  - created_at, updated_at (from BaseModel)

Indexes:
  UNIQUE (account_scope, user_id)
```

**PortfolioMeta:**
```
PortfolioMeta:
  - id: UUID (from BaseModel)
  - key: str
  - value: str
  - user_id: UUID (FK → users.id)
  - created_at, updated_at (from BaseModel)

Indexes:
  UNIQUE (key, user_id)
```

PortfolioMeta stores:
- "peak_equity": "103500.00"
- "peak_equity_at": "2025-03-08T14:30:00Z"
- "initial_capital": "100000.00"
- "inception_date": "2025-03-01"

### 2. Portfolio Schemas (backend/app/portfolio/schemas.py)

Use camelCase aliases (alias_generator=to_camel, populate_by_name=True).

**Response schemas:**
```python
class PositionResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    symbol: str
    market: str
    side: str
    qty: Decimal
    avg_entry_price: Decimal
    cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    realized_pnl: Decimal
    total_fees: Decimal
    total_dividends_received: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    status: str
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None
    highest_price_since_entry: Decimal
    lowest_price_since_entry: Decimal
    bars_held: int
    broker_account_id: str | None
    contract_multiplier: int
    created_at: datetime

class PortfolioSummaryResponse(BaseModel):
    equity: Decimal
    cash: Decimal
    positions_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl_total: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    drawdown_percent: Decimal
    peak_equity: Decimal
    open_positions_count: int

class CashBalanceResponse(BaseModel):
    account_scope: str
    balance: Decimal

class EquityBreakdownResponse(BaseModel):
    total_equity: Decimal
    total_cash: Decimal
    total_positions_value: Decimal
    equities_cash: Decimal
    equities_positions_value: Decimal
    forex_cash: Decimal
    forex_positions_value: Decimal
```

**Query schemas:**
```python
class PositionQueryParams(BaseModel):
    strategy_id: UUID | None = None
    symbol: str | None = None
    status: str | None = None
    market: str | None = None
    page: int = 1
    page_size: int = 20
```

### 3. Portfolio Errors (backend/app/portfolio/errors.py)

```python
class PositionNotFoundError(DomainError):
    # PORTFOLIO_POSITION_NOT_FOUND, 404

class InsufficientCashError(DomainError):
    # PORTFOLIO_INSUFFICIENT_CASH, 400

class InvalidFillError(DomainError):
    # PORTFOLIO_INVALID_FILL, 400

class PortfolioStateError(DomainError):
    # PORTFOLIO_STATE_ERROR, 500
```

Register in common/errors.py.

### 4. Portfolio Config (backend/app/portfolio/config.py)

```python
class PortfolioConfig:
    def __init__(self):
        s = get_settings()
        self.mark_to_market_interval = s.portfolio_mark_to_market_interval_sec
        self.snapshot_interval = s.portfolio_snapshot_interval_sec
        self.risk_free_rate = Decimal(str(s.portfolio_risk_free_rate))
        self.initial_cash = Decimal(str(s.paper_trading_initial_cash))
        self.forex_pool_size = s.paper_trading_forex_account_pool_size
        self.forex_capital_per_account = Decimal(str(s.paper_trading_forex_capital_per_account))
```

### 5. Portfolio Repository (backend/app/portfolio/repository.py)

```python
class PositionRepository:
    async def create(self, db, position: Position) -> Position
    async def get_by_id(self, db, position_id: UUID) -> Position | None
    async def get_open_by_strategy_symbol(self, db, strategy_id: UUID,
                                          symbol: str) -> Position | None
    async def get_open_by_strategy(self, db, strategy_id: UUID) -> list[Position]
    async def get_all_open(self, db, user_id: UUID) -> list[Position]
    async def get_filtered(self, db, user_id: UUID, strategy_id=None,
                           symbol=None, status=None, market=None,
                           page=1, page_size=20) -> tuple[list, int]
    async def get_open_positions_count(self, db, strategy_id: UUID) -> int
    async def get_open_by_symbol(self, db, symbol: str) -> list[Position]:
        """All open positions for a symbol across ALL strategies (for exposure calc)."""
    async def update(self, db, position: Position) -> Position
    async def get_all_open_for_user(self, db, user_id: UUID) -> list[Position]:
        """All open positions for a user (for portfolio-level calculations)."""

class CashBalanceRepository:
    async def get_by_scope(self, db, account_scope: str,
                           user_id: UUID) -> CashBalance | None
    async def get_all(self, db, user_id: UUID) -> list[CashBalance]
    async def create(self, db, cash: CashBalance) -> CashBalance
    async def update_balance(self, db, account_scope: str,
                             user_id: UUID, delta: Decimal) -> CashBalance:
        """Atomically adjust balance by delta (positive=credit, negative=debit)."""
    async def get_total_cash(self, db, user_id: UUID) -> Decimal

class PortfolioMetaRepository:
    async def get(self, db, key: str, user_id: UUID) -> str | None
    async def set(self, db, key: str, value: str, user_id: UUID) -> None
    async def get_all(self, db, user_id: UUID) -> dict[str, str]
```

### 6. Fill Processor (backend/app/portfolio/fill_processor.py)

The core logic that turns fills into position updates.

```python
class FillProcessor:
    """Processes fills from the paper trading engine into position updates.
    
    This is the entry point that paper_trading_service.process_fill() calls.
    Handles all four scenarios: entry, scale-in, scale-out, full exit.
    """
    
    async def process_fill(self, db: AsyncSession, fill: 'PaperFill',
                           order: 'PaperOrder', user_id: UUID) -> Position:
        """Process a fill and update/create position.
        
        Steps:
        1. Look up existing open position for strategy + symbol
        2. Determine scenario (entry, scale-in, scale-out, full exit)
        3. Execute the appropriate update
        4. Adjust cash balance
        5. Return the updated/created position
        
        This runs within the same transaction as the fill creation
        (atomic — both succeed or both fail).
        """
    
    async def _process_entry(self, db, fill, order, user_id) -> Position:
        """No existing position. Create new position.
        
        Position fields:
          strategy_id, symbol, market = from order
          side = "long" if buy else "short"
          qty = fill.qty
          avg_entry_price = fill.price
          cost_basis = fill.net_value
          current_price = fill.price
          market_value = fill.qty * fill.price * order.contract_multiplier
          unrealized_pnl = 0
          realized_pnl = 0
          total_fees = fill.fee
          status = "open"
          opened_at = fill.filled_at
          highest/lowest_price_since_entry = fill.price
          bars_held = 0
          broker_account_id = fill.broker_account_id
          contract_multiplier, underlying_symbol, etc. = from order
          user_id = user_id
        
        Cash: debit for buys, credit for sells (opening short)
        """
    
    async def _process_scale_in(self, db, position, fill, order) -> Position:
        """Existing position, same direction. Increase size.
        
        new_total_qty = position.qty + fill.qty
        avg_entry_price = weighted average:
          ((position.qty * position.avg_entry_price) + (fill.qty * fill.price))
          / new_total_qty
        cost_basis += fill.net_value
        total_fees += fill.fee
        
        Cash: debit for buys, credit for sells
        """
    
    async def _process_scale_out(self, db, position, fill, order) -> Position:
        """Existing position, partial close. Reduce size.
        
        Calculate realized PnL on closed portion:
          if long: gross_pnl = (fill.price - avg_entry_price) * fill.qty * multiplier
          if short: gross_pnl = (avg_entry_price - fill.price) * fill.qty * multiplier
          net_pnl = gross_pnl - fill.fee
        
        Update position:
          qty -= fill.qty
          realized_pnl += net_pnl
          cost_basis adjusted proportionally: cost_basis * (remaining / original)
          total_fees += fill.fee
        
        Cash: credit for sells (closing long), debit for buys (closing short)
        """
    
    async def _process_full_exit(self, db, position, fill, order) -> Position:
        """Close entire position.
        
        Calculate realized PnL on full position:
          same formulas as scale-out but for full qty
        
        Update position:
          qty = 0
          realized_pnl += net_pnl
          total_fees += fill.fee
          status = "closed"
          closed_at = fill.filled_at
          close_reason = from signal's exit_reason (via order)
          total_return = realized_pnl + total_dividends_received
        
        Cash: credit for sells, debit for buys (closing short)
        
        Release forex account allocation if broker_account_id is set:
          (STUB for now — TASK-012b handles forex pool release)
        """
    
    async def _adjust_cash(self, db: AsyncSession, user_id: UUID,
                           fill: 'PaperFill', order: 'PaperOrder') -> None:
        """Adjust cash balance based on fill.
        
        Determine account_scope:
          If forex with broker_account_id: use "forex_pool_{N}"
          Else: use "equities"
        
        For buys (opening long / closing short): cash -= fill.net_value
        For sells (closing long / opening short): cash += fill.net_value
        """
    
    def _determine_scenario(self, position: Position | None,
                            order: 'PaperOrder') -> str:
        """Determine which fill scenario applies.
        
        No position → "entry"
        Position exists, same direction → "scale_in"
        Position exists, opposite direction, fill.qty < position.qty → "scale_out"
        Position exists, opposite direction, fill.qty >= position.qty → "full_exit"
        """
```

### 7. Mark-to-Market (backend/app/portfolio/mark_to_market.py)

```python
class MarkToMarket:
    """Periodically updates open positions with current prices.
    
    Runs every PORTFOLIO_MARK_TO_MARKET_INTERVAL_SEC (default: 60).
    Only during market hours for each position's market.
    """
    
    def __init__(self, config: PortfolioConfig):
        self._config = config
        self._running = False
    
    async def start(self) -> None:
        """Start the mark-to-market loop as a background task."""
    
    async def stop(self) -> None:
        """Stop the loop."""
    
    async def _run_loop(self) -> None:
        """Periodically run mark-to-market."""
    
    async def run_cycle(self, db: AsyncSession) -> dict:
        """Run one mark-to-market cycle.
        
        For each open position:
        1. Skip if market is closed for this position's market
        2. Get current price from MarketDataService.get_latest_close()
        3. Update position:
           - current_price
           - market_value = qty * current_price * contract_multiplier
           - unrealized_pnl:
             long: (current_price - avg_entry_price) * qty * multiplier
             short: (avg_entry_price - current_price) * qty * multiplier
           - unrealized_pnl_percent:
             long: (current_price - avg_entry_price) / avg_entry_price * 100
             short: (avg_entry_price - current_price) / avg_entry_price * 100
           - total_return = unrealized_pnl + realized_pnl + total_dividends_received
           - total_return_percent = total_return / cost_basis * 100 (if cost_basis > 0)
           - highest_price_since_entry = max(highest, current_price)
           - lowest_price_since_entry = min(lowest, current_price)
        4. After all positions updated, update peak equity
        
        Returns: {"positions_updated": N, "skipped_closed_market": N}
        """
    
    async def _update_peak_equity(self, db: AsyncSession, user_id: UUID) -> None:
        """Update peak equity if current equity is a new high.
        
        current_equity = total_cash + sum(open position market_values)
        peak = max(current_peak, current_equity)
        Store in PortfolioMeta as "peak_equity" and "peak_equity_at"
        """
    
    def _is_market_open(self, market: str) -> bool:
        """Check if market is open.
        
        Equities: 9:30-16:00 ET weekdays (approximate with UTC)
        Forex: Sunday 22:00 UTC through Friday 22:00 UTC
        """
```

### 8. Portfolio Service (backend/app/portfolio/service.py)

The inter-module interface. Other modules call these methods.

```python
class PortfolioService:
    """Portfolio management and inter-module interface.
    
    Called by:
    - Paper trading: process_fill()
    - Risk engine: get_equity(), get_cash(), get_exposure(), get_drawdown()
    - Strategy runner: get_positions()
    - Safety monitor: get_orphaned_positions()
    - Dashboard: summary, positions, cash
    """
    
    def __init__(self, config: PortfolioConfig,
                 fill_processor: FillProcessor):
        self._config = config
        self._fill_processor = fill_processor
        self._position_repo = PositionRepository()
        self._cash_repo = CashBalanceRepository()
        self._meta_repo = PortfolioMetaRepository()
    
    # --- Fill Processing (called by paper trading) ---
    
    async def process_fill(self, db: AsyncSession, fill: 'PaperFill',
                           order: 'PaperOrder', user_id: UUID) -> Position:
        """Process a fill into a position update. Delegates to FillProcessor."""
    
    # --- Position Queries (called by strategy runner, safety monitor, risk) ---
    
    async def get_open_positions(self, db, strategy_id: UUID) -> list[Position]:
        """Get open positions for a strategy. Used by runner for exit evaluation."""
    
    async def get_open_position_for_symbol(self, db, strategy_id: UUID,
                                           symbol: str) -> Position | None:
        """Get open position for a specific strategy+symbol. Used by runner."""
    
    async def get_all_open_positions(self, db, user_id: UUID) -> list[Position]:
        """Get all open positions for a user. Used by mark-to-market."""
    
    async def get_positions_count(self, db, strategy_id: UUID) -> int:
        """Count open positions for a strategy. Used by risk position limit check."""
    
    async def get_orphaned_positions(self, db) -> list[tuple[Position, 'Strategy']]:
        """Get positions whose strategy is paused/disabled.
        Used by safety monitor.
        
        JOIN positions ON strategies WHERE
        positions.status = 'open' AND
        strategies.status IN ('paused', 'disabled')
        """
    
    # --- Cash (called by paper trading cash manager, risk engine) ---
    
    async def get_cash(self, db, user_id: UUID,
                       account_scope: str = "equities") -> Decimal:
        """Get cash balance for an account scope."""
    
    async def get_total_cash(self, db, user_id: UUID) -> Decimal:
        """Get total cash across all accounts."""
    
    async def get_all_cash_balances(self, db, user_id: UUID) -> list[CashBalance]:
        """Get all cash balances."""
    
    # --- Equity and Exposure (called by risk engine) ---
    
    async def get_equity(self, db, user_id: UUID) -> Decimal:
        """total_cash + sum(open position market_values)"""
    
    async def get_peak_equity(self, db, user_id: UUID) -> Decimal:
        """Read from PortfolioMeta."""
    
    async def get_drawdown(self, db, user_id: UUID) -> dict:
        """Calculate current drawdown.
        
        Returns: {
            "peak_equity": Decimal,
            "current_equity": Decimal,
            "drawdown_percent": Decimal
        }
        """
    
    async def get_symbol_exposure(self, db, symbol: str) -> Decimal:
        """Total market value of all open positions in a symbol.
        Used by risk per-symbol exposure check."""
    
    async def get_strategy_exposure(self, db, strategy_id: UUID) -> Decimal:
        """Total market value of all open positions for a strategy.
        Used by risk per-strategy exposure check."""
    
    async def get_total_exposure(self, db, user_id: UUID) -> Decimal:
        """Total market value of all open positions.
        Used by risk portfolio exposure check."""
    
    async def get_daily_realized_loss(self, db, user_id: UUID) -> Decimal:
        """Sum of realized losses today (where realized_pnl < 0).
        Used by risk daily loss check.
        
        Queries positions closed today where realized_pnl < 0.
        (Will be more accurate when TASK-013b adds the PnL ledger.)
        """
    
    # --- Portfolio Summary (called by dashboard API) ---
    
    async def get_summary(self, db, user_id: UUID) -> dict:
        """Full portfolio summary.
        
        Returns: {
            equity, cash, positions_value, unrealized_pnl,
            realized_pnl_total, total_return, total_return_percent,
            drawdown_percent, peak_equity, open_positions_count
        }
        """
    
    async def get_equity_breakdown(self, db, user_id: UUID) -> dict:
        """Equity breakdown by market.
        
        Returns: {
            total_equity, total_cash, total_positions_value,
            equities_cash, equities_positions_value,
            forex_cash, forex_positions_value
        }
        """
    
    # --- Read Operations ---
    
    async def get_position(self, db, position_id: UUID,
                           user_id: UUID) -> Position:
        """Get position by ID. Verify ownership."""
    
    async def list_positions(self, db, user_id: UUID,
                             **filters) -> tuple[list, int]:
        """List positions with filters and pagination."""
    
    async def get_open_positions_for_user(self, db,
                                          user_id: UUID) -> list[Position]:
        """All open positions for the user."""
    
    async def get_closed_positions(self, db, user_id: UUID,
                                   date_start=None, date_end=None,
                                   page=1, page_size=20) -> tuple[list, int]:
        """Closed positions with date range filter."""
    
    # --- Cash Initialization ---
    
    async def initialize_cash(self, db, user_id: UUID) -> None:
        """Create initial cash balances if they don't exist.
        
        Creates:
          "equities" → PAPER_TRADING_INITIAL_CASH
          "forex_pool_1" through "forex_pool_N" → FOREX_CAPITAL_PER_ACCOUNT each
        
        Called during startup or when a user first accesses portfolio.
        """
```

### 9. Portfolio Router (backend/app/portfolio/router.py)

Replace the empty stub.

```
# Positions
GET  /api/v1/portfolio/positions              → list positions (paginated, filtered)
GET  /api/v1/portfolio/positions/open         → all open positions
GET  /api/v1/portfolio/positions/closed       → closed positions (date range)
GET  /api/v1/portfolio/positions/:id          → position detail

# Portfolio State
GET  /api/v1/portfolio/summary               → portfolio summary
GET  /api/v1/portfolio/equity                 → equity breakdown by market
GET  /api/v1/portfolio/cash                   → cash balances per account scope
```

All endpoints require auth (get_current_user).
All enforce user ownership.
All responses use standard {"data": ...} envelope with camelCase.
All model_dump() calls use by_alias=True.

### 10. Wire into Paper Trading — Replace process_fill Stub

Update backend/app/paper_trading/service.py:

Replace the TODO TASK-013 stub in process_signal() with:

```python
# After creating the PaperFill, call portfolio:
from app.portfolio.startup import get_portfolio_service
portfolio_service = get_portfolio_service()
if portfolio_service:
    position = await portfolio_service.process_fill(db, fill, order, user_id)
```

The user_id comes from the strategy: signal → strategy → user_id.

### 11. Wire into Paper Trading — Replace Cash Manager Stub

Update backend/app/paper_trading/cash_manager.py:

Replace the stub that returns (True, initial_cash) with:

```python
from app.portfolio.startup import get_portfolio_service
portfolio_service = get_portfolio_service()
if portfolio_service:
    available = await portfolio_service.get_cash(db, user_id, account_scope)
    return (available >= required_cash, available)
else:
    # Fallback if portfolio not initialized
    return (True, self._config.initial_cash)
```

### 12. Wire into Risk Engine — Replace Portfolio Stubs

Update the risk engine's context building (backend/app/risk/service.py _build_context):

Replace the stubbed values with real calls:

```python
from app.portfolio.startup import get_portfolio_service
portfolio_service = get_portfolio_service()

# Replace stubbed portfolio_equity (was 100000)
context.portfolio_equity = await portfolio_service.get_equity(db, user_id)

# Replace stubbed portfolio_cash
context.portfolio_cash = await portfolio_service.get_total_cash(db, user_id)

# Replace stubbed peak_equity
context.peak_equity = await portfolio_service.get_peak_equity(db, user_id)

# Replace stubbed drawdown (was 0)
dd = await portfolio_service.get_drawdown(db, user_id)
context.current_drawdown_percent = dd["drawdown_percent"]

# Replace stubbed daily_realized_loss (was 0)
context.daily_realized_loss = await portfolio_service.get_daily_realized_loss(db, user_id)

# Replace stubbed exposure (was all zeros)
context.symbol_exposure = {}  # Built from real position data
for symbol in relevant_symbols:
    context.symbol_exposure[symbol] = await portfolio_service.get_symbol_exposure(db, symbol)
context.strategy_exposure = {str(strategy.id): await portfolio_service.get_strategy_exposure(db, strategy.id)}
context.total_exposure = await portfolio_service.get_total_exposure(db, user_id)

# Replace stubbed positions count
context.open_positions_count = await portfolio_service.get_positions_count(db, strategy.id)
context.strategy_positions_count = context.open_positions_count
```

Also update the drawdown monitor (backend/app/risk/monitoring/drawdown.py)
and exposure calculator (backend/app/risk/monitoring/exposure.py) to use
real portfolio data.

### 13. Wire into Strategy Runner — Replace Position Stub

Update backend/app/strategies/runner.py:

In evaluate_strategy(), replace the TASK-013 TODO that returns empty
positions with:

```python
from app.portfolio.startup import get_portfolio_service
portfolio_service = get_portfolio_service()
if portfolio_service:
    positions = await portfolio_service.get_open_positions(db, strategy.id)
else:
    positions = []
```

This makes the runner's exit evaluation actually work — it now knows
which symbols have open positions and can evaluate exit conditions.

### 14. Wire into Safety Monitor — Replace Position Stub

Update backend/app/strategies/safety_monitor.py:

Replace the TASK-013 TODO that returns empty positions with:

```python
from app.portfolio.startup import get_portfolio_service
portfolio_service = get_portfolio_service()
if portfolio_service:
    orphaned = await portfolio_service.get_orphaned_positions(db)
else:
    orphaned = []
```

### 15. Portfolio Startup (backend/app/portfolio/startup.py)

```python
_portfolio_service: PortfolioService | None = None
_mark_to_market: MarkToMarket | None = None

async def start_portfolio(db: AsyncSession, user_id: UUID) -> None:
    """Initialize portfolio module.
    
    1. Load config
    2. Create FillProcessor
    3. Create PortfolioService
    4. Initialize cash balances if they don't exist
    5. Create and start MarkToMarket
    """

async def stop_portfolio() -> None:
    """Stop mark-to-market."""

def get_portfolio_service() -> PortfolioService | None:
    return _portfolio_service
```

### 16. Register in main.py

Add portfolio startup/shutdown to lifespan, after paper trading:

```python
await start_market_data(db)
await start_strategies()
await start_signals()
await start_risk()
await start_paper_trading()
await start_portfolio(db, admin_user_id)  # needs a user context
# ...
await stop_portfolio()
await stop_paper_trading()
# etc.
```

Note: portfolio initialization needs a user_id for cash balance seeding.
For MVP, use the admin user's ID. This can be refined later for
multi-user support.

### 17. Alembic Migration

Create migration for positions, cash_balances, and portfolio_meta tables:

```bash
cd backend
alembic revision --autogenerate -m "create_portfolio_tables"
alembic upgrade head
```

Update migrations/env.py to import portfolio models.

---

## Acceptance Criteria

### Models and Migration
1. Position model exists with all fields, all financial fields use Numeric
2. Position has user_id FK for row-level security
3. CashBalance model exists with unique constraint on (account_scope, user_id)
4. PortfolioMeta model exists with unique constraint on (key, user_id)
5. Alembic migration creates all three tables and applies cleanly

### Fill Processing
6. Entry fill creates new position with correct field values
7. Scale-in fill updates qty and recalculates weighted average entry price
8. Scale-out fill reduces qty and calculates realized PnL on closed portion
9. Full exit fill closes position with realized PnL and close_reason
10. Cash is debited on buy fills and credited on sell fills
11. Cash adjustment uses correct account scope (equities vs forex pool)
12. Fill processing is atomic with position update (same transaction)
13. Cost basis adjustment on scale-out is proportional

### Mark-to-Market
14. Mark-to-market runs periodically as a background task
15. Position current_price, market_value, unrealized_pnl updated correctly
16. Unrealized PnL formula: long = (current - entry) * qty * multiplier
17. Unrealized PnL formula: short = (entry - current) * qty * multiplier
18. highest/lowest_price_since_entry tracked correctly
19. total_return includes unrealized + realized + dividends
20. Mark-to-market skips positions when market is closed
21. Peak equity updated after each cycle

### Cash and Equity
22. Initial cash balances created on startup (equities + forex pool accounts)
23. Equity = total_cash + sum(open positions market_value)
24. Peak equity persisted to database via PortfolioMeta (not in-memory)
25. Drawdown calculated from peak_equity and current_equity

### Portfolio Service Interface
26. get_equity() returns correct value
27. get_cash() returns balance for specific account scope
28. get_total_cash() returns sum across all accounts
29. get_symbol_exposure() returns total position value for a symbol
30. get_strategy_exposure() returns total position value for a strategy
31. get_total_exposure() returns total value of all open positions
32. get_daily_realized_loss() returns sum of negative realized PnL from today's closes
33. get_positions_count() returns count of open positions for a strategy
34. get_orphaned_positions() returns positions with paused/disabled strategies

### Wiring — Paper Trading
35. paper_trading service.process_signal() calls portfolio.process_fill() instead of stub
36. paper_trading cash_manager reads real cash balances instead of stub

### Wiring — Risk Engine
37. Risk context uses real equity from portfolio (not stubbed 100000)
38. Risk context uses real exposure values from portfolio (not stubbed zeros)
39. Risk context uses real drawdown from portfolio (not stubbed zero)
40. Risk context uses real daily loss from portfolio (not stubbed zero)
41. Risk context uses real positions count from portfolio

### Wiring — Strategy Runner
42. Strategy runner queries real positions for exit evaluation
43. Runner exit conditions evaluate against actual open positions

### Wiring — Safety Monitor
44. Safety monitor queries real orphaned positions
45. Safety monitor now processes actual positions (not empty list)

### API
46. GET /portfolio/positions returns filtered, paginated position list
47. GET /portfolio/positions/open returns all open positions
48. GET /portfolio/positions/closed returns closed positions with date filter
49. GET /portfolio/positions/:id returns position detail
50. GET /portfolio/summary returns portfolio summary with real values
51. GET /portfolio/equity returns equity breakdown by market
52. GET /portfolio/cash returns cash balances per account scope
53. All endpoints enforce user ownership
54. All responses use standard {"data": ...} envelope with camelCase

### General
55. Portfolio error classes exist and registered in common/errors.py
56. PortfolioConfig loads settings with Decimal conversions
57. Startup/shutdown registered in main.py lifespan
58. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-013a-portfolio-core/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
