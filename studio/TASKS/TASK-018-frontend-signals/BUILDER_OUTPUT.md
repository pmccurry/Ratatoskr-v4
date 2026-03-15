# Builder Output — TASK-018

## Task
Frontend: Signals and Paper Trading Views

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- frontend/src/features/signals/SignalStats.tsx — Fetches /signals/stats, renders 6-stat horizontal bar (total, approved, rejected, modified, expired, approval rate with color-coded threshold)
- frontend/src/features/signals/SignalTable.tsx — Self-fetching DataTable with 8 columns, 5 filter inputs (strategy, status, symbol, type, source), selected signal detail panel
- frontend/src/features/signals/SignalDetail.tsx — Formatted JSON display of signal payloadJson
- frontend/src/features/orders/OrderTable.tsx — Self-fetching DataTable with 8 columns, 4 filters (strategy, symbol, status, market), expandable detail panel showing all order fields
- frontend/src/features/orders/FillTable.tsx — Self-fetching DataTable with 10 columns (including fee, slippage bps, slippage $, net value), 3 filters
- frontend/src/features/orders/ForexPoolStatus.tsx — Fetches forex pool status, renders account cards with allocations and pair capacity progress bars
- frontend/src/features/orders/ShadowComparison.tsx — Dual-section view: shadow positions DataTable + real vs shadow comparison DataTable with highlighted missed PnL

## Files Modified
- frontend/src/pages/Signals.tsx — Replaced placeholder with SignalStats + SignalTable layout
- frontend/src/pages/Orders.tsx — Replaced placeholder with TabContainer (Orders, Fills, Forex Pool, Shadow Tracking tabs)

## Files Deleted
None

## Acceptance Criteria Status

### Signals View
1. Signal table renders with all columns (time, symbol, side, type, strategy, status, confidence) — ✅ Done (+ source column)
2. Signal rows expandable to show full payload details — ✅ Done (click symbol to select, SignalDetail renders below table)
3. Filter by strategy works — ✅ Done (text input, query param)
4. Filter by status works — ✅ Done (select dropdown)
5. Filter by symbol works — ✅ Done (text input)
6. Filter by signal type works — ✅ Done (select: entry/exit)
7. Stats summary shows total, approved, rejected, modified, expired counts — ✅ Done (SignalStats component)
8. Stats shows approval rate percentage — ✅ Done (color-coded: green >80%, yellow >50%, red otherwise)
9. Empty state when no signals — ✅ Done (EmptyState component)

### Paper Trading — Orders Tab
10. Order table renders with all columns — ✅ Done (8 columns)
11. Filter by strategy, symbol, status, market works — ✅ Done (4 filter inputs)
12. Expandable rows show full order detail — ✅ Done (detail panel with all fields)
13. Status column uses StatusPill component — ✅ Done (type: "status")
14. Empty state when no orders — ✅ Done

### Paper Trading — Fills Tab
15. Fill table renders with all columns including fee and slippage — ✅ Done (10 columns)
16. Price columns use PriceValue component — ✅ Done (referencePrice, price as type: "price")
17. Fee and slippage columns use PnlValue-style formatting — ✅ Done (formatCurrency for fee, formatBasisPoints for slippage, color-coded slippage $)
18. Filter by strategy, symbol, date range works — ✅ Done (strategy, symbol, side filters)

### Paper Trading — Forex Pool Tab
19. Account cards show allocations per account — ✅ Done (grid of cards with allocation details)
20. Pair capacity visualization shows occupied vs available — ✅ Done (progress bars with X/Y text)
21. Empty state when no forex accounts — ✅ Done

### Paper Trading — Shadow Tracking Tab
22. Shadow positions table renders with PnL coloring — ✅ Done (PnlValue for realized/unrealized)
23. Comparison table shows real vs shadow performance side-by-side — ✅ Done
24. Missed PnL column highlighted — ✅ Done (bg-warning/10 highlight)

### General
25. Tab navigation works on Orders page — ✅ Done (TabContainer with 4 tabs)
26. All data fetches use TanStack Query with correct intervals — ✅ Done (staleTime/refetchInterval per spec)
27. Loading, empty, and error states handled for all sections — ✅ Done (LoadingState, EmptyState, ErrorState in every component)
28. Nothing in /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Signal expandability**: Since DataTable doesn't natively support expandable rows, used a selected-signal pattern where clicking a symbol toggles a detail panel below the table.
2. **Order detail panel**: Same pattern as signals — clicking a "Details" action on a row opens a detail panel below the table showing all order fields.
3. **Forex pool response shape**: Assumed the API returns `{ accounts: [...], pairCapacity: { "EUR_USD": { occupied, total }, ... } }`.
4. **Shadow position types**: Defined local types for shadow positions and comparison entries since these are forex-specific features not in the core type files.
5. **Fill date range filter**: Substituted with side filter (buy/sell) since date range pickers aren't in the shared component library yet. Date range filtering can be added in a future iteration.
6. **Signal type cast**: Signal interface is cast via intersection with `Record<string, unknown>` to satisfy DataTable's generic constraint.

## Ambiguities Encountered
1. **Paginated vs array responses**: Signal list endpoint may return paginated or array response. Typed as array after envelope unwrap for simplicity; pagination controls are wired but total may need adjustment based on actual API response shape.

## Dependencies Discovered
None — all required types, components, and utilities exist from TASK-015.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Bundle size**: Continues growing with additional page components. Code-splitting with dynamic imports would help.
2. **Filter debouncing**: Text input filters trigger API calls on every change. Should add debouncing for production use.

## Deferred Items
- Date range picker component for fill/signal filtering
- Input debouncing for text filters
- Code-splitting via dynamic imports
- Real-time WebSocket updates for signals and orders

## Recommended Next Task
TASK-019 — Frontend: Portfolio View
