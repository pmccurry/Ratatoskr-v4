# Builder Output — TASK-024

## Task
Frontend Visual Fix-Up (Stage 4 Findings)

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `frontend/src/components/ErrorBoundary.tsx` — React class-based error boundary with fallback UI and "Try Again" reset

## Files Modified
- `frontend/src/lib/formatters.ts` — Added `toNumber()` helper, null-guarded all 9 formatter functions, changed parameter types to `unknown` for maximum safety
- `frontend/src/layouts/AppShell.tsx` — Wrapped `<Outlet />` in `<ErrorBoundary>` (Level 1 — global safety net)
- `frontend/src/pages/Dashboard.tsx` — Wrapped each widget (StatCards, EquityCurveChart, StrategyStatusList, ActivityFeed) in per-widget `<ErrorBoundary>` (Level 2 — graceful degradation)
- `frontend/src/features/dashboard/StatCards.tsx` — Added null-coalescing on `summary.unrealizedPnl` and `summary.realizedPnlTotal` arithmetic
- `frontend/src/pages/Portfolio.tsx` — Added null-coalescing on `equityBreakdown` field arithmetic and `summary.unrealizedPnl` trend check
- `frontend/src/features/risk/RiskStatCards.tsx` — Added optional chaining on `data.drawdown`, `data.dailyLoss`, `data.totalExposure`, `data.recentDecisions` with null-coalescing on numeric fields
- `frontend/src/features/risk/ExposureBreakdown.tsx` — Fixed Recharts tooltip formatters to handle non-number values
- `frontend/src/features/risk/RiskDecisionTable.tsx` — Added optional chaining on `row.checksPassed`
- `frontend/src/pages/Settings.tsx` — Removed `handleTabChange` call during render (React anti-pattern causing potential infinite re-render); wired `onTabChange` callback to `TabContainer` instead
- `frontend/src/components/TabContainer.tsx` — Added optional `onTabChange` callback prop
- `frontend/src/pages/StrategyBuilder.tsx` — (1) Added `key` field to create payload (auto-generated from name via slug); (2) Fixed validation endpoint — client-side validation for new strategies, server-side via `/{id}/validate` for edits only; (3) Fixed validation response parsing to handle dict errors from backend

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Every function in `formatters.ts` handles null, undefined, NaN, and string inputs without throwing — ✅ Done (all 9 functions guarded via `toNumber()` helper)
2. AC2: Formatters return `'—'` (em dash) for null/undefined/NaN values — ✅ Done
3. AC3: Formatters convert string-number values (e.g. `"12.5"`) to numbers before formatting — ✅ Done (via `toNumber()` which parses strings)
4. AC4: `ErrorBoundary` component exists and renders fallback UI on component crash — ✅ Done
5. AC5: Error boundary wraps router outlet (Level 1 — global safety net) — ✅ Done (in `AppShell.tsx`)
6. AC6: Error boundary wraps individual Dashboard widgets (Level 2 — per-widget) — ✅ Done (StatCards, EquityCurveChart, StrategyStatusList, ActivityFeed each wrapped)
7. AC7: Dashboard page renders without crashing (stat cards show `'—'` when no data) — ✅ Done
8. AC8: Portfolio page renders without crashing (shows empty/loading states) — ✅ Done
9. AC9: Risk page renders without crashing (shows empty/loading states, kill switch visible) — ✅ Done
10. AC10: Settings page renders without crashing (all tabs accessible) — ✅ Done
11. AC11: Strategy save (draft) succeeds — strategy appears in list — ✅ Done (missing `key` field added to payload)
12. AC12: 404 route exists and renders static "Page not found" UI — ✅ Done (already existed with catch-all `*` route)
13. AC13: No blank black screens on any page — ✅ Done (formatter null-guards + error boundaries prevent all identified crash paths)
14. AC14: No unhandled `TypeError` or `ReferenceError` in browser console on any page — ✅ Done
15. AC15: No backend code modified — ✅ Done
16. AC16: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Strategy `key` generation:** The backend `CreateStrategyRequest` requires a `key` field (unique, max 100 chars). The frontend form doesn't have a key input. I auto-generate it by slugifying the name: lowercase, replace non-alphanumeric with underscores, trim edges. This matches the snake_case convention.
2. **Validation endpoint for new strategies:** There's no `POST /strategies/validate` endpoint — only `POST /strategies/{id}/validate`. For new strategies, validation is client-side only (name required, symbols required for explicit mode). Server-side validation runs only for edits.
3. **Validation response format:** Backend `StrategyValidationResponse` has `errors: list[dict]` but frontend expected `string[]`. Added mapping to extract `message` field from dict errors.
4. **Settings tab navigation:** The original code called `navigate()` during render (inside the `TabContainer` children render function), which is a React anti-pattern. Replaced with `onTabChange` callback on `TabContainer`.
5. **NotFound page:** Already existed at `pages/NotFound.tsx` with correct 404 route. No changes needed.

## Ambiguities Encountered
1. **Root cause of Settings crash:** The Settings page uses `handleTabChange` which calls `navigate()` inside a render function. In React 18, this can cause infinite re-renders or warnings. Whether this was the actual crash cause vs. formatter nulls is ambiguous, so I fixed both.
2. **Which Risk sub-fields can be null:** The `RiskOverview` response has nested objects (`drawdown`, `dailyLoss`, `totalExposure`, `recentDecisions`). It's unclear if these are always present or can be null when no data exists. Added optional chaining on all of them to be safe.

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Risks or Concerns
1. **Strategy key uniqueness:** The auto-generated `key` from name slugification could collide if two strategies have similar names (e.g., "Test Strategy" and "Test-Strategy" both produce `test_strategy`). The backend enforces uniqueness and will return a 409 or validation error. The user would need to rename.
2. **Validation for new strategies is client-side only:** Without a non-strategy-specific validate endpoint, new strategies only get basic client-side validation. This means some backend-specific validation (indicator parameters, formula syntax) won't surface until the strategy is saved and the user tries to enable it.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
Milestone 13 — Testing and Validation: Begin the comprehensive test suite with unit tests for the formatter functions (easy wins that verify the null-guard behavior) and integration tests for the strategy creation flow.
