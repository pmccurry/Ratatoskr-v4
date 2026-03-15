# TASK-041c — Fix Strategy Detail Page Crash (profitFactor null guard)

## Goal

Fix the crash on the Strategy Detail page: `_.profitFactor.toFixed is not a function`. The page crashes because backtest metrics components try to call `.toFixed()` on null/undefined values when no backtest has been run yet.

## Problem

When viewing a strategy that has no backtest results:
1. Navigate to Strategies → click on a strategy → page crashes
2. Error: `_.profitFactor.toFixed is not a function`
3. The ErrorBoundary catches it and shows "Something went wrong loading this page"
4. This blocks access to the Backtest tab (which is on this page)

## Fix

Search all backtest-related frontend components for `.toFixed()` calls and add null guards:

```bash
grep -rn "\.toFixed\|\.toLocaleString\|\.toPrecision" frontend/src/features/backtesting/
```

Every `.toFixed()` call on a metrics value needs a null/undefined guard:

```typescript
// BEFORE (crashes when profitFactor is null/undefined/Infinity):
metrics.profitFactor.toFixed(2)

// AFTER:
(metrics?.profitFactor ?? 0).toFixed(2)
// Or for Infinity:
Number.isFinite(metrics?.profitFactor) ? metrics.profitFactor.toFixed(2) : '—'
```

**Check these files specifically:**
- `BacktestMetricsCards.tsx` — likely source (renders 6 metric cards)
- `BacktestResultsList.tsx` — renders metrics in the results table
- `BacktestDetail.tsx` — renders the detail header

**Also check:** Does the `BacktestResultsList` component render on the strategy detail page even when there are 0 backtests? If so, ensure it handles an empty list without trying to format null metrics.

**The profitFactor edge case:** When there are 0 losing trades, profit factor = Infinity. `Infinity.toFixed(2)` throws. Handle this:

```typescript
const formatPF = (pf: number | null | undefined) => {
  if (pf == null || !Number.isFinite(pf)) return '—';
  return pf.toFixed(2);
};
```

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Strategy detail page loads without crash when no backtests exist |
| AC2 | Strategy detail page loads without crash when backtests exist with Infinity profit factor |
| AC3 | Backtest tab is visible and accessible on the strategy detail page |
| AC4 | All `.toFixed()` calls on metrics have null/undefined/Infinity guards |
| AC5 | No backend code modified |
| AC6 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |
