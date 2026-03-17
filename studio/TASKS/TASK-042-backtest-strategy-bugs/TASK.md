# TASK-042 — Backtest & Strategy Builder Bug Fixes

## Goal

Fix all remaining bugs in the strategy builder, backtest engine, and frontend display that prevent the full strategy → backtest → evaluate pipeline from working correctly.

## Depends On

TASK-041d

## Scope

**In scope:**
- Strategy builder condition UI: right-side indicator missing params
- Backtest fixed quantity sizing producing 0 trades
- Strategy disable/delete not working (422 errors)
- Config tab crash ("Cannot read properties of undefined (reading 'length')")
- Backtest form should pre-fill exit rules from strategy's risk management config
- Portfolio metrics Decimal serialized as strings (profitFactor root cause)
- Equity curve display issues on 0-trade backtests

**Out of scope:**
- New features
- Dev workflow documentation
- New strategy types or indicators

---

## Bug Fixes

### BF-1 — Right-side indicator missing parameter inputs

**Problem:** When setting up a condition like `SMA(20) crosses_above SMA(50)`, the right side only shows "Simple Moving Average" with no way to set the period or source. The user can toggle to "Indicator" and select the indicator type, but the parameter fields (period, source) don't render.

**Where to look:** The condition row component in the strategy builder — likely `frontend/src/features/strategies/ConditionRow.tsx` or `ConditionBuilder.tsx` or similar. The right-side indicator section needs the same parameter inputs as the left side.

**Fix:** When the right side is set to "Indicator" mode, render period and source inputs identical to the left side. The condition should produce:

```json
{
  "left": { "type": "indicator", "indicator": "sma", "params": { "period": 20, "source": "close" } },
  "operator": "crosses_above",
  "right": { "type": "indicator", "indicator": "sma", "params": { "period": 50, "source": "close" } }
}
```

Currently the right side produces:
```json
{ "type": "indicator", "indicator": "sma" }
```
Missing `params`.

### BF-2 — Fixed quantity backtest produces 0 trades

**Problem:** Backtest with position sizing type "fixed" and amount 10,000 produces 0 trades. The same strategy with "percent_equity" sizing works and produces 6 trades.

**Root cause investigation:**

1. Check the sizing type string mapping. The backtest form sends a `type` value — verify it matches what `backend/app/backtesting/sizing.py` expects:
   - Form might send: `"fixed"`, `"fixed_qty"`, or `"fixed_units"`
   - Backend expects: check `calculate_size()` function for the exact string

2. Check if the fixed sizing returns 0 or raises an error silently. Add logging:
   ```python
   logger.info(f"Position sizing: type={sizing_type}, result={quantity}")
   ```

3. Check if cash check rejects the trade. Fixed 10,000 units × EUR_USD price (~1.08) = $10,800. With $100K capital this should be fine, but verify the cash deduction logic isn't comparing units vs dollars incorrectly.

**Fix:** Ensure the sizing type string matches between frontend and backend, and that the fixed sizing calculation returns a non-zero Decimal.

### BF-3 — Can't disable strategies (422 error)

**Problem:** Clicking "Disable" on a strategy returns 422. The endpoint is `PUT /api/v1/strategies/{id}/disable`.

**Root cause investigation:**

1. Check what the frontend sends in the request body (might be sending empty body or wrong format)
2. Check what the backend schema expects for the disable endpoint
3. The 422 is a Pydantic validation error — check the response body for details

**Fix:** Align the request body with what the backend schema expects. Common issue: endpoint expects `{ "reason": "..." }` but frontend sends nothing, or the endpoint expects a specific content type.

### BF-4 — Can't delete strategies

**Problem:** No delete functionality, or delete button exists but endpoint fails.

**Investigation:**
1. Check if a delete button exists in the UI
2. Check if `DELETE /api/v1/strategies/{id}` endpoint exists in the backend router
3. If endpoint exists but UI doesn't have a button, add one
4. If endpoint doesn't exist, create it (soft delete — set status to "archived" or "deleted")

**Fix:** Ensure delete endpoint exists and UI has a delete option (confirm dialog before deleting). Strategy deletion should:
- Only allow deleting draft strategies (not enabled ones — disable first)
- Soft delete (mark as archived/deleted, don't remove from DB)
- Remove from the strategies list view

### BF-5 — Config tab crash

**Problem:** Config tab on strategy detail page shows: "Cannot read properties of undefined (reading 'length')"

**Root cause:** The config display component tries to read `.length` on a property that's undefined. Likely `conditions.length` where `conditions` is undefined because the config uses camelCase keys but the display component reads snake_case, or a section of the config is missing.

**Fix:** Add null guards to all array `.length` accesses in the config display component. Find the component:
```bash
grep -rn "\.length" frontend/src/features/strategies/ --include="*.tsx" | grep -v node_modules | grep -v __tests__
```

### BF-6 — Backtest form should pre-fill from strategy risk management

**Problem:** The backtest form has its own exit rules section (SL pips, TP pips, signal exit, max hold bars) but doesn't pre-fill from the strategy's risk management config. The user has to re-enter values they already configured.

**Fix:** When the backtest form loads, read the strategy's config and pre-fill:
- `strategy.config.riskManagement.stopLoss.value` → Stop Loss pips field
- `strategy.config.riskManagement.takeProfit.value` → Take Profit pips field
- `strategy.config.riskManagement.maxHoldBars` → Max Hold Bars field

This is a convenience improvement, not a structural change. The user can still override these values for a specific backtest run.

### BF-7 — Portfolio metrics Decimal serialized as strings

**Problem:** The portfolio metrics endpoint (`/portfolio/metrics/{id}` or wherever `PerformanceMetricsResponse` is used) returns Decimal fields as JSON strings (`"1.5"` instead of `1.5`). This caused the `profitFactor.toFixed()` crash.

**Root cause:** `PerformanceMetricsResponse` in `backend/app/portfolio/schemas.py` uses `Decimal` type. Pydantic v2 serializes Decimal as strings in JSON.

**Fix:** Change the response schema's financial display fields from `Decimal` to `float`:
```python
class PerformanceMetricsResponse(BaseSchema):
    profit_factor: float | None = None
    sharpe_ratio: float | None = None
    win_rate: float | None = None
    # ... other display-only metrics
```

This is safe because this is a read-only display endpoint — no arithmetic is done on these values after serialization.

### BF-8 — Equity curve display on 0-trade backtests

**Problem:** When a backtest produces 0 trades, the equity curve chart drops to $0.00 on the Y-axis. It should show a flat line at the initial capital ($100,000).

**Fix options:**

1. **Backend:** When 0 trades, still record equity curve points at the initial capital level (the runner may be skipping equity recording when no trades occur)

2. **Frontend:** Set Y-axis domain minimum to something reasonable:
```tsx
<YAxis 
  yAxisId="equity" 
  domain={[
    (dataMin: number) => Math.max(0, dataMin * 0.95), 
    (dataMax: number) => dataMax * 1.05
  ]} 
/>
```

3. **Frontend:** If equity curve data is empty, show a message "No equity data — no trades were generated" instead of a flat-zero chart.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Right-side indicator in conditions has period and source inputs |
| AC2 | Condition with indicator-vs-indicator comparison saves correctly (e.g., SMA(20) crosses_above SMA(50)) |
| AC3 | Backtest with fixed quantity sizing (10,000 units) produces trades |
| AC4 | All 4 position sizing types produce trades in backtest (fixed, fixed_cash, percent_equity, percent_risk) |
| AC5 | Disable button works on enabled strategies |
| AC6 | Delete functionality exists for draft strategies (with confirmation) |
| AC7 | Config tab loads without crash on all strategies |
| AC8 | Backtest form pre-fills exit rules from strategy's risk management config |
| AC9 | Portfolio metrics endpoint returns numbers (not strings) for display fields |
| AC10 | Equity curve on 0-trade backtest shows flat line at initial capital (not $0) |
| AC11 | No other pages crash or show errors |
| AC12 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Modify

### Frontend
| File | What Changes |
|------|-------------|
| Condition row/builder component | BF-1: Add right-side indicator params (period, source) |
| Strategy detail config tab component | BF-5: Null guards on array .length |
| Backtest form component | BF-6: Pre-fill exit rules from strategy config |
| Equity curve chart component | BF-8: Better Y-axis domain for 0-trade case |
| Strategy detail page | BF-4: Add delete button with confirmation |

### Backend
| File | What Changes |
|------|-------------|
| `backend/app/backtesting/sizing.py` | BF-2: Debug/fix fixed sizing type string and calculation |
| `backend/app/strategies/router.py` | BF-3: Fix disable endpoint (check schema expectations) |
| `backend/app/strategies/router.py` | BF-4: Add delete endpoint if missing |
| `backend/app/portfolio/schemas.py` | BF-7: Change Decimal → float on display metrics |
| `backend/app/backtesting/runner.py` | BF-8: Record equity curve even when 0 trades |

---

## Builder Notes

- **BF-1 is the highest priority** — without right-side indicator params, you can't build proper crossover strategies (SMA vs SMA, EMA vs EMA, RSI vs threshold). This is the most impactful fix.
- **BF-2 debugging:** Add a `logger.info()` inside `calculate_size()` in sizing.py to log the sizing type and result. If the type string doesn't match any case, it returns 0 silently. Log what type string the backtest form sends vs what the function checks for.
- **BF-3/BF-4:** Check the request/response in detail. The 422 on disable might just need an empty JSON body `{}` instead of no body, or the endpoint might expect a specific field.
- **BF-7:** This is the root cause of the profitFactor crash we've been chasing. Changing Decimal → float in the response schema fixes it at the source instead of adding frontend guards everywhere.
- **For BF-4 (delete):** Use soft delete — set a `status = "deleted"` or `is_deleted = True` flag. Don't actually DELETE from the database. Filter deleted strategies from list queries.

## References

- TASK-041 — Backtest UI components
- TASK-041a/b/c — Previous strategy builder fixes
- strategy_module_spec.md — condition engine, indicator library
- cross_cutting_specs.md — API conventions
