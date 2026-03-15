# Builder Output — TASK-041c

## Task
Fix Strategy Detail Page Crash (profitFactor null guard)

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
None

## Files Modified
- `frontend/src/pages/StrategyDetail.tsx` — Added null guards to 5 metrics values: `profitFactor` (null + Infinity guard), `totalTrades` (null fallback to 0), `riskReward` (null guard), `sharpeRatio` (null guard), `avgHoldBars` (null fallback to 0), `maxDrawdown` (null fallback to 0)
- `frontend/src/features/backtesting/BacktestResultsList.tsx` — Added `isFinite()` guard on sharpe ratio `.toFixed(2)` call

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Strategy detail page loads without crash when no backtests exist — ✅ Done (all `.toFixed()` and `.toLocaleString()` calls guarded)
2. AC2: Strategy detail page loads without crash when backtests exist with Infinity profit factor — ✅ Done (`isFinite()` check on profitFactor)
3. AC3: Backtest tab is visible and accessible on the strategy detail page — ✅ Done (crash was in performance tab, preventing all tabs from rendering)
4. AC4: All `.toFixed()` calls on metrics have null/undefined/Infinity guards — ✅ Done (grep verified: all remaining `.toFixed()` on metrics are guarded)
5. AC5: No backend code modified — ✅ Done
6. AC6: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
None

## Ambiguities Encountered
None

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Risks or Concerns
None identified

## Deferred Items
None — all deliverables complete

## Recommended Next Task
None — this was a targeted bug fix.
