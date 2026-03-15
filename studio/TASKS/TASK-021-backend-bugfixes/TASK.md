# TASK-021 — Backend Bug Fixes

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Fix all known backend bugs identified during the build validation cycle.
These bugs were flagged by the Validator or Builder during TASK-010 through
TASK-013b but deferred to Phase 4 hardening.

After this task:
- All 8 backend bugs are fixed
- No new features are added
- No architecture changes
- Each fix is minimal and targeted

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. This task file (the bug descriptions below ARE the spec)

## Constraints

- Fix ONLY the listed bugs — no feature additions, no refactoring
- Do NOT modify any frontend code
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Each fix should be the minimum change needed
- If a fix requires touching multiple files, list all of them

---

## Bug Fixes

### FIX-B1 (MAJOR): Options expiration PnL entry records qty_closed=0

**Module:** portfolio
**File:** backend/app/portfolio/options_lifecycle.py
**Problem:** When an option expires, the code zeroes `position.qty` BEFORE
creating the RealizedPnlEntry. The PnL entry then records qty_closed=0,
which makes the entry useless for analytics.

**Root cause:** In fill_processor.py, the pattern is correct — qty is
captured before zeroing (line ~186). But options_lifecycle.py doesn't
follow the same pattern.

**Fix:** Capture `position.qty` into a local variable BEFORE setting
`position.qty = 0`. Use that captured value for the RealizedPnlEntry's
`qty_closed` field.

**Pseudocode:**
```python
# BEFORE (broken):
position.qty = Decimal("0")
position.status = "closed"
# ... later ...
entry = RealizedPnlEntry(qty_closed=position.qty)  # always 0!

# AFTER (fixed):
qty_at_expiry = position.qty  # capture before zeroing
position.qty = Decimal("0")
position.status = "closed"
# ... later ...
entry = RealizedPnlEntry(qty_closed=qty_at_expiry)  # correct
```

**Verify:** The RealizedPnlEntry created during options expiration has
qty_closed equal to the position's quantity before expiration, not zero.

---

### FIX-B2 (MEDIUM): Signal status updates in paper trading bypass SignalService validation

**Module:** paper_trading
**File:** backend/app/paper_trading/service.py
**Problem:** When an order is filled or rejected, the paper trading service
updates the signal's status directly (e.g., setting "order_filled" or
"order_rejected") without going through SignalService.update_signal_status().
This bypasses the transition validation that ensures only valid status
changes occur.

**Root cause:** The signal statuses "order_filled" and "order_rejected"
weren't in the original valid transitions defined in the signals module.
The paper trading service worked around this by writing directly to the
signal model instead of going through the service.

**Fix:** Two changes needed:

1. In `backend/app/signals/service.py` — add the new valid transitions:
   ```
   risk_approved → order_filled
   risk_approved → order_rejected
   risk_modified → order_filled
   risk_modified → order_rejected
   ```

2. In `backend/app/paper_trading/service.py` — replace direct signal
   status writes with calls to `signal_service.update_signal_status()`.
   Import the signal service via the startup singleton getter.

**Verify:** After a fill, the signal status is updated via SignalService
and the transition is validated. Direct writes to signal.status no longer
exist in paper_trading/service.py.

---

### FIX-B3 (MEDIUM): DrawdownMonitor in-memory fallback alongside DB persistence

**Module:** risk
**File:** backend/app/risk/monitoring/drawdown.py
**Problem:** The DrawdownMonitor was originally built with an in-memory
`_peak_equity` field as a fallback when the portfolio service was stubbed.
Now that the portfolio module exists and persists peak equity to the
PortfolioMeta table, the in-memory fallback is redundant and could
silently use stale data after a restart if the portfolio service is
temporarily unavailable during startup.

**Fix:** Remove the in-memory `_peak_equity` fallback. The monitor should
ALWAYS read peak equity from the portfolio service (which reads from
PortfolioMeta in the database). If the portfolio service is unavailable,
return a "degraded" status with the last known values rather than
falling back to a potentially stale in-memory value.

**Verify:** DrawdownMonitor has no `_peak_equity` instance variable.
All peak equity reads go through the portfolio service. If the portfolio
service is unavailable, the drawdown status shows "degraded" (not a
silently wrong number).

---

### FIX-B4 (MEDIUM): DailyPortfolioJobs not auto-triggered

**Module:** portfolio
**File:** backend/app/portfolio/daily_jobs.py and backend/app/portfolio/startup.py
**Problem:** The DailyPortfolioJobs class exists with a `run_daily()` method,
but nothing calls it automatically. The task spec said "runs as a check in
the snapshot periodic loop when a new trading day is detected," but this
detection logic was not implemented.

**Fix:** Add trading-day detection to the snapshot manager's periodic loop.
Track the last trading day processed. On each periodic cycle, check if
a new trading day has started. If so, run DailyPortfolioJobs.run_daily().

**Implementation:**
```python
# In SnapshotManager._periodic_loop() or a new _daily_check():
class SnapshotManager:
    def __init__(self, ...):
        self._last_daily_run: date | None = None

    async def _check_daily_jobs(self, db, user_id):
        today = date.today()
        if self._last_daily_run != today:
            # Check if market close has occurred (after 4 PM ET for equities)
            if self._is_after_market_close():
                await self._daily_jobs.run_daily(db, user_id)
                self._last_daily_run = today
```

**Verify:** When the periodic snapshot loop runs after market close on a
new trading day, DailyPortfolioJobs.run_daily() is called automatically.
The daily jobs (dividend processing, split adjustment, options expiration,
daily close snapshot) run without manual intervention.

---

### FIX-B5 (MEDIUM): Signal status updates bypass validation (same root as B2)

This is the same issue as B2. The fix for B2 covers this entirely.
No additional work needed — just confirming they're the same bug.

---

### FIX-B6 (LOW): Cash manager buy order check excludes estimated fees

**Module:** paper_trading
**File:** backend/app/paper_trading/cash_manager.py
**Problem:** The `calculate_required_cash()` method computes
`qty * reference_price * contract_multiplier` but does NOT add
the estimated fee to the required cash amount. The spec says
"required_cash = qty * reference_price * contract_multiplier + estimated_fee."

**Fix:** Add estimated fee calculation to `calculate_required_cash()`.
The fee can be estimated using the same FeeModel used during fill
simulation, or a conservative estimate based on the market's fee config.

```python
def calculate_required_cash(self, order, reference_price):
    gross = order.requested_qty * reference_price * order.contract_multiplier
    # Add estimated fee
    estimated_fee = self._estimate_fee(gross, order.market)
    return gross + estimated_fee if order.side == "buy" else Decimal("0")
```

**Verify:** `calculate_required_cash()` for a buy order returns a value
that includes the estimated trading fee, not just the gross order value.

---

### FIX-B7 (LOW): Sortino ratio denominator convention

**Module:** portfolio
**File:** backend/app/portfolio/metrics.py
**Problem:** The Sortino ratio calculation divides by `sqrt(sum(neg²) / N)`
where N is the total count of all returns (positive and negative). Some
implementations use N = count(negative returns only) as the denominator
inside the sqrt. Both are defensible conventions, but the spec says
"downside deviation" which conventionally uses count of ALL returns.

**Fix:** This is actually the correct convention for downside deviation
in the context of the Sortino ratio. No code change needed. Add a
clarifying comment to the Sortino calculation:

```python
# Downside deviation uses ALL returns in the denominator (not just
# negative returns). This is the standard convention for Sortino ratio
# where downside_dev = sqrt(sum(min(0, r-MAR)²) / N) and N = total periods.
```

**Verify:** Comment exists explaining the convention choice.

---

### FIX-B8 (LOW): Exposure checks use estimated position values

**Module:** risk
**File:** backend/app/risk/checks/exposure.py (symbol, strategy, portfolio checks)
**Problem:** Exposure limit checks compute "proposed_value" as
`max_position_size_percent * equity / 100` (an estimate based on the risk
limit) rather than using the actual proposed order value
(`requested_qty * current_price * contract_multiplier`).

**Fix:** Use the actual proposed order value for exposure calculations.
The RiskContext should include the proposed position value computed from
the signal's requested qty and the current market price.

Add to RiskContext:
```python
proposed_position_value: Decimal  # qty * price * multiplier
```

Populate in `_build_context()`:
```python
context.proposed_position_value = (
    signal_qty * context.current_price * contract_multiplier
)
```

Update exposure checks to use `context.proposed_position_value` instead
of estimating from the percentage limit.

**Verify:** Per-symbol, per-strategy, and portfolio exposure checks use
the actual proposed order value, not an estimate derived from the
position size limit.

---

## Acceptance Criteria

1. FIX-B1: Options expiration PnL entry has correct qty_closed (not zero)
2. FIX-B2: Paper trading updates signal status through SignalService (not direct write)
3. FIX-B2: Signal module accepts transitions: risk_approved/risk_modified → order_filled/order_rejected
4. FIX-B3: DrawdownMonitor reads peak equity from portfolio service only (no in-memory fallback)
5. FIX-B3: DrawdownMonitor returns "degraded" status if portfolio service unavailable
6. FIX-B4: DailyPortfolioJobs runs automatically after market close on new trading days
7. FIX-B4: Trading day detection integrated into snapshot periodic loop
8. FIX-B6: Cash manager includes estimated fee in required cash for buy orders
9. FIX-B7: Sortino ratio has clarifying comment about denominator convention
10. FIX-B8: Exposure checks use actual proposed position value (not estimated from limit)
11. FIX-B8: RiskContext includes proposed_position_value field
12. No new features or modules created
13. No frontend code modified
14. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-021-backend-bugfixes/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
