# TASK-024 — Frontend Visual Fix-Up (Stage 4 Findings)

## Goal

Fix all issues found during the Stage 4 visual review. The frontend boots but 4 pages crash to blank black screens, strategy save fails with a validation error, and there is no error boundary. After this task, every page renders without crashing — showing loading/empty states when there's no data.

## Depends On

TASK-023a

## Root Cause Analysis

The confirmed crash is in `StatCards.tsx:42` which calls `formatPercent()` on a value from the API response. `formatPercent` in `formatters.ts:18` calls `value.toFixed()` — but the value is not a number (null, undefined, or string). This crashes the component, and since there is no React error boundary, the crash propagates up and kills the entire page (blank black screen).

The same pattern almost certainly causes Portfolio, Risk, and Settings pages to crash — any formatter calling `.toFixed()`, `.toLocaleString()`, or similar on a null/undefined API response field.

## Scope

**In scope:**
- Null-guard ALL formatter functions in `formatters.ts`
- Add a global React error boundary that catches component crashes and shows a fallback UI
- Fix Dashboard page (StatCards crash)
- Fix Portfolio page (blank screen)
- Fix Risk page (blank screen)
- Fix Settings page (blank screen)
- Fix strategy save validation error
- Fix 404 page

**Out of scope:**
- Backend code changes
- New features
- Performance optimization
- Test creation

---

## Deliverables

### D1 — Null-guard all formatters (`lib/formatters.ts`)

**This is the highest priority fix.** Every formatter function must handle null, undefined, and non-number inputs gracefully.

For every function in `formatters.ts`, add a guard at the top:

```typescript
// Pattern: guard → fallback → format
export function formatPercent(value: number | null | undefined): string {
  if (value == null || typeof value !== 'number' || isNaN(value)) return '—';
  return `${value.toFixed(2)}%`;
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null || typeof value !== 'number' || isNaN(value)) return '—';
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null || typeof value !== 'number' || isNaN(value)) return '—';
  return value.toFixed(decimals);
}
```

Apply this pattern to EVERY function in the file. The fallback character is `'—'` (em dash). Do not throw. Do not return empty string. Do not return `'0'`.

Also handle the case where the API returns a number-as-string (e.g., `"12.5"` instead of `12.5`). If the value is a string that parses to a valid number, convert it:

```typescript
function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && !isNaN(value)) return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    if (!isNaN(parsed)) return parsed;
  }
  return null;
}
```

Use `toNumber()` as the first step in every formatter.

### D2 — Global Error Boundary (`components/ErrorBoundary.tsx`)

Create a React error boundary component:

```typescript
import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex flex-col items-center justify-center h-full gap-4 text-text-secondary">
          <p className="text-lg">Something went wrong loading this page.</p>
          <p className="text-sm text-text-tertiary">{this.state.error?.message}</p>
          <button
            className="px-4 py-2 bg-accent text-white rounded"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### D3 — Wire Error Boundary into app

Wrap the router outlet (or each page route) with the error boundary. Two levels:

**Level 1 — Global (in `AppShell.tsx` or `AppRouter.tsx`):**
Wrap the `<Outlet />` so any page crash shows the fallback instead of a blank screen.

```tsx
<ErrorBoundary>
  <Outlet />
</ErrorBoundary>
```

**Level 2 — Per-widget (optional, recommended for Dashboard):**
Wrap individual dashboard widgets (StatCards, EquityCurve, StrategyStatusList, ActivityFeed) so one widget crash doesn't kill the whole page:

```tsx
<ErrorBoundary fallback={<div className="text-text-secondary p-4">Failed to load stats</div>}>
  <StatCards />
</ErrorBoundary>
```

Both levels must be implemented. Level 1 is the safety net. Level 2 provides graceful degradation on Dashboard.

### D4 — Fix Dashboard page crash

The crash is in `StatCards.tsx:42` calling `formatPercent()` on a non-number value.

Two fixes needed:

**Fix 4a:** The formatter fix (D1) prevents the crash.

**Fix 4b:** `StatCards.tsx` should also handle the case where the API response (`/api/v1/portfolio/summary`) returns null, is loading, or has missing fields. Check:
- What does `useQuery` return when the API returns an error or empty data?
- Are the stat card values accessed with optional chaining? e.g., `data?.drawdownPercent` not `data.drawdownPercent`
- Is there a loading state shown while the query is pending?

The component should render skeleton loaders while loading, and show `'—'` values if the response has null fields. It should NEVER pass raw API response values directly to formatters without the response being loaded.

### D5 — Fix Portfolio page crash

The Portfolio page (`/portfolio`) renders as a blank black screen. Same class of bug — a component or formatter crashes on null data.

**Investigation steps for the builder:**
1. Open `pages/Portfolio.tsx` (or equivalent)
2. Check which components it renders and which API calls they make
3. Add optional chaining on all data access from useQuery responses
4. Ensure all components handle `isLoading`, `isError`, and `data === undefined` states
5. Specifically check: EquityCurve, PositionTable, PnlCalendar, any component using formatCurrency/formatPercent

**Required outcome:** `/portfolio` renders with empty states when there's no data. No crash.

### D6 — Fix Risk page crash

The Risk page (`/risk`) renders as a blank black screen.

**Investigation steps for the builder:**
1. Open `pages/Risk.tsx`
2. Check RiskConfigSummary, KillSwitch, exposure charts, stat cards
3. The risk stat cards likely call formatPercent on null drawdown/exposure values
4. Add null guards on all data access
5. Ensure kill switch component handles the case where `/api/v1/risk/kill-switch/status` returns an error

**Required outcome:** `/risk` renders with empty states and the kill switch control visible. No crash.

### D7 — Fix Settings page crash

The Settings page (`/settings`) renders as a blank black screen.

**Investigation steps for the builder:**
1. Open `pages/Settings.tsx`
2. Check which tab components crash — likely the risk config tab or the audit history tab (added in TASK-022 FIX-F14)
3. The audit history query (`GET /risk/config/audit`) may return 404 or an unexpected shape
4. Add error handling on all queries
5. Each tab should render independently — one failing tab should not crash the others

**Required outcome:** `/settings` renders all tabs. Tabs with no data show appropriate empty states. No crash.

### D8 — Fix strategy save validation error

Creating a strategy via the builder form fails with "VALIDATION REQUEST FAILED".

**Investigation steps for the builder:**
1. Open browser Network tab, attempt a strategy save, check the POST request to `/api/v1/strategies`
2. Check the request payload — does the frontend send camelCase or snake_case keys?
3. Check the response body — what validation error does the backend return?
4. Common causes:
   - camelCase/snake_case mismatch (frontend sends `stopLoss`, backend expects `stop_loss`)
   - Missing required field (backend requires a field the form doesn't populate)
   - Enum value mismatch (form sends a value the backend enum doesn't accept)
   - Nested object structure wrong (conditions, position sizing config)
5. Fix the form submission to match the backend's expected schema

**If the bug is in the frontend's request payload:** fix it.
**If the bug is in the backend's validation being too strict:** document it in BUILDER_OUTPUT.md but do NOT modify backend code. This task is frontend-only.

**Required outcome:** Saving a draft strategy with basic fields (name, market, timeframe, at least one symbol) succeeds. The strategy appears in the list.

### D9 — Fix 404 page

Unknown routes should render a static "Page not found" message, not attempt to load data or crash.

**Check:**
1. Does a catch-all `*` route exist in the router config?
2. Does the 404 component try to fetch data (it shouldn't)?
3. Does it render a simple message with a link back to Dashboard?

If no 404 route exists, create one:
```tsx
// pages/NotFound.tsx
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-text-secondary">
      <h1 className="text-4xl font-bold">404</h1>
      <p>Page not found.</p>
      <a href="/dashboard" className="text-accent hover:underline">Back to Dashboard</a>
    </div>
  );
}
```

Wire it as the last route: `<Route path="*" element={<NotFound />} />`

**Required outcome:** Navigating to `/asdfasdf` shows "404 — Page not found" with a link back. No crash, no data loading.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Every function in `formatters.ts` handles null, undefined, NaN, and string inputs without throwing |
| AC2 | Formatters return `'—'` (em dash) for null/undefined/NaN values |
| AC3 | Formatters convert string-number values (e.g. `"12.5"`) to numbers before formatting |
| AC4 | `ErrorBoundary` component exists and renders fallback UI on component crash |
| AC5 | Error boundary wraps router outlet (Level 1 — global safety net) |
| AC6 | Error boundary wraps individual Dashboard widgets (Level 2 — per-widget) |
| AC7 | Dashboard page renders without crashing (stat cards show `'—'` when no data) |
| AC8 | Portfolio page renders without crashing (shows empty/loading states) |
| AC9 | Risk page renders without crashing (shows empty/loading states, kill switch visible) |
| AC10 | Settings page renders without crashing (all tabs accessible) |
| AC11 | Strategy save (draft) succeeds — strategy appears in list |
| AC12 | 404 route exists and renders static "Page not found" UI |
| AC13 | No blank black screens on any page |
| AC14 | No unhandled `TypeError` or `ReferenceError` in browser console on any page |
| AC15 | No backend code modified |
| AC16 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/ErrorBoundary.tsx` | React error boundary with fallback UI |
| `frontend/src/pages/NotFound.tsx` | 404 page (if it doesn't already exist) |

## Files to Modify

| File | What Changes |
|------|-------------|
| `frontend/src/lib/formatters.ts` | Null-guard every function, add `toNumber` helper |
| `frontend/src/layouts/AppShell.tsx` (or wherever `<Outlet />` lives) | Wrap outlet in ErrorBoundary |
| `frontend/src/pages/Dashboard.tsx` | Wrap widgets in per-widget ErrorBoundary |
| `frontend/src/features/dashboard/StatCards.tsx` | Optional chaining on data access, loading state |
| `frontend/src/pages/Portfolio.tsx` | Null guards, loading/empty states |
| `frontend/src/pages/Risk.tsx` | Null guards, loading/empty states |
| `frontend/src/pages/Settings.tsx` | Null guards, error handling on audit query |
| `frontend/src/app/router.tsx` (or equivalent) | Add 404 catch-all route, fix strategy save if needed |
| Strategy form submission file (likely `StrategyForm.tsx` or similar) | Fix payload to match backend schema |

## Files NOT to Touch

- Anything under `backend/`
- Anything under `studio/`
- `docker-compose.yml`, `Dockerfile.*`, `scripts/*`

---

## Debugging Guidance for Builder

**For blank-screen pages (Dashboard, Portfolio, Risk, Settings):**
1. Look at the page component and identify which child components it renders
2. For each child: check what useQuery hook it calls and what fields it accesses on the response
3. Add `?.` (optional chaining) everywhere data from useQuery is accessed
4. Ensure every component checks `isLoading` and `isError` before accessing `data`
5. After fixing, verify the page renders with empty states (no data in database is expected)

**For strategy save:**
1. Use browser Network tab to see the exact request payload and error response
2. The backend error response body will tell you exactly which field failed validation
3. Most likely fix: transform the form data before POST (e.g., camelCase → snake_case, or restructure nested objects)

**Testing approach:**
1. Boot the app with no data in the database (fresh Postgres)
2. Every page should render without crashing
3. All pages should show loading skeletons briefly, then empty states
4. Strategy form → fill minimal fields → Save Draft → should succeed
5. Navigate to every route in the sidebar
6. Navigate to a garbage URL → should show 404 page

---

## References

- frontend_specs.md §11 — Loading, Empty, and Error States ("Never show a blank screen")
- frontend_specs.md §9 — API Client
- Console error: `formatters.ts:18 Uncaught TypeError: value.toFixed is not a function at formatPercent`
- Console error: `StatCards.tsx:42` crash propagating through entire component tree
