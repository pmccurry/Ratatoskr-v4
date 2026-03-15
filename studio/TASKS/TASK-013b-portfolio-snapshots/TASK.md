# TASK-013b — Portfolio: Snapshots, PnL Ledger, Dividends, Splits, Options, and Metrics

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Complete the portfolio module with analytics, corporate actions, and
lifecycle handling that builds on the core from TASK-013a.

After this task:
- Portfolio snapshots capture equity state periodically, on events, and at daily close
- The realized PnL ledger provides an append-only record of every closed trade
- Dividend payments are processed (ex-date eligibility → payable date cash credit)
- Stock splits adjust position quantities and entry prices
- Options positions expire at intrinsic value (ITM) or zero (OTM)
- Performance metrics are calculated on demand (Sharpe, Sortino, profit factor, etc.)
- Equity curve data is available for charting
- Full PnL, dividend, and metrics API endpoints exist

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/portfolio_module_spec.md — PRIMARY SPEC, sections 6-7, 9-13
5. /studio/SPECS/cross_cutting_specs.md
6. Review TASK-013a BUILDER_OUTPUT.md — understand existing portfolio code

## Constraints

- Do NOT modify Position, CashBalance, or PortfolioMeta models from TASK-013a
  (add new models alongside them)
- Do NOT modify fill processing logic from TASK-013a
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow repository pattern and API conventions
- All financial values use Decimal, all timestamps UTC

---

## Deliverables

### 1. New Models (add to backend/app/portfolio/models.py)

**PortfolioSnapshot:**
```
PortfolioSnapshot:
  - id: UUID (from BaseModel)
  - user_id: UUID (FK → users.id)
  - ts: datetime (UTC)
  - cash_balance: Numeric
  - positions_value: Numeric
  - equity: Numeric
  - unrealized_pnl: Numeric
  - realized_pnl_today: Numeric
  - realized_pnl_total: Numeric
  - dividend_income_today: Numeric
  - dividend_income_total: Numeric
  - drawdown_percent: Numeric
  - peak_equity: Numeric
  - open_positions_count: int
  - snapshot_type: str (periodic | event | daily_close)
  - created_at (from BaseModel)

Indexes:
  INDEX (ts)
  INDEX (snapshot_type, ts)
  INDEX (user_id, ts)
```

**RealizedPnlEntry:**
```
RealizedPnlEntry:
  - id: UUID (from BaseModel)
  - position_id: UUID (FK → positions.id)
  - strategy_id: UUID (FK → strategies.id)
  - user_id: UUID (FK → users.id)
  - symbol: str
  - market: str
  - side: str (long | short)
  - qty_closed: Numeric
  - entry_price: Numeric
  - exit_price: Numeric
  - gross_pnl: Numeric
  - fees: Numeric
  - net_pnl: Numeric
  - pnl_percent: Numeric
  - holding_period_bars: int
  - closed_at: datetime
  - created_at (from BaseModel)

Indexes:
  INDEX (strategy_id, closed_at)
  INDEX (symbol, closed_at)
  INDEX (closed_at)
  INDEX (user_id, closed_at)

Append-only — entries are never modified after creation.
```

**DividendPayment:**
```
DividendPayment:
  - id: UUID (from BaseModel)
  - position_id: UUID (FK → positions.id)
  - announcement_id: UUID (FK → dividend_announcements.id)
  - user_id: UUID (FK → users.id)
  - symbol: str
  - ex_date: date
  - payable_date: date
  - shares_held: Numeric (qty at ex-date)
  - amount_per_share: Numeric
  - gross_amount: Numeric
  - net_amount: Numeric (after any withholding — same as gross for MVP)
  - status: str (pending | paid)
  - paid_at: datetime, nullable
  - created_at (from BaseModel)

Indexes:
  INDEX (position_id)
  INDEX (user_id, payable_date)
  INDEX (status)
```

**SplitAdjustment:**
```
SplitAdjustment:
  - id: UUID (from BaseModel)
  - symbol: str
  - split_type: str (forward | reverse)
  - old_rate: int
  - new_rate: int
  - effective_date: date
  - positions_adjusted: int
  - adjustments_json: JSON (per-position before/after for audit)
  - created_at (from BaseModel)

Indexes:
  INDEX (symbol, effective_date)
```

### 2. Snapshot Manager (backend/app/portfolio/snapshots.py)

```python
class SnapshotManager:
    """Creates and queries portfolio snapshots."""
    
    async def take_snapshot(self, db, user_id: UUID,
                            snapshot_type: str) -> PortfolioSnapshot:
        """Capture current portfolio state.
        
        Gathers: equity, cash, positions_value, unrealized_pnl,
        realized_pnl_today/total, dividend_income_today/total,
        drawdown_percent, peak_equity, open_positions_count.
        """
    
    async def start_periodic(self) -> None:
        """Start background task for periodic snapshots.
        Interval: PORTFOLIO_SNAPSHOT_INTERVAL_SEC (default 300).
        """
    
    async def stop_periodic(self) -> None:
        """Stop periodic snapshot task."""
    
    async def take_daily_close_snapshot(self, db, user_id: UUID) -> PortfolioSnapshot:
        """Take a daily close snapshot. Called at market close."""
    
    async def get_equity_curve(self, db, user_id: UUID,
                               start: datetime | None = None,
                               end: datetime | None = None,
                               snapshot_type: str = "periodic"
                               ) -> list[dict]:
        """Return equity time series for charting.
        Returns: [{"ts": datetime, "equity": Decimal}, ...]
        """
    
    async def get_snapshots(self, db, user_id: UUID,
                            snapshot_type: str | None = None,
                            start: datetime | None = None,
                            end: datetime | None = None,
                            page: int = 1, page_size: int = 50
                            ) -> tuple[list[PortfolioSnapshot], int]:
        """Query snapshots with filters."""
```

### 3. Wire Event Snapshots into Fill Processing

Update backend/app/portfolio/fill_processor.py:

After processing any fill (entry, scale-in, scale-out, exit), take an
event snapshot:

```python
# At end of process_fill():
snapshot_mgr = get_snapshot_manager()
if snapshot_mgr:
    await snapshot_mgr.take_snapshot(db, user_id, "event")
```

### 4. Realized PnL Ledger (backend/app/portfolio/pnl.py)

```python
class PnlLedger:
    """Manages the append-only realized PnL ledger."""
    
    async def record_close(self, db, position: Position,
                           fill: 'PaperFill', exit_price: Decimal,
                           qty_closed: Decimal, gross_pnl: Decimal,
                           fees: Decimal, net_pnl: Decimal) -> RealizedPnlEntry:
        """Record a realized PnL entry when a position is partially or fully closed.
        
        Called by FillProcessor during scale-out and full exit.
        """
    
    async def get_entries(self, db, user_id: UUID,
                          strategy_id: UUID | None = None,
                          symbol: str | None = None,
                          start: datetime | None = None,
                          end: datetime | None = None,
                          page: int = 1, page_size: int = 50
                          ) -> tuple[list[RealizedPnlEntry], int]:
        """Query PnL entries with filters."""
    
    async def get_summary(self, db, user_id: UUID,
                          strategy_id: UUID | None = None) -> dict:
        """PnL summary.
        Returns: {
            today, this_week, this_month, total,
            by_strategy: {id: {total, count}},
            by_symbol: {symbol: {total, count}}
        }
        """
    
    async def get_daily_loss(self, db, user_id: UUID) -> Decimal:
        """Sum of negative net_pnl entries closed today.
        Replaces the approximate daily loss from TASK-013a.
        """
```

### 5. Wire PnL Ledger into Fill Processor

Update backend/app/portfolio/fill_processor.py:

In _process_scale_out() and _process_full_exit(), after calculating
realized PnL, create a RealizedPnlEntry:

```python
pnl_ledger = get_pnl_ledger()
if pnl_ledger:
    await pnl_ledger.record_close(db, position, fill, exit_price,
                                   qty_closed, gross_pnl, fees, net_pnl)
```

### 6. Dividend Processor (backend/app/portfolio/dividends.py)

```python
class DividendProcessor:
    """Processes dividend payments for held positions."""
    
    async def process_ex_date(self, db, user_id: UUID) -> list[DividendPayment]:
        """Check for ex-dates today and create pending dividend payments.
        
        1. Query dividend_announcements where ex_date = today
        2. For each, find open positions in that symbol held by user
        3. Create DividendPayment with status='pending',
           shares_held = position.qty, amount = qty * amount_per_share
        4. Return created payments
        """
    
    async def process_payable_date(self, db, user_id: UUID) -> list[DividendPayment]:
        """Process pending dividends where payable_date = today.
        
        1. Query pending DividendPayments where payable_date <= today
        2. For each:
           a. Credit cash to the correct account scope
           b. Update position.total_dividends_received
           c. Set payment status='paid', paid_at=now()
        3. Return processed payments
        """
    
    async def get_upcoming(self, db, user_id: UUID) -> list[dict]:
        """Get upcoming dividends for positions the user holds."""
    
    async def get_payment_history(self, db, user_id: UUID,
                                  page: int = 1, page_size: int = 20
                                  ) -> tuple[list[DividendPayment], int]:
        """Query dividend payment history."""
    
    async def get_income_summary(self, db, user_id: UUID) -> dict:
        """Dividend income summary.
        Returns: {today, this_month, this_year, total, by_symbol}
        """
```

### 7. Stock Split Processor (backend/app/portfolio/splits.py)

```python
class SplitProcessor:
    """Adjusts positions for stock splits."""
    
    async def process_splits(self, db, user_id: UUID) -> list[SplitAdjustment]:
        """Check for splits effective today and adjust positions.
        
        For each split announcement effective today:
        1. Find all open positions in the symbol
        2. Forward split (e.g., 4:1): qty *= 4, avg_entry_price /= 4
        3. Reverse split (e.g., 1:10): qty /= 10, avg_entry_price *= 10
        4. Adjust highest/lowest_price_since_entry
        5. Cost basis unchanged
        6. Create SplitAdjustment audit record
        7. Return adjustments made
        """
```

### 8. Options Lifecycle (backend/app/portfolio/options_lifecycle.py)

```python
class OptionsLifecycle:
    """Handles options expiration."""
    
    async def check_expirations(self, db, user_id: UUID) -> list[dict]:
        """Check for expiring options positions at daily close.
        
        For each open option position where expiration_date <= today:
        1. Get underlying price
        2. Calculate intrinsic value:
           - call: max(0, underlying - strike)
           - put: max(0, strike - underlying)
        3. If intrinsic > 0 (ITM):
           - Close at intrinsic value per contract
           - close_reason = "expiration"
        4. If intrinsic == 0 (OTM):
           - Close at zero
           - close_reason = "expiration"
           - realized_pnl = -cost_basis (total loss)
        5. Create RealizedPnlEntry
        6. Return list of expired positions
        """
```

### 9. Performance Metrics (backend/app/portfolio/metrics.py)

```python
class PerformanceMetrics:
    """Calculates trading performance metrics on demand."""
    
    async def calculate(self, db, user_id: UUID,
                        strategy_id: UUID | None = None) -> dict:
        """Calculate all performance metrics.
        
        Returns: {
            total_return: Decimal,
            total_return_percent: Decimal,
            total_pnl: Decimal,
            win_rate: Decimal,
            profit_factor: Decimal,
            average_winner: Decimal,
            average_loser: Decimal,
            risk_reward_ratio: Decimal,
            max_drawdown: Decimal,
            sharpe_ratio: Decimal,
            sortino_ratio: Decimal,
            average_hold_bars: Decimal,
            longest_win_streak: int,
            longest_loss_streak: int,
            total_trades: int,
            winning_trades: int,
            losing_trades: int,
            total_fees: Decimal,
            total_dividend_income: Decimal
        }
        """
    
    async def _calculate_sharpe(self, db, user_id: UUID,
                                risk_free_rate: Decimal) -> Decimal | None:
        """Sharpe ratio from daily close snapshots.
        (avg_daily_return - risk_free_rate) / std_dev(daily_returns)
        Returns None if insufficient data.
        """
    
    async def _calculate_sortino(self, db, user_id: UUID,
                                 risk_free_rate: Decimal) -> Decimal | None:
        """Sortino ratio — like Sharpe but only downside deviation."""
    
    async def _calculate_max_drawdown(self, db, user_id: UUID) -> Decimal:
        """Max peak-to-trough decline from snapshot time series."""
    
    async def _calculate_streaks(self, entries: list) -> tuple[int, int]:
        """Longest win and loss streaks from PnL entries."""
```

### 10. Daily Corporate Actions Job (backend/app/portfolio/daily_jobs.py)

```python
class DailyPortfolioJobs:
    """Runs daily portfolio maintenance tasks.
    
    Should be triggered once per day (at market close or via schedule).
    For MVP, runs as a check in the snapshot periodic loop when a new
    trading day is detected.
    """
    
    async def run_daily(self, db, user_id: UUID) -> dict:
        """Run all daily jobs.
        
        1. Process ex-date dividends (create pending payments)
        2. Process payable-date dividends (credit cash)
        3. Process stock splits
        4. Check options expirations
        5. Take daily close snapshot
        6. Return summary of actions taken
        """
```

### 11. Update Portfolio Service

Add methods to backend/app/portfolio/service.py:

```python
# Snapshots
async def get_equity_curve(self, db, user_id, start=None, end=None) -> list[dict]
async def get_snapshots(self, db, user_id, **filters) -> tuple[list, int]

# PnL
async def get_pnl_entries(self, db, user_id, **filters) -> tuple[list, int]
async def get_pnl_summary(self, db, user_id, strategy_id=None) -> dict

# Dividends
async def get_dividend_payments(self, db, user_id, **filters) -> tuple[list, int]
async def get_upcoming_dividends(self, db, user_id) -> list[dict]
async def get_dividend_summary(self, db, user_id) -> dict

# Metrics
async def get_metrics(self, db, user_id, strategy_id=None) -> dict

# Admin
async def reset_peak_equity(self, db, user_id, admin_user: str) -> None
async def adjust_cash(self, db, user_id, account_scope: str,
                      amount: Decimal, reason: str, admin_user: str) -> CashBalance
```

### 12. Update Portfolio Router

Add endpoints to backend/app/portfolio/router.py:

```
# Snapshots and History
GET  /api/v1/portfolio/snapshots              → snapshot time series (filtered)
GET  /api/v1/portfolio/equity-curve           → equity values over time

# PnL
GET  /api/v1/portfolio/pnl/realized           → realized PnL entries (filtered)
GET  /api/v1/portfolio/pnl/summary            → PnL summary (today, week, month, total)

# Dividends
GET  /api/v1/portfolio/dividends              → dividend payment history
GET  /api/v1/portfolio/dividends/upcoming     → upcoming dividends for held positions
GET  /api/v1/portfolio/dividends/summary      → dividend income summary

# Performance Metrics
GET  /api/v1/portfolio/metrics                → full metrics (portfolio-wide)
GET  /api/v1/portfolio/metrics/:strategy_id   → per-strategy metrics

# Admin
POST /api/v1/portfolio/drawdown/reset-peak    → reset peak equity (admin only)
POST /api/v1/portfolio/cash/adjust            → manual cash adjustment (admin only)
```

All require auth, ownership enforced, envelope + camelCase.
Admin endpoints require require_admin.

### 13. Update Portfolio Startup

Start the snapshot periodic task and daily jobs check.
Wire PnL ledger and snapshot manager as available singletons.

### 14. Alembic Migration

Create migration for the four new tables.

---

## Acceptance Criteria

### Models and Migration
1. PortfolioSnapshot model exists with all fields, all Numeric
2. RealizedPnlEntry model exists as append-only with all fields
3. DividendPayment model exists with all fields
4. SplitAdjustment model exists with adjustments_json (JSON)
5. Alembic migration creates all four tables and applies cleanly

### Snapshots
6. Periodic snapshots run every SNAPSHOT_INTERVAL_SEC
7. Event snapshots taken after every fill
8. Daily close snapshots can be triggered
9. Snapshots capture equity, cash, PnL, drawdown, positions count
10. Equity curve query returns time series for charting

### Realized PnL Ledger
11. PnL entry created on scale-out (partial close)
12. PnL entry created on full exit
13. Entries are append-only (never modified)
14. PnL summary provides today, week, month, total breakdowns
15. Daily loss calculation uses PnL ledger (more accurate than TASK-013a)

### Dividends
16. Ex-date processing creates pending dividend payments for held positions
17. Payable-date processing credits cash and updates position dividends_received
18. Dividend income tracked separately from price PnL (no cost basis adjustment)
19. Upcoming dividends query shows what's coming for held positions
20. Dividend income summary provides totals by period and symbol

### Stock Splits
21. Forward splits multiply qty and divide avg_entry_price
22. Reverse splits divide qty and multiply avg_entry_price
23. Cost basis unchanged after split
24. SplitAdjustment audit record created with before/after details

### Options Expiration
25. ITM options close at intrinsic value
26. OTM options expire worthless (realized_pnl = -cost_basis)
27. Close reason set to "expiration"
28. Expiration check runs daily

### Performance Metrics
29. Total return includes realized + unrealized + dividends
30. Win rate calculated from PnL entries (net_pnl > 0 = win)
31. Profit factor = sum(winners) / abs(sum(losers))
32. Sharpe ratio calculated from daily close snapshots
33. Sortino ratio uses downside deviation only
34. Max drawdown calculated from snapshot time series
35. Win/loss streaks calculated from consecutive PnL entries
36. Metrics available portfolio-wide and per-strategy

### API
37. GET /portfolio/snapshots returns filtered snapshot list
38. GET /portfolio/equity-curve returns time series
39. GET /portfolio/pnl/realized returns PnL entries
40. GET /portfolio/pnl/summary returns PnL breakdown
41. GET /portfolio/dividends returns payment history
42. GET /portfolio/dividends/upcoming returns upcoming dividends
43. GET /portfolio/dividends/summary returns income summary
44. GET /portfolio/metrics returns full performance metrics
45. GET /portfolio/metrics/:strategy_id returns per-strategy metrics
46. POST /portfolio/drawdown/reset-peak works (admin only)
47. POST /portfolio/cash/adjust works (admin only)
48. All responses use {"data": ...} envelope with camelCase

### General
49. Event snapshots wired into fill processor
50. PnL ledger wired into fill processor (scale-out and exit)
51. Startup initializes snapshot manager and daily jobs
52. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-013b-portfolio-analytics/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
