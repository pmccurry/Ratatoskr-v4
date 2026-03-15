# TASK-018 — Frontend: Signals and Paper Trading Views

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Replace the Signals and Orders placeholder pages with complete views:
signal table with filters and stats, order and fill tables, forex pool
status, and shadow tracking comparison.

## Read First

1. /studio/SPECS/frontend_specs.md — section 5, Views 5-6
2. Review TASK-015 BUILDER_OUTPUT.md — existing components and types

## Constraints

- Use existing shared components from TASK-015
- Do NOT modify backend code
- Do NOT touch /studio (except BUILDER_OUTPUT.md)

---

## Deliverables

### 1. Signals Page (frontend/src/pages/Signals.tsx)

```
Filters bar: strategy select, status select, symbol input, signal type,
  source, date range picker
Stats summary bar: total, approved, rejected, modified, expired, approval rate
Signal table (DataTable): time, symbol, side, type, strategy, status,
  confidence, source
Expandable rows: full payload (indicator values at signal time)
```

### 2. Signal Feature Components (frontend/src/features/signals/)

**SignalTable.tsx** — DataTable configured for signals with expandable rows
**SignalDetail.tsx** — Expanded row content showing payload_json formatted
**SignalStats.tsx** — Summary bar with counts and approval rate

### 3. Orders Page (frontend/src/pages/Orders.tsx)

**Tabs:** [Orders] [Fills] [Forex Pool] [Shadow Tracking]

**Orders Tab:**
```
Filters: strategy, symbol, status, market, date range
Order table: time, symbol, side, type, qty, price, status, slippage, strategy
Expandable rows: full order detail (broker IDs, rejection reason)
```

**Fills Tab:**
```
Filters: strategy, symbol, side, date range
Fill table: time, symbol, side, qty, ref price, fill price, fee,
  slippage bps, slippage $, net value
```

**Forex Pool Tab:**
```
Account cards: account label, allocations (symbol + side + strategy name + since)
Pair capacity summary: per-pair bar showing occupied/available
Empty state: "No forex accounts configured"
```

**Shadow Tracking Tab:**
```
Shadow positions table: strategy, symbol, side, entry price, current/exit price,
  PnL, status (open/closed), close reason
Comparison table: strategy name, real trades, real PnL, shadow trades,
  shadow PnL, blocked signals, missed PnL
```

### 4. Paper Trading Feature Components (frontend/src/features/orders/)

**OrderTable.tsx** — DataTable for orders
**FillTable.tsx** — DataTable for fills
**ForexPoolStatus.tsx** — Account cards + pair capacity visualization
**ShadowComparison.tsx** — Side-by-side real vs shadow performance table

### 5. Data Requirements

```
# Signals
GET /signals                           → paginated list (stale: 10s, refetch: 10s)
GET /signals/stats                     → summary stats (stale: 30s, refetch: 30s)

# Orders & Fills
GET /paper-trading/orders              → orders (stale: 15s, refetch: 30s)
GET /paper-trading/fills               → fills (stale: 15s, refetch: 30s)
GET /paper-trading/fills/recent        → recent fills

# Forex Pool
GET /paper-trading/forex-pool/status   → pool status (stale: 30s, refetch: 30s)
GET /paper-trading/forex-pool/accounts → account details

# Shadow
GET /paper-trading/shadow/positions    → shadow positions
GET /paper-trading/shadow/comparison   → comparison stats
```

---

## Acceptance Criteria

### Signals View
1. Signal table renders with all columns (time, symbol, side, type, strategy, status, confidence)
2. Signal rows expandable to show full payload details
3. Filter by strategy works
4. Filter by status works
5. Filter by symbol works
6. Filter by signal type works
7. Stats summary shows total, approved, rejected, modified, expired counts
8. Stats shows approval rate percentage
9. Empty state when no signals

### Paper Trading — Orders Tab
10. Order table renders with all columns
11. Filter by strategy, symbol, status, market works
12. Expandable rows show full order detail
13. Status column uses StatusPill component
14. Empty state when no orders

### Paper Trading — Fills Tab
15. Fill table renders with all columns including fee and slippage
16. Price columns use PriceValue component
17. Fee and slippage columns use PnlValue-style formatting
18. Filter by strategy, symbol, date range works

### Paper Trading — Forex Pool Tab
19. Account cards show allocations per account
20. Pair capacity visualization shows occupied vs available
21. Empty state when no forex accounts

### Paper Trading — Shadow Tracking Tab
22. Shadow positions table renders with PnL coloring
23. Comparison table shows real vs shadow performance side-by-side
24. Missed PnL column highlighted

### General
25. Tab navigation works on Orders page
26. All data fetches use TanStack Query with correct intervals
27. Loading, empty, and error states handled for all sections
28. Nothing in /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

BUILDER_OUTPUT.md at /studio/TASKS/TASK-018-signals-orders/BUILDER_OUTPUT.md
