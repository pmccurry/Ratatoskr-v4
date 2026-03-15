# Validation Report — TASK-022

## Task
Frontend Bug Fixes

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present (explicitly "None")
- [x] Files Modified section present (18 files listed)
- [x] Files Deleted section present (3 files listed)
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (4 assumptions documented)
- [x] Ambiguities section present (2 documented)
- [x] Dependencies section present (1 dependency: sparkline endpoint)
- [x] Tests section present
- [x] Risks section present (2 risks documented)
- [x] Deferred Items section present (1: sparklines)
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

### Styling Fixes

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | All instances of `text-danger` replaced with `text-error` across entire frontend | ✅ | ✅ `grep text-danger` across frontend returns 0 matches. All 4 files (OrderTable, FillTable, ForexPoolStatus, ShadowComparison) now use `text-error`. | PASS |
| 2 | No other non-existent Tailwind classes used in modified files | ✅ | ✅ Spot-checked all modified files — all classes match project theme (`text-success`, `text-error`, `text-accent`, `text-text-primary`, etc.) | PASS |

### Functional Fixes

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 3 | ConditionRow radio buttons use stable IDs (useId), not Math.random() | ✅ | ✅ ConditionRow.tsx line 1: `import { useId } from 'react'`; line 43: `const radioId = useId()`; lines 264/280: `name={\`right-mode-${radioId}\`}`. `grep Math.random()` returns 0 matches. | PASS |
| 4 | ActivityFeed category filter maps correctly to backend categories | ✅ | ✅ ActivityFeed.tsx line 9: `CATEGORY_OPTIONS` includes `'paper_trading'` (not `'execution'`). Line 10-18: `CATEGORY_LABELS` maps `paper_trading` to display label `'trading'`. | PASS |
| 5 | Only one "Edit in Settings" link on Risk page | ✅ | ✅ Risk.tsx renders `<RiskConfigSummary />` directly with no wrapper link. `grep "Edit in Settings"` finds exactly 1 occurrence in RiskConfigSummary.tsx:57. | PASS |
| 6 | StrategyStatusList shows operationally useful data (not just market+version) | ✅ | ✅ StrategyStatusList.tsx lines 46-49: shows `<StatusPill status={s.status} />` and `<TimeAgo value={s.lastEvaluatedAt} />` (or "never"). No market/version display. | PASS |
| 7 | EditStopLossDialog pre-fills current SL/TP values | ✅ | ✅ EditStopLossDialog.tsx lines 16-22: `useEffect` sets `stopLoss` and `takeProfit` from `position.stopLoss`/`position.takeProfit` when `open && position`. | PASS |
| 8 | SignalTable pagination uses server totalItems (not client data.length) | ✅ | ✅ SignalTable.tsx line 30: query typed as `{ data: Signal[]; total: number }`. Line 44: `const serverTotal = response?.total ?? 0`. Line 211: `total={serverTotal}` passed to DataTable. | PASS |
| 9 | OrderTable has working pagination controls | ✅ | ✅ OrderTable.tsx lines 12-13: `page`/`pageSize` state. Line 40: `serverTotal = response?.total ?? 0`. Lines 139-143: DataTable receives `page`, `pageSize`, `total`, `onPageChange`, `onPageSizeChange`. | PASS |
| 10 | Strategy filter on Signals page is a dropdown, not UUID text input | ✅ | ✅ SignalTable.tsx lines 37-41: fetches strategies. Lines 128-140: renders `<select>` with strategy name options, not text input. | PASS |
| 11 | Strategy filter on Orders page is a dropdown, not UUID text input | ✅ | ✅ OrderTable.tsx lines 33-37: fetches strategies. Lines 89-98: renders `<select>` with strategy name options. | PASS |
| 12 | Fills tab has date range filter inputs | ✅ | ✅ FillTable.tsx lines 16-17: `dateStart`/`dateEnd` state. Lines 23-24: converted to ISO and passed as API params. Lines 121-134: two `<input type="date">` elements rendered. | PASS |
| 13 | EquityCurve period selector includes YTD option | ✅ | ✅ ChartContainer.tsx line 3: `PERIODS` includes `'YTD'`. EquityCurve.tsx line 15: `PERIOD_MAP` includes `'YTD': 'ytd'`. store.ts line 7: type union includes `'ytd'`. | PASS |
| 14 | Win/loss distribution chart uses green (positive) and red (negative) bar colors | ✅ | ✅ PnlCalendar.tsx lines 53-68: `buildBuckets()` assigns `COLORS.success` for positive, `COLORS.error` for negative. Lines 162-170: `<Bar>` uses `<Cell>` with per-bucket `fill={entry.color}`. | PASS |
| 15 | Close position action is a dropdown menu (Close All at minimum) | ✅ | ✅ PositionTable.tsx lines 4, 84-104: `DropdownMenu` with trigger button "Close ▾" and two items: "Close All" (danger, functional) and "Close Partial (coming soon)" (no-op). | PASS |

### Deferred Items

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 16 | Risk config change history table renders (or has TODO with endpoint call) | ✅ | ✅ Settings.tsx lines 75-79: queries `GET /risk/config/audit`. Lines 163-174: renders DataTable with AUDIT_COLUMNS (field, old value, new value, changed by, timestamp). Fully implemented, not just a TODO. | PASS |
| 17 | Sparkline mini-charts render (or have comment explaining deferral) | ✅ | ✅ ThroughputMetrics.tsx lines 5-6: TODO comment: "Add per-metric sparkline charts... Deferred — requires a new backend endpoint that returns historical throughput snapshots." | PASS |
| 18 | Evaluation log expandable rows work (or have basic expand pattern) | ✅ | ✅ StrategyDetail.tsx line 69: `expandedEvalId` state. Lines 240-261: eval Time column renders click-to-expand button with ▸/▾ indicators. Lines 467-502: expanded detail panel shows strategy version, duration, symbols evaluated, errors, skip reason, signals emitted, exits triggered. | PASS |

### Unused Components

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 19 | IndicatorSelect.tsx is either wired in or deleted | ✅ | ✅ File does not exist — `glob` returns no matches. Deleted. | PASS |
| 20 | ClosePositionDialog.tsx is either wired in or deleted | ✅ | ✅ File does not exist — `glob` returns no matches. Deleted. | PASS |
| 21 | FormulaInput.tsx is either wired in or deleted | ✅ | ✅ File does not exist — `glob` returns no matches. Deleted. | PASS |

### General

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 22 | No backend code modified | ✅ | ✅ All modified files are under `frontend/src/`. No backend files in modified list. | PASS |
| 23 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md written in /studio/TASKS/TASK-022-frontend-bugfixes/. | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] TypeScript component files use PascalCase
- [x] TypeScript utility files use camelCase (store.ts, formatters.ts)
- [x] Folder names match module specs exactly
- [x] Entity names match GLOSSARY exactly
- [x] No typos in module or entity names
- N/A Python files (no backend changes)
- N/A Database-related names (no backend changes)

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] API is REST-first (DECISION-011)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and frontend spec
- [x] File organization follows the defined module layout
- [x] No unexpected files in any directory

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have modified — independently verified:
1. `frontend/src/features/orders/OrderTable.tsx` — ✅ verified (text-error, pagination, strategy dropdown)
2. `frontend/src/features/orders/FillTable.tsx` — ✅ verified (text-error, strategy dropdown, date range filters)
3. `frontend/src/features/orders/ForexPoolStatus.tsx` — ✅ verified (text-error)
4. `frontend/src/features/orders/ShadowComparison.tsx` — ✅ verified (text-error)
5. `frontend/src/features/strategies/ConditionRow.tsx` — ✅ verified (useId replaces Math.random)
6. `frontend/src/features/dashboard/ActivityFeed.tsx` — ✅ verified (paper_trading category, Trading label)
7. `frontend/src/pages/Risk.tsx` — ✅ verified (duplicate Edit in Settings link removed)
8. `frontend/src/features/dashboard/StrategyStatusList.tsx` — ✅ verified (StatusPill + TimeAgo)
9. `frontend/src/features/portfolio/EditStopLossDialog.tsx` — ✅ verified (useEffect pre-fills)
10. `frontend/src/features/signals/SignalTable.tsx` — ✅ verified (server total, strategy dropdown)
11. `frontend/src/components/ChartContainer.tsx` — ✅ verified (YTD in PERIODS)
12. `frontend/src/features/portfolio/EquityCurve.tsx` — ✅ verified (YTD in PERIOD_MAP)
13. `frontend/src/lib/store.ts` — ✅ verified (ytd in type union)
14. `frontend/src/features/portfolio/PnlCalendar.tsx` — ✅ verified (Cell with green/red per bucket)
15. `frontend/src/features/portfolio/PositionTable.tsx` — ✅ verified (DropdownMenu with Close All)
16. `frontend/src/pages/Settings.tsx` — ✅ verified (audit DataTable rendered below form)
17. `frontend/src/features/system/ThroughputMetrics.tsx` — ✅ verified (TODO comment for sparklines)
18. `frontend/src/pages/StrategyDetail.tsx` — ✅ verified (expandable eval rows with detail panel)

### Files builder claims to have deleted — independently verified:
1. `frontend/src/features/strategies/IndicatorSelect.tsx` — ✅ confirmed deleted (glob returns no matches)
2. `frontend/src/features/portfolio/ClosePositionDialog.tsx` — ✅ confirmed deleted (glob returns no matches)
3. `frontend/src/features/strategies/FormulaInput.tsx` — ✅ confirmed deleted (glob returns no matches)

### Files that EXIST but builder DID NOT MENTION:
None found.

### Files builder claims to have created that DO NOT EXIST:
N/A (no files claimed created).

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)

1. **Settings.tsx handleTabChange called in render body**: Lines 117-119 call `handleTabChange(activeTab)` inside the TabContainer render callback, which triggers `navigate()` during render. This can cause React warnings about state updates during render. Should be moved to a `useEffect` or the TabContainer's `onChange` callback.

2. **StrategyDetail.tsx eval expand panel outside DataTable**: The expanded detail panel (lines 467-502) renders below the entire DataTable rather than inline after the expanded row. This is a UX limitation noted by the builder. Acceptable for MVP.

3. **FillTable missing pagination**: FillTable.tsx has date range filters and strategy dropdown but no pagination controls (no page/pageSize state, DataTable rendered without pagination props). If the fills list grows large, users cannot paginate through results. OrderTable was fixed with pagination (FIX-F8) but FillTable was not mentioned in the task and was not in scope.

4. **EditStopLossDialog accesses position fields via type cast**: Line 18 uses `position as unknown as Record<string, unknown>` to access `stopLoss`/`takeProfit` fields, bypassing TypeScript type checking. Works but fragile — the Position type should ideally include these fields.

5. **Close Partial dropdown item has no-op onClick**: PositionTable.tsx line 101: `onClick: () => {}` for "Close Partial (coming soon)" — acceptable per task spec which allows disabled option, but the item is clickable with no visual indication that it's non-functional. Should ideally have a `disabled` prop or visual indicator.

---

## Risk Notes

- The Settings.tsx audit query (FIX-F14) assumes the `/risk/config/audit` endpoint returns data matching the `AuditEntry` interface. If the backend uses different field names (e.g., `field_changed` vs `field`, `changed_at` vs `changedAt`), the table will show empty cells. The builder noted this as a risk.
- The `handleTabChange` in render body (minor #1) is a pre-existing pattern from TASK-020, not introduced by this task. The builder did not fix it because it wasn't listed as a bug in this task.

---

## RESULT: PASS

All 23 acceptance criteria independently verified against actual code. All 16 bug fixes correctly implemented (F1-F16), 3 unused components deleted (U1-U3). No backend modifications, no new features, no scope creep. 0 blockers, 0 major, 5 minor issues. Task is ready for Librarian update.
