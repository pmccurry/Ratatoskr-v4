# TASK-019 — Frontend: Portfolio View

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Replace the Portfolio placeholder with the complete portfolio view:
positions with inline actions, PnL analysis with calendar heatmap,
equity and drawdown charts, and dividend tracking.

## Read First

1. /studio/SPECS/frontend_specs.md — section 5, View 7
2. Review TASK-015 BUILDER_OUTPUT.md — existing components and types

## Constraints

- Use existing shared components from TASK-015
- Do NOT modify backend code
- Do NOT touch /studio (except BUILDER_OUTPUT.md)

---

## Deliverables

### 1. Portfolio Page (frontend/src/pages/Portfolio.tsx)

**Tabs:** [Positions] [PnL Analysis] [Equity] [Dividends]

### 2. Positions Tab

```
Portfolio summary stat cards at top:
  Equity, Cash, Positions Value, Unrealized PnL

Open positions table:
  Symbol, side, qty, entry price, current price, market value,
  unrealized PnL ($, %), realized PnL, total return, bars held
  Actions: [Close ▼] dropdown, [Edit SL/TP]

Closed positions section (collapsible):
  Date range filter
  Closed positions table: symbol, side, entry/exit price, PnL,
    holding period, close reason, closed at
```

### 3. PnL Analysis Tab

```
PnL summary cards: Today, This Week, This Month, Total
  (by strategy breakdown, by symbol breakdown)

PnL calendar heatmap:
  30-day grid, each day colored by PnL (green gradient/red gradient)
  Hover shows day's PnL detail

Win/loss distribution chart (Recharts BarChart):
  Histogram of trade PnL values
```

### 4. Equity Tab

```
Equity curve chart (period selector: 1D, 7D, 30D, 90D, YTD, ALL)
  Green area chart for equity

Drawdown chart (below equity curve, same time axis):
  Red area chart showing drawdown %
  Threshold line at max drawdown limit

Equity breakdown cards:
  Cash vs Positions Value (stacked)
  Equities vs Forex breakdown
```

### 5. Dividends Tab

```
Upcoming dividends table:
  Symbol, ex-date, payable date, shares held, estimated amount

Recent dividend payments table:
  Symbol, ex-date, paid date, shares, amount per share, gross, net, status

Dividend income summary cards:
  Today, This Month, This Year, All Time
  By symbol breakdown
```

### 6. Feature Components (frontend/src/features/portfolio/)

**PositionCard.tsx** — Compact position display with PnL
**PositionTable.tsx** — DataTable configured for open/closed positions
**PnlSummary.tsx** — PnL breakdown cards
**PnlCalendar.tsx** — 30-day heatmap grid (custom component)
**EquityCurve.tsx** — Recharts AreaChart with equity data
**DrawdownChart.tsx** — Recharts AreaChart (red) with drawdown data
**DividendTable.tsx** — DataTable for dividend payments
**ClosePositionDialog.tsx** — Confirm dialog for closing (Close All / Close Partial)
**EditStopLossDialog.tsx** — Modal for editing SL/TP on a position

### 7. Data Requirements

```
GET /portfolio/summary               → stat cards (stale: 30s, refetch: 60s)
GET /portfolio/equity                 → equity breakdown (stale: 30s, refetch: 60s)
GET /portfolio/cash                   → cash balances
GET /portfolio/positions/open         → open positions (stale: 15s, refetch: 30s)
GET /portfolio/positions/closed       → closed positions
GET /portfolio/pnl/summary           → PnL breakdown (stale: 30s, refetch: 60s)
GET /portfolio/pnl/realized          → PnL entries for calendar/distribution
GET /portfolio/equity-curve          → chart data (stale: 60s, refetch: 300s)
GET /portfolio/metrics               → performance metrics
GET /portfolio/dividends             → payment history
GET /portfolio/dividends/upcoming    → upcoming dividends
GET /portfolio/dividends/summary     → income summary
```

---

## Acceptance Criteria

### Positions Tab
1. Portfolio summary stat cards render with real data
2. Open positions table renders with all columns
3. Position PnL values use green/red coloring (PnlValue component)
4. Position prices use monospace formatting (PriceValue component)
5. Close dropdown shows Close All / Close Partial options
6. Close triggers confirmation dialog
7. Edit SL/TP opens modal with current values pre-filled
8. Closed positions section is collapsible
9. Closed positions filterable by date range
10. Empty state when no open positions

### PnL Analysis Tab
11. PnL summary cards show today, week, month, total
12. PnL calendar heatmap renders 30-day grid
13. Calendar days colored by PnL (green gradient positive, red gradient negative)
14. Calendar hover shows day detail
15. Win/loss distribution chart renders as histogram

### Equity Tab
16. Equity curve chart renders with period selector
17. Drawdown chart renders below equity curve
18. Drawdown chart shows threshold line at max limit
19. Equity breakdown shows cash vs positions, equities vs forex

### Dividends Tab
20. Upcoming dividends table renders
21. Dividend payment history table renders
22. Dividend income summary cards show totals by period
23. Dividend income by symbol breakdown shown

### General
24. Tab navigation works
25. All data fetches use TanStack Query with correct intervals
26. Loading, empty, and error states handled for all sections
27. Nothing in /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

BUILDER_OUTPUT.md at /studio/TASKS/TASK-019-portfolio/BUILDER_OUTPUT.md
