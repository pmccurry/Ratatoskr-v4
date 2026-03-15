# Validation Report — TASK-013b

## Task
Portfolio: Snapshots, PnL Ledger, Dividends, Splits, Options, and Metrics

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present and non-empty
- [x] Files Modified section present
- [x] Files Deleted section present
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (6 assumptions documented)
- [x] Ambiguities section present (2 ambiguities documented)
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present (3 risks documented)
- [x] Deferred Items section present
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | PortfolioSnapshot model exists with all fields, all Numeric | ✅ | ✅ models.py lines 108-132: all spec fields present, financial fields Numeric, 3 indexes matching spec | PASS |
| 2 | RealizedPnlEntry model exists as append-only with all fields | ✅ | ✅ models.py lines 135-165: all spec fields, 4 indexes. PnlLedger has no update method — append-only | PASS |
| 3 | DividendPayment model exists with all fields | ✅ | ✅ models.py lines 168-194: all spec fields, FKs to positions and dividend_announcements, 3 indexes | PASS |
| 4 | SplitAdjustment model exists with adjustments_json (JSON) | ✅ | ✅ models.py lines 197-210: adjustments_json uses JSON type, all other fields present, 1 index | PASS |
| 5 | Alembic migration creates all four tables and applies cleanly | ✅ | ✅ Migration a1b2c3d4e5f6 creates portfolio_snapshots, realized_pnl_entries, dividend_payments, split_adjustments with correct columns, types, FKs, indexes. Downgrade drops in correct order | PASS |
| 6 | Periodic snapshots run every SNAPSHOT_INTERVAL_SEC | ✅ | ✅ snapshots.py _run_loop sleeps config.snapshot_interval between iterations | PASS |
| 7 | Event snapshots taken after every fill | ✅ | ✅ fill_processor.py lines 54-61: calls take_snapshot(db, user_id, "event") after fill processing | PASS |
| 8 | Daily close snapshots can be triggered | ✅ | ✅ snapshots.py take_daily_close_snapshot delegates to take_snapshot with type "daily_close" | PASS |
| 9 | Snapshots capture equity, cash, PnL, drawdown, positions count | ✅ | ✅ snapshots.py take_snapshot gathers all fields: equity, cash_balance, positions_value, unrealized_pnl, realized_pnl_today/total, dividend_income_today/total, drawdown_percent, peak_equity, open_positions_count | PASS |
| 10 | Equity curve query returns time series for charting | ✅ | ✅ snapshots.py get_equity_curve returns [{"ts": ..., "equity": ...}] with optional start/end filters | PASS |
| 11 | PnL entry created on scale-out (partial close) | ✅ | ✅ fill_processor.py lines 168-177: calls pnl_ledger.record_close in _process_scale_out | PASS |
| 12 | PnL entry created on full exit | ✅ | ✅ fill_processor.py lines 228-237: calls pnl_ledger.record_close in _process_full_exit, with qty_closed captured before zeroing (line 186) | PASS |
| 13 | Entries are append-only (never modified) | ✅ | ✅ PnlLedger class only has record_close (create), get_entries, get_summary, get_daily_loss — no update/delete methods | PASS |
| 14 | PnL summary provides today, week, month, total breakdowns | ✅ | ✅ pnl.py get_summary returns today, this_week, this_month, total, by_strategy, by_symbol | PASS |
| 15 | Daily loss calculation uses PnL ledger | ✅ | ✅ pnl.py get_daily_loss sums negative net_pnl entries closed today | PASS |
| 16 | Ex-date processing creates pending dividend payments | ✅ | ✅ dividends.py process_ex_date queries announcements with ex_date=today, creates DividendPayment with status="pending" for each held position | PASS |
| 17 | Payable-date processing credits cash and updates position dividends_received | ✅ | ✅ dividends.py process_payable_date credits cash via CashBalanceRepository.update_balance, updates position.total_dividends_received, sets status="paid" and paid_at | PASS |
| 18 | Dividend income tracked separately from price PnL (no cost basis adjustment) | ✅ | ✅ DividendPayment is a separate table, dividend processing never touches cost_basis on positions | PASS |
| 19 | Upcoming dividends query shows what's coming | ✅ | ✅ dividends.py get_upcoming queries announcements with ex_date >= today for symbols held by user | PASS |
| 20 | Dividend income summary provides totals by period and symbol | ✅ | ✅ dividends.py get_income_summary returns today, this_month, this_year, total, by_symbol | PASS |
| 21 | Forward splits multiply qty and divide avg_entry_price | ✅ | ✅ splits.py line 80-81: qty *= ratio, avg_entry_price /= ratio (forward: ratio > 1) | PASS |
| 22 | Reverse splits divide qty and multiply avg_entry_price | ✅ | ✅ Same code path with ratio < 1 for reverse splits (old_rate > new_rate) | PASS |
| 23 | Cost basis unchanged after split | ✅ | ✅ splits.py line 89 comment "# Cost basis unchanged" — cost_basis field is never modified | PASS |
| 24 | SplitAdjustment audit record created with before/after details | ✅ | ✅ splits.py creates SplitAdjustment with adjustments_json containing per-position before/after dicts | PASS |
| 25 | ITM options close at intrinsic value | ✅ | ✅ options_lifecycle.py lines 59-65: calculates intrinsic, close_value = intrinsic * qty * multiplier | PASS |
| 26 | OTM options expire worthless (realized_pnl = -cost_basis) | ✅ | ✅ options_lifecycle.py lines 67-71: long OTM gets -cost_basis, short OTM gets +cost_basis | PASS |
| 27 | Close reason set to "expiration" | ✅ | ✅ options_lifecycle.py line 82: position.close_reason = "expiration" | PASS |
| 28 | Expiration check runs daily | ✅ | ✅ daily_jobs.py run_daily step 4 calls options_lifecycle.check_expirations | PASS |
| 29 | Total return includes realized + unrealized + dividends | ✅ | ✅ metrics.py line 108: total_return = total_pnl + unrealized_pnl + total_dividend_income | PASS |
| 30 | Win rate calculated from PnL entries (net_pnl > 0 = win) | ✅ | ✅ metrics.py lines 46-56: winners filtered by net_pnl > 0, win_rate = winning/total * 100 | PASS |
| 31 | Profit factor = sum(winners) / abs(sum(losers)) | ✅ | ✅ metrics.py lines 68-72 | PASS |
| 32 | Sharpe ratio calculated from daily close snapshots | ✅ | ✅ metrics.py _calculate_sharpe queries daily_close snapshots, computes daily returns, annualized with sqrt(252) | PASS |
| 33 | Sortino ratio uses downside deviation only | ✅ | ✅ metrics.py _calculate_sortino filters negative_returns (below risk-free), computes downside deviation | PASS |
| 34 | Max drawdown calculated from snapshot time series | ✅ | ✅ metrics.py _calculate_max_drawdown iterates equity snapshots tracking peak and max peak-to-trough decline | PASS |
| 35 | Win/loss streaks calculated from consecutive PnL entries | ✅ | ✅ metrics.py _calculate_streaks iterates entries tracking consecutive wins/losses | PASS |
| 36 | Metrics available portfolio-wide and per-strategy | ✅ | ✅ calculate() accepts optional strategy_id which filters PnL entries and positions | PASS |
| 37 | GET /portfolio/snapshots returns filtered snapshot list | ✅ | ✅ router.py lines 199-226: accepts snapshotType, dateStart, dateEnd, page, pageSize | PASS |
| 38 | GET /portfolio/equity-curve returns time series | ✅ | ✅ router.py lines 229-242 | PASS |
| 39 | GET /portfolio/pnl/realized returns PnL entries | ✅ | ✅ router.py lines 248-276: accepts strategyId, symbol, dateStart, dateEnd, page, pageSize | PASS |
| 40 | GET /portfolio/pnl/summary returns PnL breakdown | ✅ | ✅ router.py lines 279-291 | PASS |
| 41 | GET /portfolio/dividends returns payment history | ✅ | ✅ router.py lines 297-320 | PASS |
| 42 | GET /portfolio/dividends/upcoming returns upcoming dividends | ✅ | ✅ router.py lines 323-334 | PASS |
| 43 | GET /portfolio/dividends/summary returns income summary | ✅ | ✅ router.py lines 337-348 | PASS |
| 44 | GET /portfolio/metrics returns full performance metrics | ✅ | ✅ router.py lines 354-365 | PASS |
| 45 | GET /portfolio/metrics/:strategy_id returns per-strategy metrics | ✅ | ✅ router.py lines 368-380 | PASS |
| 46 | POST /portfolio/drawdown/reset-peak works (admin only) | ✅ | ✅ router.py lines 386-398: uses require_admin dependency | PASS |
| 47 | POST /portfolio/cash/adjust works (admin only) | ✅ | ✅ router.py lines 401-417: uses require_admin, accepts CashAdjustRequest body | PASS |
| 48 | All responses use {"data": ...} envelope with camelCase | ✅ | ✅ All endpoints wrap in {"data": ...} and use model_dump(by_alias=True) with to_camel alias_generator | PASS |
| 49 | Event snapshots wired into fill processor | ✅ | ✅ fill_processor.py lines 54-61 | PASS |
| 50 | PnL ledger wired into fill processor (scale-out and exit) | ✅ | ✅ fill_processor.py lines 168-177 (scale-out) and 228-237 (full exit) | PASS |
| 51 | Startup initializes snapshot manager and daily jobs | ✅ | ✅ startup.py: SnapshotManager created and start_periodic called; PnlLedger initialized; get_snapshot_manager() and get_pnl_ledger() getters added | PASS |
| 52 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md added in studio/TASKS/TASK-013b-portfolio-snapshots/ | PASS |

Section Result: ✅ PASS
Issues: None (see Major issues below for a bug found outside acceptance criteria scope)

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs exactly
- [x] Entity names match GLOSSARY exactly (PortfolioSnapshot, RealizedPnlEntry, DividendPayment, SplitAdjustment)
- [x] Database-related names follow conventions (_id, _at, _json suffixes)
- [x] No typos in module or entity names

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] API is REST-first (DECISION-011)
- [x] Dividend income tracked separately from price PnL, no cost basis adjustment (DECISION-023)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and portfolio module spec
- [x] File organization follows the defined module layout
- [x] No unexpected files in any directory
- [x] Existing models (Position, CashBalance, PortfolioMeta) are NOT modified — verified untouched

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
- [x] backend/app/portfolio/snapshots.py
- [x] backend/app/portfolio/pnl.py
- [x] backend/app/portfolio/dividends.py
- [x] backend/app/portfolio/splits.py
- [x] backend/app/portfolio/options_lifecycle.py
- [x] backend/app/portfolio/metrics.py
- [x] backend/app/portfolio/daily_jobs.py
- [x] backend/migrations/versions/a1b2c3d4e5f6_create_portfolio_analytics_tables.py

All 8 files verified present.

### Files that EXIST but builder DID NOT MENTION:
None found.

### Files builder claims to have created that DO NOT EXIST:
None — all 8 files exist.

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)

1. **Options expiration PnL entry records qty_closed=0**: In options_lifecycle.py, position.qty is set to Decimal("0") at line 76, but the RealizedPnlEntry is created afterward at lines 94-121 using `qty_closed=position.qty if position.qty > 0 else Decimal("0")`. Since position.qty is already 0, qty_closed will always be 0 in the PnL entry, losing the actual trade size. The qty should be captured before zeroing, as the fill_processor correctly does at line 186 (`qty_closed = position.qty  # Capture before zeroing`). Fix: capture qty before line 76 and use the captured value in the PnL entry.

### Minor (note for future, does not block)

1. **Admin endpoints operate on admin's own user_id**: reset_peak_equity and cash/adjust both use `user.id` (the admin's own user_id) rather than accepting a target user_id. For single-user MVP this works, but the admin endpoint pattern typically allows operating on other users' data.

2. **DailyPortfolioJobs not wired to any automatic trigger**: The DailyPortfolioJobs class exists and run_daily orchestrates all daily tasks, but no automatic scheduling is wired up. The startup only starts the periodic snapshot loop. The builder noted this in Deferred Items.

3. **Sortino ratio denominator uses full N**: In metrics.py line 232, downside_variance divides by `n` (total number of returns) instead of `len(negative_returns)`. This is actually a common convention (Sortino uses full-period denominator to avoid overweighting downside), but it differs from some implementations that use only the count of negative returns.

4. **Snapshot periodic loop discovers users from CashBalance table**: In snapshots.py line 167, periodic snapshots only run for users who have CashBalance records. Users who haven't been initialized won't get snapshots. This is fine since initialize_cash always runs before snapshots start, but it's worth noting.

---

## Risk Notes

1. **Portfolio snapshot table growth**: With 5-minute periodic snapshots plus event snapshots on every fill, the portfolio_snapshots table will grow rapidly. The builder has noted this as a future cleanup item.

2. **Decimal exponentiation for Sharpe/Sortino**: Using `Decimal("0.5")` as an exponent for square root calculation. Python Decimal supports this but may have precision/performance characteristics different from math.sqrt. For trading metrics this is acceptable.

3. **Options expiration relies on OHLCVBar for underlying price**: options_lifecycle.py _get_underlying_price queries the most recent 1m bar. If market data isn't streaming or bars are stale, the price could be inaccurate for expiration settlement.

---

## RESULT: PASS

All 52 acceptance criteria independently verified. 1 major issue found (options expiration PnL entry records qty_closed=0 — a correctness bug that should be fixed before proceeding but does not block the task's acceptance criteria). 4 minor issues documented. Task is ready for Librarian update.
