# TASK-016 — Frontend: Dashboard Home View

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Replace the Dashboard placeholder with the full dashboard home view:
portfolio stat cards, equity curve chart, strategy status list, and
live activity feed.

## Read First

1. /studio/SPECS/frontend_specs.md — section 5, View 1 (Dashboard Home)
2. Review TASK-015 BUILDER_OUTPUT.md — understand existing components

## Constraints

- Use existing shared components from TASK-015 (StatCard, ChartContainer,
  ActivityFeedItem, CardGrid, etc.)
- Do NOT modify shared components (create feature-specific wrappers)
- Do NOT modify backend code
- Do NOT touch /studio (except BUILDER_OUTPUT.md)
- All data fetched via TanStack Query with refresh intervals from constants

---

## Deliverables

### 1. Dashboard Page (frontend/src/pages/Dashboard.tsx)

Replace placeholder with full layout:

```
Row 1: CardGrid with 4 StatCards
  - Total Equity ($, % return, linked to /portfolio)
  - Today's PnL ($, %, trend arrow)
  - Open Positions (count, linked to /portfolio)
  - Drawdown (%, progress bar vs limit, linked to /risk)

Row 2: Two columns (2/3 + 1/3)
  - Left: EquityCurveChart (30d default, period selector)
  - Right: StrategyStatusList

Row 3: Full width
  - ActivityFeed (recent 20 events, auto-scroll, pause on hover)
```

### 2. Feature Components (frontend/src/features/dashboard/)

**StatCards.tsx** — Fetches portfolio summary, renders 4 StatCards
**EquityCurveChart.tsx** — Fetches equity curve data, renders in ChartContainer with Recharts AreaChart
**StrategyStatusList.tsx** — Fetches strategy list, renders compact cards with status dot, name, PnL, position count. Click → /strategies/:id
**ActivityFeed.tsx** — Fetches recent events, renders ActivityFeedItem list. Auto-scrolls for new events. Pauses on hover. Category/severity filter buttons.

### 3. Data Fetching

```
GET /portfolio/summary        → stat cards (stale: 30s, refetch: 60s)
GET /portfolio/equity-curve   → chart (stale: 60s, refetch: 300s)
GET /strategies               → strategy list (stale: 30s, refetch: 60s)
GET /observability/events/recent → activity feed (stale: 5s, refetch: 10s)
```

---

## Acceptance Criteria

1. Dashboard renders 4 stat cards with real data from portfolio summary API
2. Stat cards show loading skeletons while data loads
3. Equity stat card shows $ value and % return
4. PnL stat card shows $ value with green/red coloring
5. Drawdown card shows progress bar (current vs limit)
6. Equity curve chart renders with real data from equity-curve API
7. Chart has period selector (1D, 7D, 30D, 90D, ALL)
8. Chart uses green area fill for equity line
9. Strategy status list shows all strategies with status dot, name, PnL
10. Strategy items are clickable → navigates to /strategies/:id
11. Activity feed shows recent events with emoji prefixes
12. Activity feed auto-scrolls for new events
13. Activity feed pauses auto-scroll on hover
14. All data fetches use TanStack Query with correct refresh intervals
15. Loading, empty, and error states handled for all sections
16. Nothing in /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

BUILDER_OUTPUT.md at /studio/TASKS/TASK-016-dashboard/BUILDER_OUTPUT.md
