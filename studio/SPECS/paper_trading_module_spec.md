# PAPER_TRADING_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the paper trading module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The paper trading module owns:

- Order creation from risk-approved signals
- Fill simulation (internal simulation mode)
- Broker order routing (broker paper trading mode)
- Executor abstraction (simulated, broker paper, future live)
- Forex account pool management and allocation
- Shadow tracking for contention-blocked signals
- Order and fill lifecycle management
- Cash availability checks
- Fee and slippage modeling

The paper trading module does NOT own:

- Signal creation (owned by strategy/signals module)
- Risk evaluation (owned by risk module, upstream)
- Position persistence and PnL calculation (owned by portfolio module)
- Market data (reads from market data module)

---

## 1. Design Philosophy

### Honest Simulation

Paper trading must simulate the same constraints as live trading.
If a condition would block a trade in live (account contention, netting),
it must block in paper. Otherwise paper results are fiction.

### Dual-Mode Execution

The system supports two execution modes:

```
ExecutionMode:
  - "simulation"  → internal fill simulation
                     (for backtesting, offline testing, forex account pool)
  - "paper"       → broker paper trading API
                     (for equities via Alpaca, realistic fills)
  - "live"        → broker live API (future, not in MVP)
```

Equities default to broker paper trading (Alpaca paper API).
Forex defaults to internal simulation with account pool constraints.

### Why Forex Uses Internal Simulation

US forex brokers enforce FIFO netting — one net direction per pair per
account. Multiple strategies trading the same pair require multiple
accounts. The internal simulation models this constraint through a
virtual account pool, enforcing the same rules paper and live would face.

---

## 2. Executor Abstraction

### Interface

Every executor implements:

```
submit_order(order: PaperOrder) → OrderResult
cancel_order(order_id: UUID) → CancelResult
get_order_status(order_id: UUID) → OrderStatus
```

The strategy runner, risk engine, and portfolio module don't know or care
which executor is active. They see the same PaperOrder and PaperFill
records regardless of execution mode.

### Executor Routing

```
if market == "equities":
    executor = AlpacaPaperExecutor    (broker paper API, single account)
elif market == "forex":
    executor = ForexPoolExecutor      (internal simulation, account pool)
```

### Folder Structure

```
backend/app/paper_trading/
    __init__.py
    service.py              ← order creation, lifecycle management
    models.py               ← SQLAlchemy models
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← paper trading configuration
    cash_manager.py         ← cash availability checks
    executors/
        __init__.py
        base.py             ← abstract executor interface
        simulated.py        ← internal fill simulation (slippage/fee model)
        alpaca_paper.py     ← Alpaca paper trading API
        oanda_practice.py   ← OANDA practice API (future, for non-US or single-strategy)
    forex_pool/
        __init__.py
        pool_manager.py     ← account pool allocation and release
        allocation.py       ← allocation tracking and queries
        reconciliation.py   ← internal vs broker state comparison
    shadow/
        __init__.py
        tracker.py          ← shadow fill and position management
        evaluator.py        ← shadow position exit condition evaluation
    fill_simulation/
        __init__.py
        engine.py           ← fill price calculation
        slippage.py         ← slippage models
        fees.py             ← fee models
```

---

## 3. Order and Fill Data Models

### PaperOrder

```
PaperOrder:
  - id: UUID
  - signal_id: UUID (FK → Signal)
  - risk_decision_id: UUID (FK → RiskDecision)
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - market: str (equities | forex)
  - side: str (buy | sell)
  - order_type: str (market | limit)
  - signal_type: str (entry | exit | scale_in | scale_out)
  - requested_qty: Decimal
  - requested_price: Decimal, nullable (for limit orders)
  - filled_qty: Decimal (default 0)
  - filled_avg_price: Decimal, nullable
  - status: str (pending | accepted | filled | partially_filled |
                  canceled | rejected)
  - rejection_reason: str, nullable
  - execution_mode: str (simulation | paper | live)
  - broker_order_id: str, nullable (ID from broker API, if applicable)
  - broker_account_id: str, nullable (which broker/virtual account)
  - underlying_symbol: str, nullable (for options: the underlying)
  - contract_type: str, nullable (for options: call | put)
  - strike_price: Decimal, nullable (for options)
  - expiration_date: date, nullable (for options)
  - contract_multiplier: int (default 1, options use 100)
  - submitted_at: datetime
  - accepted_at: datetime, nullable
  - filled_at: datetime, nullable
  - created_at: datetime
  - updated_at: datetime

Indexes:
  INDEX (signal_id) UNIQUE
  INDEX (strategy_id, created_at)
  INDEX (symbol, status)
  INDEX (status)
  INDEX (broker_order_id) WHERE broker_order_id IS NOT NULL
```

### PaperFill

```
PaperFill:
  - id: UUID
  - order_id: UUID (FK → PaperOrder)
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - side: str (buy | sell)
  - qty: Decimal
  - reference_price: Decimal (market price before slippage)
  - price: Decimal (execution price after slippage)
  - gross_value: Decimal (qty * price, adjusted for contract_multiplier)
  - fee: Decimal
  - slippage_bps: Decimal (basis points of slippage applied)
  - slippage_amount: Decimal (dollar amount of slippage)
  - net_value: Decimal (gross_value ± fee, accounting for side)
  - broker_fill_id: str, nullable (ID from broker, if applicable)
  - broker_account_id: str, nullable
  - filled_at: datetime
  - created_at: datetime

Indexes:
  INDEX (order_id)
  INDEX (strategy_id, filled_at)
  INDEX (symbol, filled_at)
```

### Field Notes

- reference_price vs price: reference is the market price, price is after
  slippage. The difference is visible and auditable.
- gross_value accounts for contract_multiplier (options: qty * 100 * price)
- net_value includes fees. For buys: gross + fee. For sells: gross - fee.
- broker_order_id and broker_fill_id are null for internal simulation,
  populated when using broker APIs.

---

## 4. Order Lifecycle

### States

```
pending → accepted → filled                (happy path)
                  → partially_filled → filled  (future, not MVP)
       → rejected                          (precondition failure)
       → canceled                          (user or system cancel)
```

MVP required paths:
- pending → accepted → filled
- pending → rejected

Partial fills are architecturally supported (filled_qty vs requested_qty,
partially_filled status) but MVP always fills the full quantity in one fill.

---

## 5. What Triggers Order Creation

The paper trading engine watches for signals with status = "risk_approved"
or "risk_modified".

```
1. Read the signal and risk decision
2. If risk_modified: use modified values from risk_decision.modifications_json
3. If risk_approved: use original signal values
4. For forex: check account pool availability (see section 8)
5. Check cash availability
6. Create PaperOrder (status: pending)
7. Route to appropriate executor
8. Executor processes the order:
   - Simulation: calculate fill immediately
   - Broker paper: submit to broker API, await response
9. Create PaperFill with execution details
10. Update PaperOrder (status: filled)
11. Notify portfolio module: portfolio_service.process_fill(fill)
12. Log everything
```

For internal simulation, steps 6-11 happen near-instantly (under a second).
For broker paper trading, there's network latency for the broker API call.

---

## 6. Fill Simulation Logic (Internal Simulation Mode)

Used for: forex paper trading, backtesting, offline testing.

### Step 1 — Determine Reference Price

For market orders:

```python
reference_price = market_data_service.get_latest_close(symbol, timeframe="1m")
```

If no 1m bar available, fall back to the timeframe that triggered the
strategy evaluation.

For limit orders (future): fill only occurs if market price reaches
the limit price. Deferred to post-MVP.

### Step 2 — Apply Slippage

Slippage simulates the gap between observed price and execution price.
Always works against you.

```
For buys:  execution_price = reference_price * (1 + slippage_bps / 10000)
For sells: execution_price = reference_price * (1 - slippage_bps / 10000)
```

Slippage values from configuration, per market:

```
PAPER_TRADING_SLIPPAGE_BPS_EQUITIES=5     (0.05%)
PAPER_TRADING_SLIPPAGE_BPS_FOREX=2        (0.02%)
PAPER_TRADING_SLIPPAGE_BPS_OPTIONS=10     (0.10%)
```

### Step 3 — Calculate Fee

```
Fee models:
  per_trade:  fee = flat amount per order
  per_share:  fee = qty * fee_per_share
  percent:    fee = gross_value * fee_percent / 100
  spread_bps: fee = gross_value * spread_bps / 10000 (forex spread cost)
```

Per-market defaults:

```
Equities (Alpaca): commission-free
  PAPER_TRADING_FEE_PER_TRADE_EQUITIES=0.00

Forex (OANDA): cost is in the spread
  PAPER_TRADING_FEE_SPREAD_BPS_FOREX=15

Options: commission-free on Alpaca
  PAPER_TRADING_FEE_PER_TRADE_OPTIONS=0.00
```

### Step 4 — Record Fill

```
PaperFill:
  qty = order.requested_qty
  reference_price = latest close
  price = reference_price adjusted by slippage
  gross_value = qty * price * contract_multiplier
  fee = calculated fee
  slippage_amount = abs(price - reference_price) * qty * contract_multiplier
  slippage_bps = configured slippage
  net_value = gross_value + fee (buys) or gross_value - fee (sells)
  filled_at = bar timestamp that triggered the strategy evaluation
```

### Step 5 — Update Order

```
order.status = "filled"
order.filled_qty = fill.qty
order.filled_avg_price = fill.price
order.filled_at = fill.filled_at
```

### Step 6 — Notify Portfolio

```
portfolio_service.process_fill(fill)
```

Synchronous call within the same transaction. Fill and position update
are atomic — both succeed or both fail.

### Execution Timestamp

For strategy-triggered fills:
  filled_at = timestamp of the bar that triggered evaluation
  (not datetime.now() — this matters for backtesting consistency)

For manual closes (user clicks close):
  filled_at = current time (user is acting in real-time)

---

## 7. Broker Paper Trading (Equities via Alpaca)

### Flow

```
1. Paper trading engine creates internal PaperOrder (status: pending)
2. Call Alpaca paper API: POST /v2/orders
   {
     "symbol": "AAPL",
     "qty": "100",
     "side": "buy",
     "type": "market",
     "time_in_force": "day"
   }
3. Alpaca returns order confirmation with broker_order_id
4. Update PaperOrder: status=accepted, broker_order_id stored
5. Receive fill notification via WebSocket or poll REST API
6. On fill: create PaperFill with broker-reported price, qty, timestamp
7. Update PaperOrder: status=filled, filled_avg_price, filled_at
8. Notify portfolio module
```

### Alpaca WebSocket for Order Updates

Alpaca streams order status updates via WebSocket (trade_updates channel).
The paper trading engine subscribes to this alongside the market data stream.

```
On order fill event from Alpaca:
  - match broker_order_id to internal PaperOrder
  - create PaperFill from broker-reported fill data
  - update order status
  - trigger portfolio update
```

### Fallback

If the Alpaca paper API is unavailable:

```
PAPER_TRADING_BROKER_FALLBACK=simulation
```

If broker API call fails, fall back to internal simulation for that order.
Log a warning: "Broker API unavailable, using simulated fill for AAPL."

---

## 8. Forex Account Pool

### The Constraint

US forex brokers enforce FIFO netting: one net direction per pair per
account. Multiple strategies trading the same pair require separate accounts.

### Pool Model

The system maintains a pool of virtual accounts (paper mode) or real
OANDA accounts (live mode). Each account can hold positions in multiple
pairs simultaneously, but only one position per pair.

```
PAPER_TRADING_FOREX_ACCOUNT_POOL_SIZE=4
PAPER_TRADING_FOREX_CAPITAL_PER_ACCOUNT=25000.00
```

### Allocation Rule

An account is available for a pair if it has NO open position in that pair.
An account CAN hold positions in multiple different pairs simultaneously.

```
Account is available for {pair} if:
  no active allocation exists for this account + this pair

Account CAN simultaneously hold:
  EUR_USD long (Strategy A)
  GBP_USD short (Strategy B)
  USD_JPY long (Strategy C)
  (all different pairs, no conflict)
```

### Data Model

```
BrokerAccount:
  - id: UUID
  - broker: str (oanda)
  - account_id: str (broker account identifier, or virtual ID for paper)
  - account_type: str (paper_virtual | paper_real | live)
  - label: str (human-readable name)
  - is_active: bool
  - capital_allocation: Decimal
  - credentials_env_key: str, nullable (env var prefix for real accounts)
  - created_at: datetime
  - updated_at: datetime

AccountAllocation:
  - id: UUID
  - account_id: UUID (FK → BrokerAccount)
  - strategy_id: UUID (FK → Strategy)
  - symbol: str (the pair, e.g., EUR_USD)
  - side: str (long | short)
  - status: str (active | released)
  - allocated_at: datetime
  - released_at: datetime, nullable
  - created_at: datetime

Indexes:
  BrokerAccount: INDEX (broker, is_active)
  AccountAllocation: INDEX (account_id, symbol, status)
  AccountAllocation: INDEX (strategy_id, status)
  AccountAllocation: INDEX (symbol, status)
```

### Allocation Flow

When a forex signal is approved by risk:

```
1. Query: find an account with no active allocation for this pair
   
   SELECT ba.id FROM broker_accounts ba
   WHERE ba.broker = 'oanda'
     AND ba.is_active = true
     AND ba.id NOT IN (
       SELECT account_id FROM account_allocations
       WHERE symbol = :pair AND status = 'active'
     )
   LIMIT 1

2. If account found:
   → create AccountAllocation (status: active)
   → route order to this account
   → proceed with fill

3. If no account found:
   → reject order: "no_available_account"
   → trigger shadow tracking (see section 9)
```

### Release Flow

When a forex position closes (fill on an exit signal):

```
1. Find the AccountAllocation for this strategy + symbol
2. Set status = "released", released_at = now()
3. Account is now available for other strategies on this pair
```

### Contention Priority

MVP uses first-come-first-served. The strategy whose signal reaches
the paper trading engine first gets the available account.

Future options (configurable):
- Priority ranking (user assigns per strategy)
- Capital-weighted
- Round-robin

```
FOREX_ACCOUNT_ALLOCATION_PRIORITY=first_come  (default)
```

### Live Trading Transition

For live trading, virtual accounts map to real OANDA accounts:

```
Live account mapping:
  virtual_account_1 → OANDA 101-001-XXXXX-001
  virtual_account_2 → OANDA 101-001-XXXXX-002
  virtual_account_3 → OANDA 101-001-XXXXX-003
  virtual_account_4 → OANDA 101-001-XXXXX-004
```

Allocation logic doesn't change. Only the executor changes
(from simulated to OANDA API).

### Pool Status Dashboard

```
Account Pool Status:
  Account 1: EUR_USD long (London Breakout) since 08:15
             GBP_USD short (Cable Fade) since 09:30
  Account 2: EUR_USD short (Session Reversal) since 08:45
  Account 3: USD_JPY long (Yen Carry) since 07:00
  Account 4: (available)

  Pair capacity:
    EUR_USD: 3 of 4 accounts occupied (1 available)
    GBP_USD: 1 of 4 accounts occupied (3 available)
    USD_JPY: 1 of 4 accounts occupied (3 available)

  Available accounts: 1 of 4 fully empty
```

---

## 9. Shadow Tracking

### Purpose

When a forex signal is blocked due to account contention, track what
WOULD have happened if the account had been available. This allows
fair strategy comparison without contention bias.

### When Shadow Tracking Activates

Only for signals rejected with reason_code = "no_available_account".

Does NOT activate for:
- Risk rejections (exposure, drawdown, etc.)
- Market hours blocks
- Invalid symbols
- Deduplicated signals
- Equities signals (no contention problem)

```
SHADOW_TRACKING_ENABLED=true
SHADOW_TRACKING_FOREX_ONLY=true
```

### Shadow Fill Creation

When a signal is blocked by contention:

```
1. Record the rejection in the real track (signal rejected, no real fill)
2. Create a ShadowFill:
   - same symbol, side, qty, timing as the blocked signal
   - fill price based on market data at signal time
   - slippage and fees applied normally (same models as real fills)
3. Create or update a ShadowPosition
4. Log: "Shadow fill created for blocked signal {id}"
```

### Shadow Position Management

Shadow positions are fully managed, not just logged:

- Strategy runner evaluates exit conditions against shadow positions
- Stop loss / take profit / trailing stop are tracked
- When exit conditions are met, shadow position closes with a shadow fill
- PnL is calculated on close

The strategy runner's evaluation pipeline includes:

```
Existing step 7:  Evaluate exits for real positions
New step 7b:      Evaluate exits for shadow positions
                  (same logic, writes to shadow tables)
```

### Data Models

```
ShadowFill:
  - id: UUID
  - signal_id: UUID (FK → Signal, the blocked signal)
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - side: str (buy | sell)
  - qty: Decimal
  - reference_price: Decimal
  - price: Decimal (after slippage)
  - fee: Decimal
  - slippage_bps: Decimal
  - gross_value: Decimal
  - net_value: Decimal
  - fill_type: str (entry | exit)
  - shadow_position_id: UUID (FK → ShadowPosition)
  - filled_at: datetime
  - created_at: datetime

Indexes:
  INDEX (strategy_id, filled_at)
  INDEX (shadow_position_id)

ShadowPosition:
  - id: UUID
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - side: str (long | short)
  - qty: Decimal
  - avg_entry_price: Decimal
  - current_price: Decimal
  - unrealized_pnl: Decimal
  - realized_pnl: Decimal (set when closed)
  - status: str (open | closed)
  - stop_loss_price: Decimal, nullable
  - take_profit_price: Decimal, nullable
  - trailing_stop_price: Decimal, nullable
  - highest_price_since_entry: Decimal, nullable (for trailing stop)
  - opened_at: datetime
  - closed_at: datetime, nullable
  - close_reason: str, nullable (stop_loss | take_profit | trailing_stop |
                                  condition | max_hold)
  - entry_signal_id: UUID (FK → Signal)
  - exit_signal_id: UUID, nullable
  - created_at: datetime
  - updated_at: datetime

Indexes:
  INDEX (strategy_id, status)
  INDEX (symbol, status)
```

### Dashboard: Strategy Comparison

```
Strategy Comparison (EUR_USD):

  Strategy          True PnL    True Win%   Trades   Blocked
  ──────────────────────────────────────────────────────────
  London Breakout   +$2,940     65%         31       8
  Session Reversal  +$1,230     58%         28       4
  Asian Range       +$890       52%         19       2
  Scalper 5m        +$340       49%         67       14
```

### Per-Strategy Performance View

```
Strategy: London Breakout

  Real Performance (with account constraints):
    Trades: 23
    Win rate: 61%
    Total PnL: +$1,847
    Blocked signals: 8

  True Performance (unconstrained):
    Trades: 31
    Win rate: 65%
    Total PnL: +$2,940
    Additional trades from shadow: 8

  Contention Impact:
    Missed PnL: +$1,093
    Blocked entries that would have been winners: 5 of 8
```

### Isolation Rule

Shadow tracking is completely isolated from real tracking:

- Shadow fills never affect real positions
- Shadow positions never affect real portfolio equity
- Shadow PnL is never included in real performance metrics
- Shadow positions never trigger real risk checks
- Shadow positions never consume account pool allocations

The two tracks exist in separate tables and are only combined
in the comparison/analytics views.

---

## 10. Order Rejection Conditions

An order can be rejected even after risk approval:

```
Reject if:
  - No recent market data available for the symbol
    (can't determine reference price)
  - Symbol removed from watchlist between risk approval and fill
  - Insufficient cash for order value (see section 11)
  - Order quantity is zero or negative after rounding
  - Forex: no available account in pool (triggers shadow tracking)
```

Rejected orders are logged with reason. Signal status stays "risk_approved"
(risk did its job). Order status is "rejected" with reason. This preserves
the audit trail.

---

## 11. Cash Management

### Cash Check

```
For a buy order:
  required_cash = qty * reference_price * contract_multiplier + estimated_fee

  if required_cash > available_cash:
      reject("insufficient_cash",
             f"Need ${required_cash:.2f}, have ${available_cash:.2f}")
```

For forex with account pool: cash check is against the specific virtual
account's capital allocation, not the total portfolio cash.

Available cash is read from the portfolio module. The paper trading engine
checks but does not own cash balance.

For sell orders / closing positions: cash is released, not consumed.

### Initial Capital

```
PAPER_TRADING_INITIAL_CASH=100000.00
```

For forex with account pool:

```
PAPER_TRADING_FOREX_ACCOUNT_POOL_SIZE=4
PAPER_TRADING_FOREX_CAPITAL_PER_ACCOUNT=25000.00
Total forex capital = pool_size * capital_per_account = $100,000
```

---

## 12. Options Order Handling

Options orders use the same pipeline with additional fields:

```
Options specifics:
  - contract_multiplier: 100 (1 contract = 100 shares)
  - order qty is in contracts, not shares
  - gross_value = qty * contract_multiplier * price
  - reference price from option chain snapshot (market data module)
  - higher slippage default (wider spreads)

PAPER_TRADING_SLIPPAGE_BPS_OPTIONS=10
PAPER_TRADING_DEFAULT_CONTRACT_MULTIPLIER=100
```

The option contract symbol (e.g., "AAPL250620C00190000") is stored
as the order's symbol. The underlying_symbol, contract_type,
strike_price, and expiration_date fields are populated for options.

Options orders route through the Alpaca paper executor (same as equities).

---

## 13. Observability

### Log Events

```
paper_trading.order.created         (order_id, signal_id, symbol, side, qty, executor)
paper_trading.order.accepted        (order_id, broker_order_id if applicable)
paper_trading.order.filled          (order_id, fill_id, price, fee, slippage)
paper_trading.order.rejected        (order_id, reason)
paper_trading.order.canceled        (order_id, reason)
paper_trading.fill.processed        (fill_id, portfolio update triggered)
paper_trading.cash.insufficient     (order_id, required, available)
paper_trading.broker.api_error      (broker, error details, fallback used)
paper_trading.forex_pool.allocated  (account_id, strategy_id, symbol, side)
paper_trading.forex_pool.released   (account_id, strategy_id, symbol)
paper_trading.forex_pool.blocked    (strategy_id, symbol, reason)
paper_trading.shadow.fill_created   (shadow_fill_id, signal_id, symbol)
paper_trading.shadow.position_closed (shadow_position_id, pnl)
```

---

## 14. API Endpoints

```
# Orders
GET  /api/v1/paper-trading/orders              → list orders with filters
                                                 (strategy_id, symbol, status,
                                                  market, date range, page, page_size)
GET  /api/v1/paper-trading/orders/:id          → order detail with fills

# Fills
GET  /api/v1/paper-trading/fills               → list fills with filters
GET  /api/v1/paper-trading/fills/:id           → fill detail

# Statistics
GET  /api/v1/paper-trading/stats               → trading statistics
                                                 (total orders, fill rate,
                                                  avg slippage, total fees,
                                                  by market, by strategy)

# Forex Account Pool
GET  /api/v1/paper-trading/forex-pool/status   → current pool state
                                                 (accounts, allocations,
                                                  pair capacity)
GET  /api/v1/paper-trading/forex-pool/history  → allocation history

# Shadow Tracking
GET  /api/v1/paper-trading/shadow/positions    → shadow positions (open + closed)
GET  /api/v1/paper-trading/shadow/fills        → shadow fills
GET  /api/v1/paper-trading/shadow/comparison   → real vs shadow performance comparison
                                                 (per strategy, per pair)
```

Orders are NOT created through the API directly. They are created
by the paper trading engine when it processes risk-approved signals.

---

## 15. Configuration Variables

```
# Execution Mode
PAPER_TRADING_EXECUTION_MODE_EQUITIES=paper    (paper | simulation)
PAPER_TRADING_EXECUTION_MODE_FOREX=simulation  (simulation with pool)
PAPER_TRADING_BROKER_FALLBACK=simulation       (fallback if broker API fails)

# Slippage
PAPER_TRADING_SLIPPAGE_BPS_EQUITIES=5
PAPER_TRADING_SLIPPAGE_BPS_FOREX=2
PAPER_TRADING_SLIPPAGE_BPS_OPTIONS=10

# Fees
PAPER_TRADING_FEE_PER_TRADE_EQUITIES=0.00
PAPER_TRADING_FEE_SPREAD_BPS_FOREX=15
PAPER_TRADING_FEE_PER_TRADE_OPTIONS=0.00

# Capital
PAPER_TRADING_INITIAL_CASH=100000.00

# Forex Account Pool
PAPER_TRADING_FOREX_ACCOUNT_POOL_SIZE=4
PAPER_TRADING_FOREX_CAPITAL_PER_ACCOUNT=25000.00
FOREX_ACCOUNT_ALLOCATION_PRIORITY=first_come

# Options
PAPER_TRADING_DEFAULT_CONTRACT_MULTIPLIER=100

# Shadow Tracking
SHADOW_TRACKING_ENABLED=true
SHADOW_TRACKING_FOREX_ONLY=true
```

---

## 16. Database Tables Owned

| Table | Purpose |
|---|---|
| paper_orders | All order records with full lifecycle |
| paper_fills | All fill records with execution details |
| broker_accounts | Account pool registry (virtual and real) |
| account_allocations | Forex account-to-strategy-to-pair allocations |
| shadow_fills | Shadow fills for contention-blocked signals |
| shadow_positions | Shadow position tracking with full PnL lifecycle |

---

## Acceptance Criteria

This spec is accepted when:

- Executor abstraction with multiple implementations is defined
- Equities broker paper trading flow (Alpaca) is specified
- Forex internal simulation with account pool is specified
- Account pool allocation and release logic is explicit
- Account availability rule is clear (per-pair, not per-account)
- Shadow tracking activation conditions are defined
- Shadow position lifecycle (entry, management, exit, PnL) is specified
- Shadow vs real isolation rule is documented
- Fill simulation logic (reference price, slippage, fees) is step-by-step
- Order rejection conditions are enumerated
- Cash management checks are specified
- Options order handling is defined
- Order lifecycle states and transitions are documented
- All log events are listed
- All API endpoints are enumerated
- All configuration variables are listed
- All database tables are enumerated
- A builder agent can implement this module without asking engineering design questions
