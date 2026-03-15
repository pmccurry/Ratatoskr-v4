# PORTFOLIO_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the portfolio module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The portfolio module owns:

- Position tracking (open, scale, close)
- Cash balance management
- Mark-to-market pricing
- Unrealized and realized PnL calculation
- Equity calculation
- Portfolio snapshots (periodic, event, daily)
- Peak equity and drawdown tracking
- Realized PnL ledger
- Dividend payment processing and income tracking
- Stock split position adjustment
- Per-strategy performance metrics
- Position lifecycle events

The portfolio module does NOT own:

- Fill creation (owned by paper trading module)
- Order execution (owned by paper trading module)
- Risk evaluation (owned by risk module, reads from portfolio)
- Signal generation (owned by strategy module)
- Dividend announcement fetching (owned by market data module)
- Corporate actions data sourcing (owned by market data module)

---

## 1. How Fills Become Positions

When the paper trading engine calls `portfolio_service.process_fill(fill)`,
the portfolio module performs one of four operations depending on existing
position state.

### Entry Fill (no existing position for strategy + symbol)

```
Create new Position:
  strategy_id = fill.strategy_id
  symbol = fill.symbol
  market = fill.market (from order)
  side = "long" if fill.side == "buy" else "short"
  qty = fill.qty
  avg_entry_price = fill.price
  cost_basis = fill.net_value
  current_price = fill.price
  market_value = fill.qty * fill.price * contract_multiplier
  unrealized_pnl = 0
  realized_pnl = 0
  total_fees = fill.fee
  total_dividends_received = 0
  status = "open"
  opened_at = fill.filled_at
  highest_price_since_entry = fill.price
  lowest_price_since_entry = fill.price
  bars_held = 0
  broker_account_id = fill.broker_account_id (for forex pool)
  contract_multiplier = from order (1 for equities/forex, 100 for options)
  underlying_symbol = from order (for options)
  contract_type = from order (for options)
  strike_price = from order (for options)
  expiration_date = from order (for options)

Cash adjustment:
  if buy: cash -= fill.net_value
  if sell (opening short): cash += fill.net_value
```

### Scale-In Fill (existing position, same direction)

```
Update Position:
  new_total_qty = position.qty + fill.qty
  avg_entry_price = weighted average:
    ((position.qty * position.avg_entry_price) + (fill.qty * fill.price))
    / new_total_qty
  qty = new_total_qty
  cost_basis += fill.net_value
  total_fees += fill.fee

Cash adjustment:
  if buy: cash -= fill.net_value
  if sell (adding to short): cash += fill.net_value
```

### Scale-Out Fill (existing position, partial close)

```
Calculate realized PnL on closed portion:
  if long:
    gross_pnl = (fill.price - position.avg_entry_price) * fill.qty * multiplier
    net_pnl = gross_pnl - fill.fee
  if short:
    gross_pnl = (position.avg_entry_price - fill.price) * fill.qty * multiplier
    net_pnl = gross_pnl - fill.fee

Update Position:
  qty -= fill.qty
  realized_pnl += net_pnl
  cost_basis adjusted proportionally:
    cost_basis = cost_basis * (remaining_qty / original_qty)
  total_fees += fill.fee

Create RealizedPnlEntry for the closed portion.

Cash adjustment:
  if selling (closing long): cash += fill.net_value
  if buying (closing short): cash -= fill.net_value
```

### Full Exit Fill (closing entire position)

```
Calculate realized PnL on full position:
  if long:
    gross_pnl = (fill.price - position.avg_entry_price) * fill.qty * multiplier
    net_pnl = gross_pnl - fill.fee
  if short:
    gross_pnl = (position.avg_entry_price - fill.price) * fill.qty * multiplier
    net_pnl = gross_pnl - fill.fee

Update Position:
  qty = 0
  realized_pnl += net_pnl
  total_fees += fill.fee
  status = "closed"
  closed_at = fill.filled_at
  close_reason = from signal's exit_reason
  total_return = realized_pnl + total_dividends_received

Create RealizedPnlEntry for the full close.

Cash adjustment:
  if selling (closing long): cash += fill.net_value
  if buying (closing short): cash -= fill.net_value

Release forex account allocation if applicable.
```

### Atomicity

The fill processing and position update must be atomic — both succeed
or both fail within the same database transaction. A fill that persists
without a position update (or vice versa) would corrupt portfolio state.

---

## 2. Position Data Model

```
Position:
  - id: UUID
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - market: str (equities | forex)
  - side: str (long | short)
  - qty: Decimal
  - avg_entry_price: Decimal
  - cost_basis: Decimal (total cost including fees at entry)
  - current_price: Decimal (last mark-to-market price)
  - market_value: Decimal (qty * current_price * contract_multiplier)
  - unrealized_pnl: Decimal
  - unrealized_pnl_percent: Decimal
  - realized_pnl: Decimal (accumulated from partial closes)
  - total_fees: Decimal (all fees on this position)
  - total_dividends_received: Decimal (default 0)
  - total_return: Decimal (unrealized_pnl + realized_pnl + dividends)
  - total_return_percent: Decimal
  - status: str (open | closed)
  - opened_at: datetime
  - closed_at: datetime, nullable
  - close_reason: str, nullable (stop_loss | take_profit | trailing_stop |
                                  max_hold | condition | manual | safety |
                                  system | expiration)
  - highest_price_since_entry: Decimal (for trailing stop)
  - lowest_price_since_entry: Decimal (for short trailing stops)
  - bars_held: int (evaluation cycles since entry)
  - broker_account_id: UUID, nullable (FK → BrokerAccount, forex pool)
  - underlying_symbol: str, nullable (for options)
  - contract_type: str, nullable (call | put)
  - strike_price: Decimal, nullable
  - expiration_date: date, nullable
  - contract_multiplier: int (default 1, options = 100)
  - created_at: datetime
  - updated_at: datetime

Indexes:
  INDEX (strategy_id, status)
  INDEX (symbol, status)
  INDEX (status)
  INDEX (strategy_id, symbol, status)
  INDEX (broker_account_id, status) WHERE broker_account_id IS NOT NULL
  INDEX (expiration_date) WHERE expiration_date IS NOT NULL
```

---

## 3. Mark-to-Market

### Process

Runs every PORTFOLIO_MARK_TO_MARKET_INTERVAL_SEC (default: 60 seconds).
Only during market hours for the position's market.

```
For each open position:
  current_price = market_data_service.get_latest_close(
    symbol=position.symbol, timeframe="1m")

  if position.side == "long":
    unrealized_pnl = (current_price - avg_entry_price) * qty * multiplier
    unrealized_pnl_percent = (current_price - avg_entry_price)
                              / avg_entry_price * 100
  elif position.side == "short":
    unrealized_pnl = (avg_entry_price - current_price) * qty * multiplier
    unrealized_pnl_percent = (avg_entry_price - current_price)
                              / avg_entry_price * 100

  market_value = qty * current_price * multiplier

  total_return = unrealized_pnl + realized_pnl + total_dividends_received
  total_return_percent = total_return / cost_basis * 100

  # Update tracking fields
  highest_price_since_entry = max(highest_price_since_entry, current_price)
  lowest_price_since_entry = min(lowest_price_since_entry, current_price)

  Update position with all new values
```

### Market Hours Awareness

- Equities: mark-to-market only during 9:30 AM - 4:00 PM ET, weekdays
- Forex: mark-to-market Sunday 5 PM - Friday 5 PM ET
- Outside hours: last known price persists, no updates

### Stale Price Handling

If market data is unhealthy (stale prices), mark-to-market logs a warning
but uses the last known price. Positions should always show some value,
even if slightly stale. The dashboard shows a stale indicator.

### Options Mark-to-Market

Options positions use the option's current price (from the option chain
snapshot), not the underlying price:

```
current_price = market_data_service.get_option_snapshot(
  contract_symbol=position.symbol).latest_price
```

If the option snapshot is unavailable, fall back to intrinsic value
calculated from the underlying price.

---

## 4. Cash Balance

### Model

```
CashBalance:
  - id: UUID
  - account_scope: str
      "equities" — single equity account
      "forex_pool_1" through "forex_pool_N" — per virtual forex account
  - balance: Decimal
  - updated_at: datetime

Single row per account scope.
```

### Cash Operations

```
Buy fill (opening long):     cash -= fill.net_value
Sell fill (closing long):    cash += fill.net_value
Sell fill (opening short):   cash += fill.net_value
Buy fill (closing short):    cash -= fill.net_value
Dividend payment:            cash += dividend.net_amount
```

### Forex Pool Cash

Each virtual forex account has its own cash balance:

```
Global cash view:
  Equities:       $58,000
  Forex Pool 1:   $23,200
  Forex Pool 2:   $24,800
  Forex Pool 3:   $25,000
  Forex Pool 4:   $25,000
  Total cash:     $156,000
```

### Initial Capital

```
PAPER_TRADING_INITIAL_CASH=100000.00
PAPER_TRADING_FOREX_CAPITAL_PER_ACCOUNT=25000.00
```

The portfolio module is the source of truth for cash. The paper trading
engine reads it for availability checks. The risk engine reads it for
exposure calculations.

---

## 5. Equity Calculation

```
equity = total_cash + sum(position.market_value for all open positions)
```

Recalculated on every mark-to-market cycle. Includes all account scopes
(equities + all forex pool accounts).

For forex pool:

```
total_forex_equity = sum(
  pool_account.cash + sum(pool_account.positions.market_value)
  for each pool account
)
total_equity = equities_cash + equities_positions_value + total_forex_equity
```

---

## 6. Portfolio Snapshots

### Model

```
PortfolioSnapshot:
  - id: UUID
  - ts: datetime (UTC)
  - cash_balance: Decimal (total across all accounts)
  - positions_value: Decimal (total market value of all open positions)
  - equity: Decimal (cash + positions value)
  - unrealized_pnl: Decimal (sum across all open positions)
  - realized_pnl_today: Decimal
  - realized_pnl_total: Decimal
  - dividend_income_today: Decimal
  - dividend_income_total: Decimal
  - drawdown_percent: Decimal
  - peak_equity: Decimal
  - open_positions_count: int
  - snapshot_type: str (periodic | event | daily_close)
  - created_at: datetime

Indexes:
  INDEX (ts)
  INDEX (snapshot_type, ts)
```

### Snapshot Triggers

```
Periodic:    every PORTFOLIO_SNAPSHOT_INTERVAL_SEC (default: 300, 5 minutes)
Event:       after every fill (captures equity change at trade time)
Daily close: at market close (clean daily record for equity curve)
```

Periodic snapshots feed the equity curve chart.
Event snapshots give precise equity values at trade time.
Daily close snapshots provide a clean daily series for Sharpe ratio,
drawdown curves, and longer-term analysis.

---

## 7. Realized PnL Ledger

### Model

```
RealizedPnlEntry:
  - id: UUID
  - position_id: UUID (FK → Position)
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - market: str
  - side: str (long | short)
  - qty_closed: Decimal
  - entry_price: Decimal (avg entry at time of close)
  - exit_price: Decimal
  - gross_pnl: Decimal (before fees)
  - fees: Decimal
  - net_pnl: Decimal (after fees)
  - pnl_percent: Decimal
  - holding_period_bars: int
  - closed_at: datetime
  - created_at: datetime

Indexes:
  INDEX (strategy_id, closed_at)
  INDEX (symbol, closed_at)
  INDEX (closed_at)
```

Append-only table. Entries are never modified after creation.

This table is the source of truth for all realized PnL calculations:
daily, weekly, monthly, per-strategy, per-symbol, per-market.

---

## 8. Peak Equity and Drawdown

### Peak Tracking

```
peak_equity = max(all historical equity values)
current_drawdown = (peak_equity - current_equity) / peak_equity * 100
```

Updated on every mark-to-market cycle when equity exceeds current peak.
Stored persistently — survives restarts.

```
PortfolioMeta:
  - id: UUID
  - key: str
  - value: str
  - updated_at: datetime

Keys:
  "peak_equity":     "103500.00"
  "peak_equity_at":  "2025-03-08T14:30:00Z"
  "initial_capital": "100000.00"
  "inception_date":  "2025-03-01"
```

### Peak Reset

Peak equity never auto-resets. A drawdown that recovers doesn't reset
the high-water mark.

Manual reset is supported through an admin endpoint (e.g., after adding
capital). Reset is logged in the event log.

### Drawdown Thresholds

The risk engine reads peak_equity and current_equity from the portfolio
module for drawdown checks. The portfolio module owns the calculation;
the risk engine owns the policy (what happens when thresholds are breached).

---

## 9. Dividend Processing

### Data Source

The market_data module fetches dividend announcements from Alpaca's
Corporate Actions API daily and stores them in a DividendAnnouncement
table (owned by market_data).

The portfolio module reads from this table to process payments.

### Dividend Announcement Model (owned by market_data)

```
DividendAnnouncement:
  - id: UUID
  - symbol: str
  - corporate_action_id: str (Alpaca's persistent ID)
  - ca_type: str (cash | stock)
  - declaration_date: date
  - ex_date: date
  - record_date: date
  - payable_date: date
  - cash_amount: Decimal (per share, for cash dividends)
  - stock_rate: Decimal, nullable (for stock dividends)
  - status: str (announced | confirmed | paid | canceled)
  - source: str (alpaca)
  - fetched_at: datetime
  - created_at: datetime
  - updated_at: datetime

Indexes:
  INDEX (symbol, ex_date)
  INDEX (ex_date)
  INDEX (payable_date)
  INDEX (status)
```

### Dividend Payment Model (owned by portfolio)

```
DividendPayment:
  - id: UUID
  - dividend_id: UUID (FK → DividendAnnouncement)
  - position_id: UUID (FK → Position)
  - strategy_id: UUID (FK → Strategy)
  - symbol: str
  - shares_held: Decimal (qty held at record date)
  - cash_amount_per_share: Decimal
  - gross_amount: Decimal (shares * cash per share)
  - tax_withheld: Decimal (default 0 for paper trading)
  - net_amount: Decimal (gross - tax)
  - status: str (pending | paid | canceled)
  - ex_date: date
  - payable_date: date
  - paid_at: datetime, nullable
  - created_at: datetime

Indexes:
  INDEX (strategy_id, paid_at)
  INDEX (position_id)
  INDEX (status, payable_date)
```

### Processing Cycle

Daily job runs after market close:

```
1. Ex-date processing (runs on ex-date):
   For each DividendAnnouncement where ex_date == today:
     For each open position in that symbol:
       if position.opened_at < ex_date (held before ex-date):
         Create DividendPayment:
           shares_held = position.qty
           gross_amount = position.qty * announcement.cash_amount
           net_amount = gross_amount (no tax withholding in paper)
           status = "pending"
         Log: "Position {id} eligible for ${amount} dividend on {symbol}"

2. Payable date processing (runs on payable_date):
   For each DividendPayment where payable_date == today AND status == "pending":
     Credit cash balance: cash += net_amount
     Update payment status to "paid", paid_at = now()
     Update position.total_dividends_received += net_amount
     Recalculate position.total_return
     Log: "Dividend paid: ${amount} for {shares} shares of {symbol}"
```

### PnL Impact

Dividends are tracked separately from price PnL. Cost basis is NOT adjusted.

```
Per position:
  Price P&L = unrealized_pnl (current_price vs entry_price)
  Dividend Income = total_dividends_received
  Total Return = unrealized_pnl + realized_pnl + total_dividends_received

Dashboard display:
  AAPL  100 shares  Long  Entry: $190.00  Current: $189.50
    Price P&L:      -$50.00 (-0.26%)
    Dividends:      +$22.00
    Total Return:   -$28.00 (-0.15%)
```

### Dividend Indicators for Strategies

The market_data service exposes dividend data for strategy evaluation:

```
market_data_service.get_upcoming_dividends(symbol) → list[DividendAnnouncement]
market_data_service.get_dividend_yield(symbol) → Decimal (annualized)
market_data_service.get_next_ex_date(symbol) → date | None
```

These are available as strategy indicators in the condition engine:

```
Indicator catalog additions:
  - dividend_yield:    annualized yield based on recent dividends
  - days_to_ex_date:   days until next ex-dividend date (null if none upcoming)
  - dividend_amount:   next expected dividend per share
```

A dividend capture strategy example:

```
Entry conditions (AND):
  - dividend_yield > 3.0
  - days_to_ex_date between 1 and 5
  - RSI(14) < 60
  - volume > 500000

Exit conditions (OR):
  - days_to_ex_date == 0 (ex-date reached)
  - stop_loss: 1.5%
```

### Corporate Actions Fetch Configuration

```
CORPORATE_ACTIONS_FETCH_SCHEDULE=0 8 * * 1-5   (8 AM ET, weekdays)
CORPORATE_ACTIONS_LOOKFORWARD_DAYS=30
```

30-day lookforward covers both quick-flip dividend strategies (enter 2-5
days before ex-date) and extended hold strategies (use yield as entry
criteria without specific timing).

---

## 10. Stock Split Processing

### When Splits Are Detected

The market_data module fetches split announcements from Alpaca's Corporate
Actions API alongside dividends.

### Position Adjustment

On split effective date:

```
For each open position in the split symbol:
  adjustment_factor = new_rate / old_rate

  Forward split (e.g., 4:1, old=1, new=4):
    position.qty *= 4
    position.avg_entry_price /= 4
    position.highest_price_since_entry /= 4
    position.lowest_price_since_entry /= 4
    # cost_basis unchanged (same total investment)
    # market_value recalculated on next mark-to-market

  Reverse split (e.g., 1:10, old=10, new=1):
    position.qty /= 10
    position.avg_entry_price *= 10
    # same principle — cost_basis unchanged
```

### Data Model

```
SplitAdjustment:
  - id: UUID
  - symbol: str
  - split_type: str (forward | reverse)
  - old_rate: int
  - new_rate: int
  - effective_date: date
  - positions_adjusted: int
  - adjustments_json: list[dict] (per-position before/after for audit)
  - created_at: datetime

Indexes:
  INDEX (symbol, effective_date)
```

### Historical Data

Historical bar data also needs split adjustment for backtesting accuracy.
Alpaca provides split-adjusted historical data. The market_data module
should request adjusted data for backfills. This is a market_data concern,
not a portfolio concern.

---

## 11. Options Position Lifecycle

### Expiration Handling

Options have an expiration date. Daily job checks for expiring positions:

```
Daily at market close:
  For each open option position:
    if position.expiration_date <= today:
      underlying_price = market_data_service.get_latest_close(
        position.underlying_symbol)

      if position.contract_type == "call":
        intrinsic = max(0, underlying_price - position.strike_price)
      elif position.contract_type == "put":
        intrinsic = max(0, position.strike_price - underlying_price)

      intrinsic_value = intrinsic * position.qty * position.contract_multiplier

      if intrinsic > 0:
        # In-the-money: close at intrinsic value
        close position with exit_price = intrinsic / contract_multiplier
        close_reason = "expiration"
      else:
        # Out-of-the-money: expire worthless
        close position with exit_price = 0
        close_reason = "expiration"
        realized_pnl = -cost_basis (total loss)
```

### Assignment Risk

Short options assignment is deferred to post-MVP. Paper trading MVP
only handles long options positions.

---

## 12. Forex Position Specifics

### PnL Calculation

For USD-quoted pairs (most majors):

```
EUR/USD long 10,000 units:
  entry: 1.0850
  current: 1.0920
  PnL = (1.0920 - 1.0850) * 10,000 = $70.00 USD
```

For cross pairs (EUR/GBP) where USD is not the quote currency,
conversion through USD is needed. For MVP, support only pairs where
USD is the quote currency. Flag cross-pair PnL conversion as future
enhancement.

### Per-Account Tracking

Forex positions are tracked per virtual account (from the forex pool).
Each account has its own cash balance and position set.

Portfolio-level metrics aggregate across all forex accounts.

---

## 13. Performance Metrics

Calculated on demand from underlying data. No pre-aggregated tables needed.

### Per Strategy and Portfolio-Wide

```
Total return:
  (current_equity - initial_capital) / initial_capital * 100

Total PnL:
  realized_pnl_total + unrealized_pnl_total + dividend_income_total

Win rate:
  winning_trades / total_trades * 100
  (a trade "wins" if net_pnl > 0 in RealizedPnlEntry)

Profit factor:
  sum(winning_pnl) / abs(sum(losing_pnl))

Average winner:
  sum(positive net_pnl entries) / count(winners)

Average loser:
  sum(negative net_pnl entries) / count(losers)

Risk/reward ratio:
  average_winner / abs(average_loser)

Max drawdown:
  largest peak-to-trough decline in equity
  (calculated from PortfolioSnapshot time series)

Sharpe ratio:
  (avg_daily_return - risk_free_rate) / std_dev(daily_returns)
  (calculated from daily_close snapshots)
  risk_free_rate: configurable, default 0.05 (5% annual)

Sortino ratio:
  (avg_daily_return - risk_free_rate) / std_dev(negative_daily_returns)

Average hold time:
  avg(holding_period_bars) from RealizedPnlEntry

Longest win streak:
  max consecutive winning trades (from RealizedPnlEntry ordered by closed_at)

Longest loss streak:
  max consecutive losing trades
```

### Dividend-Inclusive Metrics

When calculating strategy performance, total return includes dividends:

```
Strategy total return = price_pnl + dividend_income
Strategy win rate: trade "wins" if (price_pnl + dividends_during_hold) > 0
```

The dashboard offers a toggle: "Include dividends in performance metrics"
so users can see both perspectives.

### Configuration

```
PORTFOLIO_RISK_FREE_RATE=0.05
```

---

## 14. Dashboard Views

### Portfolio Overview

```
Portfolio Summary:
  Total Equity:      $103,847
  Cash:              $58,200
  Positions Value:   $45,647
  Total Return:      +$3,847 (+3.85%)
  Today's P&L:       +$127 (+0.12%)

  Unrealized P&L:    +$1,230
  Realized P&L:      +$2,340
  Dividend Income:   $277

  Drawdown:          1.2% (peak: $105,100)
  Open Positions:    5

  [Equity Curve Chart — from snapshots]
```

### Positions View

```
Open Positions:
  Symbol  Side  Qty   Entry    Current  Price P&L   Divs   Total     Strategy
  AAPL    Long  100   $190.00  $192.30  +$230       $22    +$252     RSI Momentum
  MSFT    Long  50    $420.00  $418.30  -$85        $38    -$47      Div Capture
  EUR_USD Long  10k   1.0850   1.0920   +$70        -      +$70      London Break

Closed Positions (recent):
  Symbol  Side  Qty   Entry    Exit     P&L      Hold   Reason      Strategy
  NVDA    Long  30    $880.00  $895.00  +$412    8 bars  condition  RSI Momentum
  GOOGL   Long  20    $175.00  $172.50  -$55     3 bars  stop_loss  Breakout
```

### Per-Strategy Performance

```
Strategy: RSI + EMA Momentum
  Open Positions: 2
  Total Trades: 23 (14 wins, 9 losses)
  Win Rate: 61%
  Total P&L: +$1,847 (price) + $60 (dividends) = +$1,907
  Profit Factor: 2.3
  Average Winner: +$203
  Average Loser: -$112
  Max Drawdown: 4.2%
  Sharpe Ratio: 1.8
  Avg Hold Time: 12 bars

  [Strategy equity curve]
  [Win/loss distribution chart]
```

### Dividend Income View

```
Dividend Income:
  Today:      $0.00
  This Month: $147.50
  This Year:  $892.00
  All Time:   $892.00

  Recent Payments:
    Mar 8   AAPL  $22.00   (100 shares × $0.22)  RSI Momentum
    Mar 1   MSFT  $37.50   (50 shares × $0.75)   Div Capture
    Feb 15  JNJ   $88.00   (80 shares × $1.10)   Div Capture

  Upcoming (eligible based on current holdings):
    Mar 15  KO    $0.48/share  (200 shares → $96.00)  Div Capture
    Mar 22  PG    $0.94/share  (not currently held)
```

---

## 15. Portfolio Event Log

```
Events:
  portfolio.position.opened           (position_id, strategy, symbol, side, qty, price)
  portfolio.position.scaled_in        (position_id, additional_qty, new_avg_price)
  portfolio.position.scaled_out       (position_id, closed_qty, realized_pnl)
  portfolio.position.closed           (position_id, realized_pnl, close_reason, total_return)
  portfolio.pnl.realized              (entry_id, strategy, symbol, net_pnl)
  portfolio.equity.snapshot           (equity, cash, positions_value, drawdown)
  portfolio.equity.new_peak           (new_peak, previous_peak)
  portfolio.equity.peak_reset         (new_peak, reset_by)
  portfolio.cash.adjusted             (account_scope, old_balance, new_balance, reason)
  portfolio.dividend.eligible         (position_id, symbol, amount, ex_date)
  portfolio.dividend.paid             (payment_id, symbol, amount, cash_credited)
  portfolio.split.adjusted            (symbol, split_ratio, positions_affected)
  portfolio.option.expired            (position_id, intrinsic_value, realized_pnl)
  portfolio.mark_to_market.completed  (positions_updated, duration_ms)
  portfolio.mark_to_market.stale      (count of positions with stale prices)
  portfolio.corporate_action.fetched  (symbols_checked, events_found)
```

---

## 16. Folder Structure

```
backend/app/portfolio/
    __init__.py
    service.py              ← position CRUD, fill processing, equity calculation
    models.py               ← SQLAlchemy models
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← portfolio module configuration
    mark_to_market.py       ← periodic mark-to-market cycle
    snapshots.py            ← snapshot creation and management
    pnl.py                  ← realized PnL ledger and calculations
    metrics.py              ← performance metric calculations
    cash.py                 ← cash balance management
    dividends.py            ← dividend payment processing
    splits.py               ← stock split position adjustment
    options_lifecycle.py    ← options expiration handling
```

---

## 17. API Endpoints

```
# Positions
GET  /api/v1/portfolio/positions              → list positions with filters
                                                (strategy_id, symbol, status,
                                                 market, page, page_size)
GET  /api/v1/portfolio/positions/:id          → position detail with fill history
GET  /api/v1/portfolio/positions/open         → all open positions
GET  /api/v1/portfolio/positions/closed       → closed positions with date range

# Portfolio State
GET  /api/v1/portfolio/summary               → current portfolio summary
                                                (equity, cash, PnL, drawdown)
GET  /api/v1/portfolio/equity                 → current equity breakdown
                                                (by account scope, by market)
GET  /api/v1/portfolio/cash                   → cash balances per account scope

# Snapshots and History
GET  /api/v1/portfolio/snapshots              → snapshot time series
                                                (type, date range, resolution)
GET  /api/v1/portfolio/equity-curve           → equity values over time
                                                (for charting)

# PnL
GET  /api/v1/portfolio/pnl/realized           → realized PnL entries with filters
                                                (strategy_id, symbol, date range)
GET  /api/v1/portfolio/pnl/summary            → PnL summary
                                                (today, week, month, total,
                                                 by strategy, by symbol)

# Dividends
GET  /api/v1/portfolio/dividends              → dividend payment history
GET  /api/v1/portfolio/dividends/upcoming     → upcoming dividends for held positions
GET  /api/v1/portfolio/dividends/summary      → dividend income summary

# Performance Metrics
GET  /api/v1/portfolio/metrics                → full metrics
                                                (win rate, profit factor, Sharpe, etc.)
GET  /api/v1/portfolio/metrics/:strategy_id   → per-strategy metrics

# Admin
POST /api/v1/portfolio/drawdown/reset-peak    → manually reset peak equity
POST /api/v1/portfolio/cash/adjust            → manually adjust cash balance
                                                (admin only, logged)
```

---

## 18. Configuration Variables

```
# Mark-to-Market
PORTFOLIO_MARK_TO_MARKET_INTERVAL_SEC=60

# Snapshots
PORTFOLIO_SNAPSHOT_INTERVAL_SEC=300

# Metrics
PORTFOLIO_RISK_FREE_RATE=0.05

# Dividends
CORPORATE_ACTIONS_FETCH_SCHEDULE=0 8 * * 1-5
CORPORATE_ACTIONS_LOOKFORWARD_DAYS=30

# Initial State
PAPER_TRADING_INITIAL_CASH=100000.00
```

---

## 19. Database Tables Owned

| Table | Purpose |
|---|---|
| positions | All position records (open and closed) |
| realized_pnl_entries | Append-only realized PnL ledger |
| portfolio_snapshots | Periodic, event, and daily equity snapshots |
| portfolio_meta | Key-value store for peak equity, initial capital, etc. |
| cash_balances | Cash balance per account scope |
| dividend_payments | Dividend payment records per position |
| split_adjustments | Stock split adjustment audit records |

### Tables Read From (owned by other modules)

| Table | Owner | Purpose |
|---|---|---|
| paper_fills | paper_trading | Input for position updates |
| dividend_announcements | market_data | Source for dividend processing |
| ohlcv_bars | market_data | Current prices for mark-to-market |
| strategies | strategies | Strategy identity for per-strategy tracking |

---

## Acceptance Criteria

This spec is accepted when:

- Fill-to-position logic for all four scenarios (entry, scale-in, scale-out, exit) is explicit
- Position data model covers all fields including dividends and options
- Mark-to-market process is specified with market hours awareness
- Cash balance management covers all account scopes (equities, forex pool)
- Equity calculation is defined
- Portfolio snapshot triggers and model are specified
- Realized PnL ledger is defined as append-only
- Peak equity and drawdown tracking is specified
- Dividend processing cycle (ex-date, payable date) is step-by-step
- Dividend PnL treatment (separate from price PnL, no cost basis adjustment) is documented
- Dividend indicators for strategy use are defined
- Stock split position adjustment is specified
- Options expiration handling is specified
- Forex per-account tracking is specified
- All performance metrics formulas are listed
- Dashboard views are described
- All events are enumerated
- All API endpoints are listed
- All configuration variables are listed
- All owned and referenced database tables are enumerated
- A builder agent can implement this module without asking engineering design questions
