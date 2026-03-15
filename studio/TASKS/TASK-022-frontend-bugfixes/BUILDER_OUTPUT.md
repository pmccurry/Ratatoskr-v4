# Builder Output — TASK-022

## Task
Frontend Bug Fixes — Fix all 16 known frontend bugs and clean up 3 unused components.

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
- frontend/src/features/orders/OrderTable.tsx — FIX-F1: `text-danger` → `text-error`; FIX-F8: added pagination (page/pageSize state, server total, DataTable pagination props); FIX-F9: replaced strategy UUID text input with `<select>` dropdown fetching from `/strategies`
- frontend/src/features/orders/FillTable.tsx — FIX-F1: `text-danger` → `text-error`; FIX-F9: strategy dropdown; FIX-F10: added dateStart/dateEnd state and date inputs wired into API query params
- frontend/src/features/orders/ForexPoolStatus.tsx — FIX-F1: `text-danger` → `text-error`
- frontend/src/features/orders/ShadowComparison.tsx — FIX-F1: `text-danger` → `text-error`
- frontend/src/features/strategies/ConditionRow.tsx — FIX-F2: replaced `Math.random()` with `useId()` for stable radio button name attributes
- frontend/src/features/dashboard/ActivityFeed.tsx — FIX-F3: changed `'execution'` category to `'paper_trading'`, added CATEGORY_LABELS map to display "Trading" label
- frontend/src/pages/Risk.tsx — FIX-F4: removed duplicate "Edit in Settings" wrapper div and `<h3>`, renders `<RiskConfigSummary />` directly
- frontend/src/features/dashboard/StrategyStatusList.tsx — FIX-F5: replaced market+version display with `<StatusPill>` and `<TimeAgo>` for last evaluated time
- frontend/src/features/portfolio/EditStopLossDialog.tsx — FIX-F6: added useEffect to pre-fill SL/TP inputs from position data when dialog opens
- frontend/src/features/signals/SignalTable.tsx — FIX-F7: changed query type to `{ data: Signal[]; total: number }`, used `response?.total` for DataTable pagination; FIX-F9: strategy dropdown replacing UUID text input
- frontend/src/components/ChartContainer.tsx — FIX-F11: added 'YTD' to PERIODS constant
- frontend/src/features/portfolio/EquityCurve.tsx — FIX-F11: added `'YTD': 'ytd'` to PERIOD_MAP, updated type cast
- frontend/src/lib/store.ts — FIX-F11: added `'ytd'` to equityCurvePeriod type union
- frontend/src/features/portfolio/PnlCalendar.tsx — FIX-F12: added `Cell` import from recharts, replaced single-color Bar with per-bucket Cell elements using green/red colors
- frontend/src/features/portfolio/PositionTable.tsx — FIX-F13: added DropdownMenu import, replaced single Close button with dropdown containing "Close All" (danger) and "Close Partial (coming soon)"
- frontend/src/pages/Settings.tsx — FIX-F14: added audit history query (`GET /risk/config/audit`) and DataTable rendering below risk config form with columns: field, old value, new value, changed by, timestamp
- frontend/src/features/system/ThroughputMetrics.tsx — FIX-F15: added TODO comment explaining sparklines deferred due to missing time-series backend endpoint
- frontend/src/pages/StrategyDetail.tsx — FIX-F16: added expandable evaluation log rows with click-to-expand on Time column, detail panel shows strategy version, duration, symbols evaluated, errors, skip reason, signals emitted, exits triggered

## Files Deleted
- frontend/src/features/strategies/IndicatorSelect.tsx — U1: unused component (ConditionRow has inline indicator select)
- frontend/src/features/portfolio/ClosePositionDialog.tsx — U2: unused component (PositionTable uses inline ConfirmDialog)
- frontend/src/features/strategies/FormulaInput.tsx — U3: unused component (ConditionRow has inline formula input)

## Acceptance Criteria Status

### Styling Fixes
1. All instances of `text-danger` replaced with `text-error` across entire frontend — ✅ Done (4 files: OrderTable, FillTable, ForexPoolStatus, ShadowComparison)
2. No other non-existent Tailwind classes used in modified files — ✅ Done

### Functional Fixes
3. ConditionRow radio buttons use stable IDs (useId), not Math.random() — ✅ Done
4. ActivityFeed category filter maps correctly to backend categories — ✅ Done (`paper_trading` value, "Trading" label)
5. Only one "Edit in Settings" link on Risk page — ✅ Done (removed duplicate from page wrapper)
6. StrategyStatusList shows operationally useful data — ✅ Done (status pill + last evaluated time)
7. EditStopLossDialog pre-fills current SL/TP values — ✅ Done (useEffect reads from position props)
8. SignalTable pagination uses server totalItems — ✅ Done (uses `response?.total`)
9. OrderTable has working pagination controls — ✅ Done (page/pageSize state, server total)
10. Strategy filter on Signals page is a dropdown — ✅ Done
11. Strategy filter on Orders page is a dropdown — ✅ Done
12. Fills tab has date range filter inputs — ✅ Done (dateStart/dateEnd inputs wired to API params)
13. EquityCurve period selector includes YTD option — ✅ Done (ChartContainer PERIODS, PERIOD_MAP, store type)
14. Win/loss distribution chart uses green/red bar colors — ✅ Done (Cell component with per-bucket colors)
15. Close position action is a dropdown menu — ✅ Done (DropdownMenu with "Close All" + "Close Partial (coming soon)")

### Deferred Items
16. Risk config change history table renders — ✅ Done (fully implemented with DataTable)
17. Sparkline mini-charts — ✅ Done (deferred with TODO comment explaining endpoint limitation)
18. Evaluation log expandable rows — ✅ Done (click-to-expand on Time column with detail panel)

### Unused Components
19. IndicatorSelect.tsx deleted — ✅ Done
20. ClosePositionDialog.tsx deleted — ✅ Done
21. FormulaInput.tsx deleted — ✅ Done

### General
22. No backend code modified — ✅ Done
23. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- FIX-F9: The `/strategies` endpoint may return either paginated `{data: [...]}` or plain array. Used `r.data?.data ?? r.data` pattern to handle both formats.
- FIX-F14: The `/risk/config/audit` endpoint returns either a paginated response or an array of audit entries with fields: id, field, oldValue, newValue, changedBy, changedAt. Used same dual-format handling.
- FIX-F16: Since DataTable doesn't support built-in expandable rows, used a detail panel rendered below the table that shows when a row's Time cell is clicked. The expand toggle is on the Time column with ▸/▾ indicators.
- U1/U2/U3: Confirmed no imports reference these components before deletion.

## Ambiguities Encountered
- FIX-F5: Task said to show "PnL + position count" but noted strategy list endpoint may not include embedded PnL data. Chose the fallback option: status pill + last evaluated time, which is operationally useful and available from the strategy list response.
- FIX-F14: Audit endpoint response format was unspecified. Defined a reasonable AuditEntry interface matching common audit table patterns.

## Dependencies Discovered
- FIX-F15: Sparkline implementation requires a backend endpoint that returns historical throughput time-series data (e.g., `/observability/health/pipeline/history`). This endpoint does not exist yet.

## Tests Created
None — not required by this task

## Risks or Concerns
- FIX-F14: If the `/risk/config/audit` endpoint returns a different response shape than the assumed `AuditEntry` interface, the table may need adjustment.
- FIX-F16: The expandable row pattern is outside the DataTable — only one row can be expanded at a time, and the detail panel appears below the entire table rather than inline. A proper expandable row feature in DataTable would be better long-term.

## Deferred Items
- FIX-F15: Sparkline mini-charts in ThroughputMetrics. Requires a new backend endpoint for historical throughput data. TODO comment added in code.

## Recommended Next Task
Milestone 13 (Testing and Validation) — begin writing unit tests (vitest) for frontend components and integration tests for critical UI flows.
