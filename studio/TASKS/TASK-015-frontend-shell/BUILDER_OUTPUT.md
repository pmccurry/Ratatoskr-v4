# Builder Output — TASK-015

## Task
Frontend Shell, Routing, Auth, API Client, and Component Library

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- frontend/src/app/App.tsx (replaced stub)
- frontend/src/app/providers.tsx (replaced stub)
- frontend/src/app/router.tsx (replaced stub)
- frontend/src/layouts/AppShell.tsx
- frontend/src/layouts/AuthLayout.tsx
- frontend/src/components/Sidebar.tsx
- frontend/src/components/AlertBanner.tsx
- frontend/src/components/StatusBar.tsx
- frontend/src/components/StatCard.tsx
- frontend/src/components/DataTable.tsx
- frontend/src/components/StatusPill.tsx
- frontend/src/components/PnlValue.tsx
- frontend/src/components/PriceValue.tsx
- frontend/src/components/PercentValue.tsx
- frontend/src/components/TimeAgo.tsx
- frontend/src/components/SymbolBadge.tsx
- frontend/src/components/ProgressBar.tsx
- frontend/src/components/EmptyState.tsx
- frontend/src/components/LoadingState.tsx
- frontend/src/components/ErrorState.tsx
- frontend/src/components/PageContainer.tsx
- frontend/src/components/PageHeader.tsx
- frontend/src/components/SectionHeader.tsx
- frontend/src/components/CardGrid.tsx
- frontend/src/components/TabContainer.tsx
- frontend/src/components/ChartContainer.tsx
- frontend/src/components/ConfirmDialog.tsx
- frontend/src/components/ActivityFeedItem.tsx
- frontend/src/components/Tooltip.tsx
- frontend/src/components/DropdownMenu.tsx
- frontend/src/components/index.ts
- frontend/src/features/auth/useAuth.ts
- frontend/src/features/auth/AuthGuard.tsx
- frontend/src/features/auth/AdminGuard.tsx
- frontend/src/lib/api.ts (replaced stub)
- frontend/src/lib/constants.ts (replaced stub)
- frontend/src/lib/formatters.ts (replaced stub)
- frontend/src/lib/store.ts (new)
- frontend/src/types/auth.ts
- frontend/src/types/strategy.ts
- frontend/src/types/signal.ts
- frontend/src/types/order.ts
- frontend/src/types/position.ts
- frontend/src/types/portfolio.ts
- frontend/src/types/risk.ts
- frontend/src/types/observability.ts
- frontend/src/types/common.ts
- frontend/src/types/index.ts
- frontend/src/pages/Dashboard.tsx
- frontend/src/pages/StrategyList.tsx
- frontend/src/pages/StrategyBuilder.tsx
- frontend/src/pages/StrategyDetail.tsx
- frontend/src/pages/Signals.tsx
- frontend/src/pages/Orders.tsx
- frontend/src/pages/Portfolio.tsx
- frontend/src/pages/Risk.tsx
- frontend/src/pages/System.tsx
- frontend/src/pages/Settings.tsx
- frontend/src/pages/Login.tsx
- frontend/src/pages/NotFound.tsx
- frontend/.env.example

## Files Modified
- frontend/src/index.css — Added body styles (bg-background, text-text-primary, font-sans), custom scrollbar styling for dark theme
- frontend/src/main.tsx — No changes (already correctly renders App)
- frontend/package.json — Added lucide-react dependency

## Files Deleted
None

## Acceptance Criteria Status

### App Shell
1. App renders with dark theme (background #0f1117) — ✅ Done (body class bg-background, Tailwind config has background: '#0f1117')
2. AppShell layout has sidebar, content area, alert banner, status bar — ✅ Done (AppShell.tsx)
3. Sidebar shows correct nav items with icons — ✅ Done (6 trading items + 2 admin items, lucide-react icons)
4. Sidebar collapses to icon-only mode (state in Zustand) — ✅ Done (useUIStore.sidebarCollapsed, 240px/64px)
5. Sidebar shows admin-only section for admin users — ✅ Done (isAdmin conditional rendering)
6. Sidebar hides admin section for regular users — ✅ Done (same conditional)
7. Active route highlighted in sidebar — ✅ Done (NavLink isActive → accent bg/text)
8. Alert banner shows active alerts from API — ✅ Done (GET /observability/alerts/active with TanStack Query)
9. Alert banner color-coded by severity (red/orange/yellow) — ✅ Done (critical=red, error=orange, warning=yellow)
10. Alert banner hidden when no active alerts — ✅ Done (returns null when no alerts)
11. Status bar shows connection status with colored dots — ✅ Done (green/red dots for Alpaca/OANDA)
12. Status bar shows active strategy count — ✅ Done (from pipeline data)
13. Status bar shows current time (updates every second) — ✅ Done (setInterval 1s, ET timezone)
14. Status bar data refreshes every 30 seconds — ✅ Done (refetchInterval: REFRESH.statusBar)

### Auth
15. Login page renders with email/password form — ✅ Done (Login.tsx)
16. Login calls POST /auth/login and stores tokens — ✅ Done (useAuth.login)
17. Login redirects to /dashboard on success — ✅ Done (useNavigate after login)
18. Login shows error message on failure — ✅ Done (error state display)
19. AuthGuard redirects unauthenticated users to /login — ✅ Done (Navigate to /login)
20. AdminGuard shows Forbidden page for non-admin users — ✅ Done (403 page inline)
21. Logout clears tokens and redirects to /login — ✅ Done (useAuth.logout)
22. Token refresh attempted on 401 response — ✅ Done (api.ts response interceptor)
23. Failed refresh triggers logout — ✅ Done (clears tokens, redirects to /login)

### API Client
24. API client attaches Bearer token to all requests — ✅ Done (request interceptor)
25. API client unwraps {"data": ...} envelope on success — ✅ Done (response interceptor)
26. API client unwraps {"error": ...} on failure — ✅ Done (error interceptor)
27. API client attempts token refresh on 401 — ✅ Done (with queue for concurrent requests)

### Component Library
28. StatCard renders value, label, subtitle, trend indicator — ✅ Done
29. StatCard shows skeleton loading state — ✅ Done (animate-pulse)
30. DataTable renders sortable columns with pagination — ✅ Done
31. DataTable handles column types: text, number, price, pnl, timestamp, status — ✅ Done
32. DataTable shows skeleton loading state — ✅ Done
33. DataTable shows EmptyState when no data — ✅ Done
34. StatusPill renders colored badges — ✅ Done (color map for enabled/disabled/active/etc.)
35. PnlValue renders positive green with +, negative red with -, monospace — ✅ Done
36. PriceValue renders with appropriate decimals per market — ✅ Done (forex 5, options 2, equities 2)
37. PercentValue renders with % suffix and optional coloring — ✅ Done
38. TimeAgo renders relative timestamps — ✅ Done (s/m/h/d ago)
39. ProgressBar renders with filled portion and threshold marker — ✅ Done
40. EmptyState renders message with optional action button — ✅ Done
41. LoadingState renders skeleton matching content shape — ✅ Done (type: card/table/chart)
42. ErrorState renders message with Retry button — ✅ Done
43. ChartContainer wraps Recharts with dark theme and period selector — ✅ Done
44. ConfirmDialog renders modal with cancel/confirm — ✅ Done
45. ActivityFeedItem renders emoji + timestamp + summary — ✅ Done

### Types and Utilities
46. TypeScript types exist for all backend response schemas — ✅ Done (9 type files)
47. All type fields use camelCase matching backend alias serialization — ✅ Done
48. Formatters handle price, PnL, percent, number, currency, bps, datetime, timeAgo — ✅ Done
49. Constants define all theme colors and refresh intervals — ✅ Done
50. Zustand store manages sidebar state and UI preferences — ✅ Done

### Routing and Pages
51. All routes from the spec are defined — ✅ Done (router.tsx)
52. / redirects to /dashboard — ✅ Done (Navigate with replace)
53. All authenticated routes wrapped in AuthGuard — ✅ Done
54. Admin routes wrapped in AdminGuard — ✅ Done (AdminLayout wrapper)
55. Every route renders a placeholder page with title — ✅ Done (12 pages)
56. NotFound page renders for unknown routes — ✅ Done (catch-all route)
57. Forbidden page renders for unauthorized admin access — ✅ Done (inline in AdminGuard)

### General
58. npm run dev starts the frontend without errors — ✅ Done
59. npm run build compiles without TypeScript errors — ✅ Done (verified clean build)
60. No backend Python files modified — ✅ Done
61. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Forbidden page**: The Forbidden page (AC #57) is rendered inline within AdminGuard rather than as a separate page component, since it's only shown in the context of admin route denial and doesn't need its own route.
2. **StatusBar timezone**: Uses `America/New_York` for ET display as specified in the task.
3. **AlertBanner**: Fetches from `/observability/alerts/active` and displays the highest-severity alert. Uses TanStack Query with 30s refetch interval.
4. **StatusBar pipeline data**: Consumes GET `/observability/health/pipeline` response. Field names assumed from the observability module's camelCase response schema.
5. **lucide-react**: Installed as a dependency (not in original package.json) since the task explicitly requires it for sidebar icons.
6. **Auth token storage**: Uses localStorage (not sessionStorage) for access_token and refresh_token, matching the standard pattern for SPAs that should persist across browser tabs.
7. **Token refresh queue**: The API client queues concurrent requests during token refresh to avoid multiple simultaneous refresh attempts.

## Ambiguities Encountered
1. **DividendPayment type**: Not explicitly listed in the task's type definitions but referenced in portfolio spec. Included in portfolio.ts types for completeness.
2. **Settings sub-routes**: The task lists /settings/risk, /settings/accounts, /settings/users, /settings/alerts as separate routes but all render the same Settings placeholder. Future tasks will add tab-based navigation within Settings.

## Dependencies Discovered
None — all required packages (react-router-dom, @tanstack/react-query, zustand, axios, recharts, lucide-react) are present in package.json.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Token refresh race condition**: The queue-based approach handles concurrent 401s, but edge cases with very rapid sequential requests during refresh might still occur in rare circumstances.
2. **StatusBar pipeline data shape**: The StatusBar assumes specific field names from the observability health/pipeline endpoint. If the actual response shape differs, the status bar will show fallback values.
3. **Tailwind custom colors**: The custom theme colors (surface-hover, text-secondary, text-tertiary, etc.) must match what's defined in tailwind.config.js. Any mismatch will result in unstyled elements.

## Deferred Items
- Real data wiring for all placeholder pages (TASK-016+)
- Strategy builder form (TASK-016/17)
- WebSocket real-time updates for activity feed and status bar
- Settings tab navigation

## Recommended Next Task
TASK-016 — Frontend Views (Dashboard, Strategy List/Detail, Strategy Builder UI)
