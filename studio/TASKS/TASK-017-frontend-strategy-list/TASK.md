# TASK-017 — Frontend: Strategy List, Builder, and Detail Views

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Replace the Strategy placeholder pages with complete views: strategy list
with cards and filtering, the config-driven strategy builder form (the most
complex UI in the platform), and the strategy detail page with tabs.

## Read First

1. /studio/SPECS/frontend_specs.md — section 5, Views 2-4
2. /studio/SPECS/strategy_module_spec.md — sections 2-5 (indicator catalog, conditions, formulas, config schema)
3. Review TASK-015 BUILDER_OUTPUT.md — existing components and types

## Constraints

- Use existing shared components from TASK-015
- The strategy builder must dynamically render from the indicator catalog API
  (adding a new indicator to the backend auto-renders in the UI)
- Do NOT modify backend code
- Do NOT touch /studio (except BUILDER_OUTPUT.md)

---

## Deliverables

### 1. Strategy List Page (frontend/src/pages/StrategyList.tsx)

```
Header: "Strategies" + [+ New Strategy] button
Filters: status dropdown, market dropdown, search input
Strategy cards: status dot, name, version, status badge, market, timeframe,
  PnL, win rate, position count, last evaluated, action buttons
Empty state: "No strategies yet. Create your first strategy."
```

### 2. Strategy Builder Page (frontend/src/pages/StrategyBuilder.tsx)

The most complex form in the platform. Single scrollable page with sections:

1. **Identity** — name, description, market (radio), timeframe (select), additional timeframes
2. **Symbols** — mode radio (explicit/watchlist/filtered), symbol search with chips, market dropdown, filter fields
3. **Entry Conditions** — dynamic condition builder (see below)
4. **Exit Conditions** — same condition builder
5. **Risk Management** — stop loss, take profit, trailing stop, max hold
6. **Position Sizing** — method select, value input, max positions, order type
7. **Schedule** — trading hours mode, re-entry cooldown
8. **Validation Summary** — live validation (debounced 500ms), errors in red, warnings in yellow
9. **Actions** — Save Draft, Validate, Enable (or Save & Apply for edits with diff)

### 3. Condition Builder Components (frontend/src/features/strategies/)

**ConditionBuilder.tsx** — Manages a condition group (AND/OR toggle + list of conditions/sub-groups)
**ConditionRow.tsx** — Single condition: [indicator select] [params] [operator select] [right side]
**IndicatorSelect.tsx** — Dropdown grouped by category, fetched from GET /strategies/indicators
**OperatorSelect.tsx** — Operator dropdown (comparison, crossover, range)
**SymbolSelector.tsx** — Multi-select with search from watchlist
**FormulaInput.tsx** — Text input with syntax highlighting for custom expressions
**RiskManagementForm.tsx** — Stop loss, take profit, trailing stop controls
**PositionSizingForm.tsx** — Method select, value, max positions
**ValidationSummary.tsx** — Live validation display from POST /strategies/formulas/validate
**StrategyDiff.tsx** — Side-by-side diff for edit mode (v1.2.0 → v1.3.0)

**Dynamic indicator parameter rendering:**
- Fetch indicator catalog on mount (cached 1 hour)
- When indicator selected → render its params dynamically:
  - int params: NumberInput with min/max from catalog
  - float params: NumberInput with min/max and step
  - select params: SelectInput with options from catalog
- Multi-output indicators: show output dropdown (macd → macd_line/signal_line/histogram)
- "Custom Formula" option: switch from dropdown to FormulaInput

### 4. Strategy Detail Page (frontend/src/pages/StrategyDetail.tsx)

Header with back link, name, version, status badge, action buttons.

**Tabs:**
- **Performance** — stat cards (PnL, win rate, trades, profit factor), equity curve, metrics grid, closed trades table
- **Open Positions** — position cards with inline SL/TP edit, close dropdown
- **Signals** — signal table filtered to this strategy
- **Config** — readable config display, version history with diff
- **Evaluation Log** — evaluation table (timestamp, symbols, signals, duration, status), expandable rows

### 5. Strategy Feature Components (frontend/src/features/strategies/)

**StrategyCard.tsx** — Card for list view with status, PnL, actions
**ClosePositionDialog.tsx** — Confirm dialog for closing positions (if needed for detail view)
**EditStopLossDialog.tsx** — Inline edit for position SL/TP

---

## Data Requirements

```
GET /strategies                        → list
GET /strategies/indicators             → indicator catalog (stale: 1hr)
GET /market-data/watchlist             → symbols for selector
GET /strategies/:id                    → detail with config
GET /strategies/:id/versions           → version history
GET /strategies/:id/evaluations        → evaluation log
GET /portfolio/metrics/:strategyId     → performance metrics
GET /portfolio/positions?strategyId=   → open positions
GET /portfolio/pnl/realized?strategyId= → closed trades
GET /signals?strategyId=               → signals for this strategy
POST /strategies                       → create
PUT /strategies/:id/config             → update config
PUT /strategies/:id/meta               → update name/description
POST /strategies/:id/enable            → enable
POST /strategies/:id/pause             → pause
POST /strategies/:id/disable           → disable
POST /strategies/:id/validate          → validate config
```

---

## Acceptance Criteria

### Strategy List
1. Strategy list renders cards with status dot, name, version, badge
2. Filter by status (all/draft/enabled/paused/disabled) works
3. Filter by market (all/equities/forex) works
4. Search by name filters cards
5. [+ New Strategy] button navigates to /strategies/new
6. Strategy card action buttons (pause/resume, edit, detail) work
7. Empty state shows when no strategies exist

### Strategy Builder
8. All 9 form sections render in correct order
9. Identity section: name, description, market radio, timeframe select
10. Symbols section: mode radio switches between explicit/watchlist/filtered
11. Symbol selector searches watchlist with autocomplete chips
12. Condition builder renders with AND/OR toggle
13. Condition rows can be added and removed dynamically
14. Condition groups can be nested (add sub-group button)
15. Indicator select fetches catalog from API and groups by category
16. Selecting an indicator renders its parameters dynamically from catalog
17. Int params render as NumberInput with min/max from catalog
18. Float params render as NumberInput with step
19. Select params render as dropdown with options from catalog
20. Multi-output indicators show output dropdown
21. "Custom Formula" option renders FormulaInput
22. Operator select shows comparison, crossover, and range operators
23. Range operator shows min/max inputs on right side
24. Risk management section: SL type+value, TP type+value, trailing toggle+type+value
25. Position sizing section: method select, value, max positions, order type
26. Validation runs on change (debounced 500ms) via POST /strategies/validate
27. Validation errors show in red, warnings in yellow
28. Save Draft creates strategy via POST /strategies
29. Enable triggers POST /strategies/:id/enable
30. Edit mode: Save & Apply shows diff before confirming

### Strategy Detail
31. Detail page shows header with name, version, status, action buttons
32. Performance tab shows stat cards, equity curve, metrics, closed trades
33. Open Positions tab shows position cards with PnL
34. Position cards have Close and Edit SL/TP actions
35. Signals tab shows filtered signal table
36. Config tab shows readable config (not raw JSON)
37. Config tab shows version history with timestamps
38. Evaluation Log tab shows evaluation table
39. Evaluation rows expand to show per-symbol detail
40. Action buttons (pause/resume/edit/disable) work from detail page

### General
41. All data fetches use TanStack Query with correct stale/refetch times
42. Loading, empty, and error states handled
43. Nothing in /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

BUILDER_OUTPUT.md at /studio/TASKS/TASK-017-strategies/BUILDER_OUTPUT.md
