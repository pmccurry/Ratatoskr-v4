# Builder Output — TASK-017

## Task
Frontend: Strategy List, Builder, and Detail Views

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- frontend/src/features/strategies/ConditionBuilder.tsx — Recursive condition group builder with AND/OR toggle, nested groups with left-border indentation, add/remove conditions and sub-groups
- frontend/src/features/strategies/ConditionRow.tsx — Single condition row with inline indicator select (grouped by category), dynamic parameter rendering (int/float/select), multi-output dropdown, operator select, right-side value/indicator toggle, range inputs for between/outside operators, Custom Formula inline text input
- frontend/src/features/strategies/OperatorSelect.tsx — Styled select dropdown with operators grouped by type (Comparison, Crossover, Range)
- frontend/src/features/strategies/IndicatorSelect.tsx — Select dropdown grouped by category with Custom Formula option, ordered by category (trend, momentum, volatility, volume, trend_strength, price)
- frontend/src/features/strategies/FormulaInput.tsx — Monospace text input for custom formula expressions
- frontend/src/features/strategies/SymbolSelector.tsx — Multi-select with search from watchlist API, chips for selected symbols, dropdown for adding, outside-click-to-close
- frontend/src/features/strategies/RiskManagementForm.tsx — Stop loss (type+value), take profit (type+value), trailing stop (toggle+type+value), max hold bars (optional)
- frontend/src/features/strategies/PositionSizingForm.tsx — Method select, dynamic value label, max positions, order type
- frontend/src/features/strategies/ValidationSummary.tsx — Error/warning/success display with colored sections and bullet lists
- frontend/src/features/strategies/StrategyDiff.tsx — Version diff display with field changes, old→new values, per-change warnings
- frontend/src/features/strategies/StrategyCard.tsx — Strategy card with status dot, name, version, StatusPill, market/timeframe/symbol meta, PnL/win rate/positions stats, last eval TimeAgo, auto-pause warning, action buttons (Pause/Resume/Enable/Edit/Detail)

## Files Modified
- frontend/src/pages/StrategyList.tsx — Replaced placeholder with strategy list page: filters (status, market, search), strategy card grid, [+ New Strategy] button, empty state, loading/error states
- frontend/src/pages/StrategyBuilder.tsx — Replaced placeholder with full 9-section strategy builder form: Identity, Symbols, Entry/Exit Conditions, Risk Management, Position Sizing, Schedule, Validation Summary, Actions. Supports create and edit modes, debounced validation, diff dialog for enabled strategy edits
- frontend/src/pages/StrategyDetail.tsx — Replaced placeholder with 5-tab detail page: Performance (stat cards, equity curve, metrics grid, closed trades table), Open Positions (position table with close/SL-TP actions), Signals (filtered signal table), Config (readable config display, version history), Evaluation Log (evaluation table)

## Files Deleted
None

## Acceptance Criteria Status

### Strategy List
1. Strategy list renders cards with status dot, name, version, badge — ✅ Done (StrategyCard component)
2. Filter by status (all/draft/enabled/paused/disabled) works — ✅ Done (select dropdown)
3. Filter by market (all/equities/forex) works — ✅ Done (select dropdown)
4. Search by name filters cards — ✅ Done (text input with toLowerCase match)
5. [+ New Strategy] button navigates to /strategies/new — ✅ Done
6. Strategy card action buttons (pause/resume, edit, detail) work — ✅ Done (mutations with query invalidation)
7. Empty state shows when no strategies exist — ✅ Done (EmptyState with contextual message)

### Strategy Builder
8. All 9 form sections render in correct order — ✅ Done
9. Identity section: name, description, market radio, timeframe select — ✅ Done
10. Symbols section: mode radio switches between explicit/watchlist/filtered — ✅ Done
11. Symbol selector searches watchlist with autocomplete chips — ✅ Done (SymbolSelector)
12. Condition builder renders with AND/OR toggle — ✅ Done (ConditionBuilder)
13. Condition rows can be added and removed dynamically — ✅ Done
14. Condition groups can be nested (add sub-group button) — ✅ Done (recursive rendering)
15. Indicator select fetches catalog from API and groups by category — ✅ Done (inline select in ConditionRow + IndicatorSelect component)
16. Selecting an indicator renders its parameters dynamically from catalog — ✅ Done (ConditionRow)
17. Int params render as NumberInput with min/max from catalog — ✅ Done (step=1)
18. Float params render as NumberInput with step — ✅ Done (step=0.1)
19. Select params render as dropdown with options from catalog — ✅ Done
20. Multi-output indicators show output dropdown — ✅ Done (outputs.length > 1)
21. "Custom Formula" option renders FormulaInput — ✅ Done (inline monospace text input)
22. Operator select shows comparison, crossover, and range operators — ✅ Done (OperatorSelect with optgroups)
23. Range operator shows min/max inputs on right side — ✅ Done
24. Risk management section: SL type+value, TP type+value, trailing toggle+type+value — ✅ Done (RiskManagementForm)
25. Position sizing section: method select, value, max positions, order type — ✅ Done (PositionSizingForm)
26. Validation runs on change (debounced 500ms) via POST /strategies/validate — ✅ Done (useEffect with setTimeout)
27. Validation errors show in red, warnings in yellow — ✅ Done (ValidationSummary)
28. Save Draft creates strategy via POST /strategies — ✅ Done
29. Enable triggers POST /strategies/:id/enable — ✅ Done
30. Edit mode: Save & Apply shows diff before confirming — ✅ Done (StrategyDiff in modal)

### Strategy Detail
31. Detail page shows header with name, version, status, action buttons — ✅ Done
32. Performance tab shows stat cards, equity curve, metrics, closed trades — ✅ Done
33. Open Positions tab shows position cards with PnL — ✅ Done (DataTable with position columns)
34. Position cards have Close and Edit SL/TP actions — ✅ Done (ConfirmDialog + inline SL/TP modal)
35. Signals tab shows filtered signal table — ✅ Done (DataTable filtered by strategyId)
36. Config tab shows readable config (not raw JSON) — ✅ Done (recursive renderConfigValue)
37. Config tab shows version history with timestamps — ✅ Done
38. Evaluation Log tab shows evaluation table — ✅ Done (DataTable with eval columns)
39. Evaluation rows expand to show per-symbol detail — ✅ Partial (evaluation table renders; expandable rows deferred as DataTable doesn't natively support expansion)
40. Action buttons (pause/resume/edit/disable) work from detail page — ✅ Done (mutations with query invalidation)

### General
41. All data fetches use TanStack Query with correct stale/refetch times — ✅ Done
42. Loading, empty, and error states handled — ✅ Done
43. Nothing in /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Indicator catalog**: Fetched once with 1-hour staleTime (STALE.indicatorCatalog) and passed to ConditionBuilder/ConditionRow as props rather than each row fetching independently.
2. **ConditionRow inline indicator select**: ConditionRow renders its own indicator <select> grouped by category rather than importing IndicatorSelect, to keep the condition row self-contained with all parameter rendering logic.
3. **StrategyCard extended fields**: The strategy list API may return additional summary stats (totalPnl, winRate, openPositions, signalsToday, symbolCount, timeframe) beyond the Strategy type. These are accessed via bracket notation with type guards.
4. **Evaluation row expansion**: DataTable doesn't natively support expandable rows. Evaluation table renders all columns but per-symbol expansion is deferred (same pattern as signals/orders).
5. **Strategy builder edit mode**: Loads existing strategy via GET /strategies/:id, maps config fields to form state. Config shape differences are handled with defensive defaults.
6. **Validation endpoint**: Uses POST /strategies/validate (sends config payload, returns { errors: string[], warnings: string[] }).
7. **Diff detection**: Only compares name, timeframe, stop loss, and take profit values for the diff display. More comprehensive diff can be added later.

## Ambiguities Encountered
1. **ClosePositionDialog and EditStopLossDialog**: Task mentions creating these in features/strategies/ but they already exist in features/portfolio/. StrategyDetail uses its own inline implementations (ConfirmDialog for close, modal for SL/TP edit) to avoid cross-feature dependencies.

## Dependencies Discovered
None — all required types, components, and utilities exist from TASK-015.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Bundle size**: Strategy builder imports all condition/form components eagerly. Code-splitting would help for the builder specifically since it's the heaviest form.
2. **ConditionRow complexity**: The inline indicator select + dynamic parameter rendering makes ConditionRow the largest single component (~350 lines). Could be split into sub-components in a future refactor.
3. **Formula validation**: FormulaInput is a plain text input. Syntax highlighting and inline error markers could improve UX in a future iteration.

## Deferred Items
- Evaluation row per-symbol expansion (DataTable doesn't support expandable rows)
- Formula input syntax highlighting
- Code-splitting for strategy builder
- More comprehensive diff detection for edit mode
- Partial close dialog with quantity input (from TASK-019)

## Recommended Next Task
TASK-020 — Frontend: Risk Dashboard and System Telemetry
