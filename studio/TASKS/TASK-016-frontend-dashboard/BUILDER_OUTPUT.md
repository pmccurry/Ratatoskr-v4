# Builder Output — TASK-016

## Task
Frontend: Dashboard Home View

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- frontend/src/features/dashboard/StatCards.tsx — Fetches portfolio summary via TanStack Query, renders 4 StatCards in CardGrid (equity, PnL, open positions, drawdown with progress bar)
- frontend/src/features/dashboard/EquityCurveChart.tsx — Fetches equity curve snapshots, renders Recharts AreaChart in ChartContainer with green gradient fill and period selector synced to Zustand store
- frontend/src/features/dashboard/StrategyStatusList.tsx — Fetches strategy list, renders compact clickable cards with status dot, name, market, version. Click navigates to /strategies/:id
- frontend/src/features/dashboard/ActivityFeed.tsx — Fetches recent events, renders ActivityFeedItem list with auto-scroll, hover pause, severity and category filter buttons

## Files Modified
- frontend/src/pages/Dashboard.tsx — Replaced placeholder with full dashboard layout: StatCards row, 2/3+1/3 grid (EquityCurveChart + StrategyStatusList), full-width ActivityFeed

## Files Deleted
None

## Acceptance Criteria Status

1. Dashboard renders 4 stat cards with real data from portfolio summary API — ✅ Done (StatCards.tsx fetches /portfolio/summary)
2. Stat cards show loading skeletons while data loads — ✅ Done (StatCard loading prop)
3. Equity stat card shows $ value and % return — ✅ Done (formatCurrency + formatPercent subtitle)
4. PnL stat card shows $ value with green/red coloring — ✅ Done (trend up/down)
5. Drawdown card shows progress bar (current vs limit) — ✅ Done (progress prop with threshold at 80% of limit)
6. Equity curve chart renders with real data from equity-curve API — ✅ Done (EquityCurveChart.tsx)
7. Chart has period selector (1D, 7D, 30D, 90D, ALL) — ✅ Done (ChartContainer built-in, synced to Zustand)
8. Chart uses green area fill for equity line — ✅ Done (COLORS.success stroke + gradient fill)
9. Strategy status list shows all strategies with status dot, name, PnL — ✅ Done (StrategyStatusList.tsx)
10. Strategy items are clickable → navigates to /strategies/:id — ✅ Done (useNavigate on click)
11. Activity feed shows recent events with emoji prefixes — ✅ Done (ActivityFeedItem renders summary which includes emoji)
12. Activity feed auto-scrolls for new events — ✅ Done (useEffect scrolls to bottom on data change)
13. Activity feed pauses auto-scroll on hover — ✅ Done (hovered state prevents auto-scroll)
14. All data fetches use TanStack Query with correct refresh intervals — ✅ Done (REFRESH and STALE constants)
15. Loading, empty, and error states handled for all sections — ✅ Done (LoadingState, EmptyState, ErrorState in each component)
16. Nothing in /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Today's PnL**: Used unrealizedPnl + realizedPnlTotal from PortfolioSummary as the combined PnL value. A dedicated "today's PnL" field may be added to the API later.
2. **Drawdown limit**: Fetched from /risk/config (maxDrawdownPercent). Falls back to 10% if the risk config endpoint is unavailable.
3. **Equity curve data**: Expects the /portfolio/equity-curve endpoint to return an array of PortfolioSnapshot objects with `ts` and `equity` fields.
4. **Strategy status dot colors**: Mapped status strings to colors (enabled=green, paused=yellow, disabled/draft=gray, error=red).

## Ambiguities Encountered
1. **Portfolio summary "today's PnL"**: The PortfolioSummary type has unrealizedPnl and realizedPnlTotal but not a dedicated "today's PnL" field. Used the combination as the best available representation.

## Dependencies Discovered
None — all required types, components, and utilities exist from TASK-015.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Bundle size warning**: Recharts adds significant bundle size (chunk >500KB). Future optimization could use dynamic imports to code-split the chart library.
2. **Activity feed filter UX**: The severity + category filter buttons may be crowded on smaller screens. Could be collapsed into dropdowns in a future iteration.

## Deferred Items
- Code-splitting for Recharts to reduce initial bundle
- Real-time WebSocket updates for activity feed (currently polling every 10s)

## Recommended Next Task
TASK-017 — Frontend: Strategy List and Detail Views
