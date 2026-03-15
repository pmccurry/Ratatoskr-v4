# TASK-015 — Frontend Shell, Routing, Auth, API Client, and Component Library

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Build the frontend foundation: the app shell (sidebar navigation, alert
banner, status bar), authentication flow (login, token management, route
guards), the API client, the shared component library, TypeScript types
for all backend models, formatters, and placeholder pages for every route.

After this task:
- The app renders with a working dark theme
- Users can log in and see the navigation
- The sidebar collapses/expands with correct nav items (user vs admin)
- The alert banner shows active alerts from the observability API
- The status bar shows connection status, active strategies, and current time
- AuthGuard redirects unauthenticated users to login
- AdminGuard blocks non-admin users from system/settings routes
- The API client attaches auth tokens, unwraps response envelopes, and refreshes tokens on 401
- All shared components exist (StatCard, DataTable, StatusPill, PnlValue, etc.)
- Every route renders a placeholder page (content filled in by later tasks)
- TypeScript types match all backend response schemas

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/frontend_specs.md — PRIMARY SPEC, sections 1-4, 6-12
5. /studio/SPECS/cross_cutting_specs.md — API envelope format, pagination format

## Constraints

- Do NOT implement full view content (only placeholder pages with titles)
- Do NOT implement the strategy builder form
- Do NOT implement data tables with real data (component exists, not wired)
- Do NOT implement charts with real data (component exists, not wired)
- Do NOT create backend code or modify any Python files
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify root /CLAUDE.md
- Use React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS
- Use shadcn/ui patterns for base components where useful
- Desktop-first responsive behavior

---

## Deliverables

### 1. App Entry Point (frontend/src/app/App.tsx)

Replace the placeholder with the full app root:

```typescript
// Wraps the app in providers: QueryClientProvider, Zustand is auto, BrowserRouter
// Renders the router
```

### 2. Providers (frontend/src/app/providers.tsx)

```typescript
// QueryClient configuration:
//   defaultOptions.queries.staleTime = 30_000
//   defaultOptions.queries.retry = 1
//   defaultOptions.queries.refetchOnWindowFocus = true

// Export a Providers component that wraps children in QueryClientProvider
```

### 3. Router (frontend/src/app/router.tsx)

All routes from the spec:

```typescript
/                        → redirect to /dashboard
/login                   → Login page (AuthLayout)

// Protected routes (AppShell layout, AuthGuard):
/dashboard               → Dashboard placeholder
/strategies              → StrategyList placeholder
/strategies/new          → StrategyBuilder placeholder
/strategies/:id          → StrategyDetail placeholder
/strategies/:id/edit     → StrategyBuilder placeholder (edit mode)
/signals                 → Signals placeholder
/orders                  → Orders placeholder
/portfolio               → Portfolio placeholder
/risk                    → Risk placeholder

// Admin routes (AppShell layout, AdminGuard):
/system                  → System placeholder
/settings                → Settings placeholder
/settings/risk           → Settings placeholder
/settings/accounts       → Settings placeholder
/settings/users          → Settings placeholder
/settings/alerts         → Settings placeholder

// Error routes:
*                        → NotFound page
```

### 4. App Shell Layout (frontend/src/layouts/AppShell.tsx)

The primary layout wrapping all authenticated routes:

```
┌──────────────────────────────────────────────┐
│  AlertBanner (if active alerts exist)         │
├────────┬─────────────────────────────────────┤
│        │                                     │
│ Sidebar│       <Outlet />                    │
│        │                                     │
├────────┴─────────────────────────────────────┤
│  StatusBar                                    │
└──────────────────────────────────────────────┘
```

- Sidebar and content area flex horizontally
- Alert banner sits above, full width
- Status bar sits below, full width
- Sidebar width: 240px expanded, 64px collapsed
- Content area gets remaining width with page padding (24px)

### 5. Sidebar Navigation (within AppShell or separate component)

Collapsible sidebar with icon + label (expanded) or icon-only (collapsed).

```
Trading Section (all users):
  📊  Dashboard         /dashboard
  📈  Strategies        /strategies
  ⚡  Signals           /signals
  📝  Orders            /orders
  💼  Portfolio         /portfolio
  🛡️  Risk              /risk

System Section (admin only, visually separated):
  📡  System            /system
  ⚙️  Settings          /settings

Footer:
  Collapse/expand toggle
  User menu (username, role badge, logout button)
```

Use lucide-react icons (LayoutDashboard, LineChart, Zap, FileText,
Briefcase, Shield, Monitor, Settings, ChevronLeft/Right, User, LogOut).

Active route: highlighted with accent background.
Hover: surface-hover background.
Collapsed state stored in Zustand UI store.

### 6. Alert Banner (frontend/src/components/AlertBanner.tsx)

```typescript
// Fetches active alerts from GET /api/v1/observability/alerts/active
// Displays the highest-severity active alert
// Color-coded: red (critical), orange (error), yellow (warning)
// Shows summary text + "View All" link → /system
// Critical/error: persistent (requires acknowledgment)
// Warning: dismissible (X button)
// Hidden when no active alerts
// Refreshes every 30 seconds
```

### 7. Status Bar (frontend/src/components/StatusBar.tsx)

Always-visible bottom bar:

```
● Alpaca Connected  ● OANDA Connected  |  Last bar: 3s ago  |  8 strategies active  |  14:30:12 ET
```

- Green dot for connected, red for disconnected
- Data from GET /api/v1/observability/health/pipeline
- Refreshes every 30 seconds
- Time shows in ET (US/Eastern), updates every second

### 8. Auth Layout (frontend/src/layouts/AuthLayout.tsx)

Simple centered layout for the login page (no sidebar, no status bar).
Dark background, centered card.

### 9. Login Page (frontend/src/pages/Login.tsx)

```
┌─────────────────────────────────┐
│   Ratatoskr Trading Platform    │
│                                 │
│   Email:    [____________]      │
│   Password: [____________]      │
│                                 │
│        [  Log In  ]             │
│                                 │
│   Error message if login fails  │
└─────────────────────────────────┘
```

- Calls POST /api/v1/auth/login with email + password
- On success: stores tokens, redirects to /dashboard
- On error: shows error message (invalid credentials, account locked, etc.)
- Submit on Enter key
- Disabled button while loading

### 10. Auth Hook (frontend/src/features/auth/useAuth.ts)

```typescript
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

// Token storage: localStorage for access_token and refresh_token
// On login: store both tokens, fetch user profile (GET /auth/me)
// On logout: call POST /auth/logout, clear tokens, redirect to /login
// On 401: attempt token refresh, if fails → logout
```

### 11. Auth Guards (frontend/src/features/auth/)

**AuthGuard.tsx:**
```typescript
// Wraps protected routes
// If not authenticated → redirect to /login
// If authenticated → render children
// Shows loading state while checking auth
```

**AdminGuard.tsx:**
```typescript
// Wraps admin routes
// If not admin → show Forbidden page
// If admin → render children
```

### 12. API Client (frontend/src/lib/api.ts)

```typescript
// axios instance with:
//   baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1'
//   Content-Type: application/json
//
// Request interceptor: attach Bearer token from localStorage
//
// Response interceptor:
//   Success: unwrap { data: ... } envelope → return the inner data
//   401 error: attempt token refresh, retry original request
//   Other errors: unwrap { error: { code, message, details } }
//
// Export typed API methods:
//   api.get<T>(url, params?) → T
//   api.post<T>(url, body?) → T
//   api.put<T>(url, body?) → T
//   api.delete<T>(url) → T
```

### 13. TypeScript Types (frontend/src/types/)

Create type files matching all backend response schemas.
All use camelCase field names (matching the backend's alias serialization).

**auth.ts:**
```typescript
interface User {
  id: string;
  email: string;
  username: string;
  role: 'admin' | 'user';
  status: string;
  lastLoginAt: string | null;
  createdAt: string;
}

interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}
```

**strategy.ts:**
```typescript
interface Strategy { id, key, name, description, type, status, currentVersion, market, autoPauseErrorCount, lastEvaluatedAt, createdAt, updatedAt }
interface StrategyDetail extends Strategy { config: StrategyConfig }
interface StrategyConfig { /* full config structure */ }
interface StrategyEvaluation { id, strategyId, strategyVersion, evaluatedAt, symbolsEvaluated, signalsEmitted, exitsTriggered, errors, durationMs, status, skipReason, createdAt }
interface IndicatorDefinition { key, name, category, params: IndicatorParam[], outputs: string[], description }
interface IndicatorParam { name, type, default, min?, max?, options? }
interface Condition { left: Operand, operator: string, right: Operand }
interface ConditionGroup { logic: 'and' | 'or', conditions: (Condition | ConditionGroup)[] }
interface Operand { type: 'indicator' | 'formula' | 'value' | 'range', indicator?, params?, output?, expression?, value?, min?, max? }
```

**signal.ts:**
```typescript
interface Signal { id, strategyId, strategyVersion, symbol, market, timeframe, side, signalType, source, confidence, status, payloadJson, positionId, exitReason, ts, expiresAt, createdAt }
interface SignalStats { total, byStatus, byStrategy, bySymbol, bySignalType, bySource }
```

**order.ts:**
```typescript
interface PaperOrder { id, signalId, riskDecisionId, strategyId, symbol, market, side, orderType, signalType, requestedQty, requestedPrice, filledQty, filledAvgPrice, status, rejectionReason, executionMode, brokerOrderId, brokerAccountId, contractMultiplier, submittedAt, filledAt, createdAt }
interface PaperFill { id, orderId, strategyId, symbol, side, qty, referencePrice, price, grossValue, fee, slippageBps, slippageAmount, netValue, filledAt, createdAt }
```

**position.ts:**
```typescript
interface Position { id, strategyId, symbol, market, side, qty, avgEntryPrice, costBasis, currentPrice, marketValue, unrealizedPnl, unrealizedPnlPercent, realizedPnl, totalFees, totalDividendsReceived, totalReturn, totalReturnPercent, status, openedAt, closedAt, closeReason, barsHeld, contractMultiplier, createdAt }
```

**portfolio.ts:**
```typescript
interface PortfolioSummary { equity, cash, positionsValue, unrealizedPnl, realizedPnlTotal, totalReturn, totalReturnPercent, drawdownPercent, peakEquity, openPositionsCount }
interface EquityBreakdown { totalEquity, totalCash, totalPositionsValue, equitiesCash, equitiesPositionsValue, forexCash, forexPositionsValue }
interface CashBalance { accountScope: string, balance: number }
interface PortfolioSnapshot { id, ts, cashBalance, positionsValue, equity, unrealizedPnl, realizedPnlToday, realizedPnlTotal, drawdownPercent, peakEquity, openPositionsCount, snapshotType, createdAt }
interface RealizedPnlEntry { id, positionId, strategyId, symbol, market, side, qtyClosed, entryPrice, exitPrice, grossPnl, fees, netPnl, pnlPercent, holdingPeriodBars, closedAt }
interface PerformanceMetrics { totalReturn, totalReturnPercent, totalPnl, winRate, profitFactor, averageWinner, averageLoser, riskRewardRatio, maxDrawdown, sharpeRatio, sortinoRatio, averageHoldBars, longestWinStreak, longestLossStreak, totalTrades, totalFees, totalDividendIncome }
```

**risk.ts:**
```typescript
interface RiskDecision { id, signalId, status, checksPassed, failedCheck, reasonCode, reasonText, modificationsJson, portfolioStateSnapshot, ts, createdAt }
interface RiskOverview { killSwitch, drawdown, dailyLoss, totalExposure, symbolExposure, strategyExposure, recentDecisions }
interface RiskConfig { maxPositionSizePercent, maxSymbolExposurePercent, maxStrategyExposurePercent, maxTotalExposurePercent, maxDrawdownPercent, maxDrawdownCatastrophicPercent, maxDailyLossPercent, minPositionValue, updatedAt }
```

**observability.ts:**
```typescript
interface AuditEvent { id, eventType, category, severity, sourceModule, entityType, entityId, strategyId, symbol, summary, detailsJson, ts, createdAt }
interface AlertInstance { id, ruleId, severity, summary, detailsJson, status, triggeredAt, acknowledgedAt, resolvedAt }
interface AlertRule { id, name, description, category, conditionType, conditionConfig, severity, enabled, cooldownSeconds, notificationChannels }
interface SystemHealth { overallStatus, uptimeSeconds, modules, pipeline }
```

**common.ts:**
```typescript
interface PaginatedResponse<T> {
  data: T[];
  pagination: { page: number; pageSize: number; totalItems: number; totalPages: number };
}

interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}
```

### 14. Formatters (frontend/src/lib/formatters.ts)

```typescript
formatPrice(value: number, market?: string): string
  // equities: $192.30  forex: 1.09230  options: $3.45

formatPnl(value: number): string
  // +$1,234.56 (green) or -$567.89 (red)

formatPercent(value: number, decimals?: number): string
  // +3.85% or -0.26%

formatNumber(value: number): string
  // 1,234,567

formatCurrency(value: number): string
  // $1,234.56

formatBasisPoints(value: number): string
  // 5bps

formatDateTime(value: string): string
  // Mar 14, 2026 14:30

formatTimeAgo(value: string): string
  // "12s ago", "5m ago", "2h ago"

formatDecimal(value: string | number, decimals: number): string
  // Handles string Decimals from API
```

### 15. Constants (frontend/src/lib/constants.ts)

```typescript
// Colors (matching Tailwind config)
export const COLORS = {
  background: '#0f1117',
  surface: '#1a1d27',
  surfaceHover: '#22252f',
  border: '#2a2d3a',
  borderStrong: '#3a3d4a',
  textPrimary: '#e4e4e7',
  textSecondary: '#a1a1aa',
  textTertiary: '#71717a',
  accent: '#3b82f6',
  accentHover: '#2563eb',
  success: '#22c55e',
  warning: '#eab308',
  error: '#ef4444',
  info: '#6366f1',
};

// Refresh intervals (ms)
export const REFRESH = {
  activityFeed: 10_000,
  signals: 10_000,
  positions: 30_000,
  riskOverview: 30_000,
  portfolioSummary: 60_000,
  strategyList: 60_000,
  equityCurve: 300_000,
  systemHealth: 10_000,
  statusBar: 30_000,
  alertBanner: 30_000,
};

// Stale times (ms)
export const STALE = {
  indicatorCatalog: 3_600_000,
  // ... etc matching spec
};
```

### 16. Zustand UI Store (frontend/src/lib/store.ts)

```typescript
interface UIStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  
  equityCurvePeriod: '1d' | '7d' | '30d' | '90d' | 'all';
  setEquityCurvePeriod: (period: string) => void;
  
  activityFeedPaused: boolean;
  toggleActivityFeed: () => void;
  
  // Per-view filter states can be added as views are built
}
```

### 17. Shared Components (frontend/src/components/)

Implement all components from spec section 6. Each component should:
- Accept props for data and configuration
- Handle loading state (skeleton)
- Handle empty state
- Use Tailwind classes matching the theme
- Use monospace font for financial numbers

**Required components:**

Layout: PageContainer, PageHeader, SectionHeader, CardGrid, TabContainer
Data display: StatCard, DataTable, StatusPill, ProgressBar, PnlValue,
  PriceValue, PercentValue, TimeAgo, SymbolBadge, EmptyState, LoadingState, ErrorState
Interactive: ConfirmDialog, AlertBanner (already in layout), ActivityFeedItem,
  ChartContainer, Tooltip, DropdownMenu

**DataTable specifics:**
- Sortable columns (click header to sort)
- Column type rendering: text, number, price (PriceValue), pnl (PnlValue),
  timestamp (TimeAgo), status (StatusPill)
- Pagination controls (page, page size, total)
- Optional expandable rows
- Loading state: skeleton rows
- Empty state: EmptyState component

**StatCard specifics:**
- Value (large, monospace for numbers)
- Label (small, secondary text)
- Subtitle (optional, tertiary text)
- Trend indicator (up arrow green, down arrow red, optional)
- Optional progress bar below
- Loading state: pulsing rectangles

**ChartContainer specifics:**
- Recharts wrapper with dark theme colors from constants
- Period selector (1D, 7D, 30D, 90D, ALL)
- Loading state: pulsing rectangle
- Empty state: "No data available"

### 18. Placeholder Pages (frontend/src/pages/)

Create placeholder page components for every route. Each shows:
- PageHeader with the page title
- A brief description of what the page will contain
- An EmptyState or simple message

Pages to create:
```
Dashboard.tsx       — "Dashboard Home — overview coming in TASK-016"
StrategyList.tsx    — "Strategies — list coming in TASK-017"
StrategyBuilder.tsx — "Strategy Builder — form coming in TASK-017"
StrategyDetail.tsx  — "Strategy Detail — coming in TASK-017"
Signals.tsx         — "Signals — table coming in TASK-018"
Orders.tsx          — "Orders & Fills — tables coming in TASK-018"
Portfolio.tsx       — "Portfolio — positions coming in TASK-019"
Risk.tsx            — "Risk Dashboard — coming in TASK-020"
System.tsx          — "System Telemetry — coming in TASK-020"
Settings.tsx        — "Settings — configuration coming in TASK-020"
NotFound.tsx        — "404 — Page not found" with link to dashboard
Forbidden.tsx       — "403 — Access denied" with link to dashboard
```

### 19. Environment Config

Create/update frontend/.env.example:
```
VITE_API_BASE_URL=/api/v1
```

---

## Acceptance Criteria

### App Shell
1. App renders with dark theme (background #0f1117)
2. AppShell layout has sidebar, content area, alert banner, status bar
3. Sidebar shows correct nav items with icons
4. Sidebar collapses to icon-only mode (state in Zustand)
5. Sidebar shows admin-only section for admin users
6. Sidebar hides admin section for regular users
7. Active route highlighted in sidebar
8. Alert banner shows active alerts from API
9. Alert banner color-coded by severity (red/orange/yellow)
10. Alert banner hidden when no active alerts
11. Status bar shows connection status with colored dots
12. Status bar shows active strategy count
13. Status bar shows current time (updates every second)
14. Status bar data refreshes every 30 seconds

### Auth
15. Login page renders with email/password form
16. Login calls POST /auth/login and stores tokens
17. Login redirects to /dashboard on success
18. Login shows error message on failure
19. AuthGuard redirects unauthenticated users to /login
20. AdminGuard shows Forbidden page for non-admin users
21. Logout clears tokens and redirects to /login
22. Token refresh attempted on 401 response
23. Failed refresh triggers logout

### API Client
24. API client attaches Bearer token to all requests
25. API client unwraps {"data": ...} envelope on success
26. API client unwraps {"error": ...} on failure
27. API client attempts token refresh on 401

### Component Library
28. StatCard renders value, label, subtitle, trend indicator
29. StatCard shows skeleton loading state
30. DataTable renders sortable columns with pagination
31. DataTable handles column types: text, number, price, pnl, timestamp, status
32. DataTable shows skeleton loading state
33. DataTable shows EmptyState when no data
34. StatusPill renders colored badges (enabled=green, disabled=gray, etc.)
35. PnlValue renders positive green with +, negative red with -, monospace
36. PriceValue renders with appropriate decimals per market
37. PercentValue renders with % suffix and optional coloring
38. TimeAgo renders relative timestamps
39. ProgressBar renders with filled portion and threshold marker
40. EmptyState renders message with optional action button
41. LoadingState renders skeleton matching content shape
42. ErrorState renders message with Retry button
43. ChartContainer wraps Recharts with dark theme and period selector
44. ConfirmDialog renders modal with cancel/confirm
45. ActivityFeedItem renders emoji + timestamp + summary

### Types and Utilities
46. TypeScript types exist for all backend response schemas (auth, strategy, signal, order, position, portfolio, risk, observability)
47. All type fields use camelCase matching backend alias serialization
48. Formatters handle price, PnL, percent, number, currency, bps, datetime, timeAgo
49. Constants define all theme colors and refresh intervals
50. Zustand store manages sidebar state and UI preferences

### Routing and Pages
51. All routes from the spec are defined
52. / redirects to /dashboard
53. All authenticated routes wrapped in AuthGuard
54. Admin routes wrapped in AdminGuard
55. Every route renders a placeholder page with title
56. NotFound page renders for unknown routes
57. Forbidden page renders for unauthorized admin access

### General
58. npm run dev starts the frontend without errors
59. npm run build compiles without TypeScript errors
60. No backend Python files modified
61. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-015-frontend-shell/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
