# FRONTEND_SPECS — Full Engineering Spec

## Purpose

Define the complete frontend architecture, views, components, and conventions.
This spec must contain enough detail that a builder agent can scaffold and
implement the entire frontend without asking design or layout questions.

---

## 1. Technology Stack

```
React 18+
Vite (build tool)
TypeScript (strict mode)
React Router (routing)
TanStack Query (server state / data fetching)
Zustand (UI-only local state)
Tailwind CSS (styling)
shadcn/ui (base component patterns)
Recharts (charting)
```

---

## 2. App Shell

### Layout Structure

Desktop-first sidebar navigation with main content area:

```
┌──────────────────────────────────────────────┐
│  Alert Banner (if active alerts)              │
├────────┬─────────────────────────────────────┤
│        │                                     │
│  Side  │       Main Content Area             │
│  Nav   │       (route outlet)                │
│        │                                     │
├────────┴─────────────────────────────────────┤
│  Status Bar                                   │
└──────────────────────────────────────────────┘
```

### Sidebar Navigation

Collapsible (icon-only vs expanded with labels).

```
Trading Section (all users):
  📊  Dashboard         /dashboard
  📈  Strategies        /strategies
  ⚡  Signals           /signals
  📝  Orders            /orders
  💼  Portfolio         /portfolio
  🛡️  Risk              /risk

System Section (admin only):
  📡  System            /system
  ⚙️  Settings          /settings

Footer:
  👤  User menu         (profile, logout)
```

Regular users see Trading section only.
Admin users see both sections.

### Alert Banner

Persistent bar at top when active alerts exist.
Color-coded by highest active severity:

```
Red background (#dc2626):     critical alert
Orange background (#ea580c):  error alert
Yellow background (#ca8a04):  warning alert
```

Shows most severe alert summary with "View All" link.
Warnings: dismissible. Critical/Error: persistent until acknowledged.

### Status Bar

Always-visible bottom bar showing system vitals:

```
● Alpaca Connected  ● OANDA Connected  |  Last bar: 3s ago  |  8 strategies active  |  14:30:12 ET
```

Green dot (#22c55e) for connected, red dot (#ef4444) for disconnected.
Visible on every page regardless of current view.

Data source: `GET /api/v1/observability/health/pipeline`
Refresh: every 30 seconds.

---

## 3. Theme

### Dark Mode (MVP — only theme)

```
Colors:
  Background:       #0f1117  (near-black, page background)
  Surface:          #1a1d27  (cards, panels, elevated surfaces)
  Surface hover:    #22252f  (interactive surface hover state)
  Border:           #2a2d3a  (subtle borders between sections)
  Border strong:    #3a3d4a  (emphasized borders)

  Text primary:     #e4e4e7  (near-white, main content)
  Text secondary:   #a1a1aa  (muted, labels, descriptions)
  Text tertiary:    #71717a  (very muted, timestamps, metadata)

  Accent:           #3b82f6  (blue, primary actions, links)
  Accent hover:     #2563eb  (blue hover state)

  Success:          #22c55e  (green, positive PnL, connected, approved)
  Warning:          #eab308  (yellow, warnings, caution)
  Error:            #ef4444  (red, negative PnL, disconnected, rejected)
  Info:             #6366f1  (indigo/purple, informational)

Fonts:
  Primary:          Inter, system-ui, sans-serif
  Monospace:        JetBrains Mono, ui-monospace, monospace
                    (used for all prices, numbers, PnL values)

Sizing:
  Font base:        14px
  Font small:       12px (metadata, timestamps)
  Font large:       16px (section headers)
  Font xlarge:      24px (stat card values)
  Font xxlarge:     32px (page-level metrics)

Spacing:
  Card padding:     16px (p-4)
  Section gap:      24px (gap-6)
  Page padding:     24px (p-6)
```

### Financial Number Formatting

```
Prices:       monospace, appropriate decimal places
                equities: 2 decimals ($192.30)
                forex: 4-5 decimals (1.09230)
                options: 2 decimals ($3.45)

PnL values:   monospace, always show sign, colored
                positive: green (#22c55e), prefix +
                negative: red (#ef4444), prefix -
                zero: neutral text color, no prefix

Percentages:  1-2 decimal places with % suffix
                +3.85%, -0.26%, 61%

Large numbers: comma-separated (1,000,000)
Currency:     $ prefix for USD amounts

Basis points: number + "bps" suffix (0.5bps, 5bps)
```

---

## 4. Route Structure

```
/                        → redirect to /dashboard
/login                   → login page (unauthenticated)

/dashboard               → Dashboard Home
/strategies              → Strategy List
/strategies/new          → Strategy Builder (create)
/strategies/:id          → Strategy Detail
/strategies/:id/edit     → Strategy Builder (edit)
/signals                 → Signals View
/orders                  → Paper Trading View
/portfolio               → Portfolio View
/risk                    → Risk Dashboard

/system                  → System Telemetry (admin only)
/settings                → Settings (admin only)
/settings/risk           → Risk Config (admin only)
/settings/accounts       → Broker Accounts (admin only)
/settings/users          → User Management (admin only)
/settings/alerts         → Alert Rules (admin only)
```

All routes except /login require authentication.
/system and /settings/* routes require admin role.
Unauthorized access redirects to /login.
Forbidden access (user trying admin route) shows 403 page.

---

## 5. View Specifications

### View 1 — Dashboard Home (/dashboard)

**Purpose:** High-level overview of everything on one screen.

**Layout:**

```
Row 1: Stat cards (4 cards)
  - Total Equity ($, % return)
  - Today's PnL ($, %)
  - Open Positions (count)
  - Drawdown (%, / max limit)

Row 2: Two columns
  - Left (wide): Equity curve chart (30d default, zoomable)
  - Right (narrow): Strategy status list (name, PnL, position count, status dot)

Row 3: Full width
  - Activity feed (recent events, live-updating)
```

**Data Requirements:**

```
GET /api/v1/portfolio/summary              → stat cards
GET /api/v1/portfolio/equity-curve         → chart (params: period=30d)
GET /api/v1/strategies                     → strategy list
GET /api/v1/observability/events/recent    → activity feed (limit=20)
```

**Refresh Intervals:**

```
Portfolio summary:    60 seconds
Equity curve:         300 seconds
Strategy list:        60 seconds
Activity feed:        10 seconds
```

**Interactions:**

- Stat cards are clickable links (equity→portfolio, drawdown→risk)
- Equity curve: period selector (1d, 7d, 30d, 90d, all)
- Strategy status items: click → navigate to strategy detail
- Activity feed items: click → navigate to relevant detail view
- Activity feed: auto-scroll for new events, pause on hover

---

### View 2 — Strategy List (/strategies)

**Purpose:** All strategies with status at a glance.

**Layout:**

```
Header: "Strategies" title + [+ New Strategy] button
Filters: status dropdown, market dropdown, search input
List: strategy cards with summary info
```

**Strategy Card Content:**

```
Status dot + Name + Version + Status badge
Market · Timeframe · Symbol count/mode
PnL (total) | Win rate | Open positions count
Last evaluated (TimeAgo) | Signals today count
Action buttons: [Pause/Resume] [Edit] [Detail →]
```

**Special States:**

- Paused strategies show pause reason
- Auto-paused strategies show error count and warning banner
- Draft strategies show [Enable] instead of [Pause]

**Data Requirements:**

```
GET /api/v1/strategies → list with embedded summary stats
```

---

### View 3 — Strategy Builder (/strategies/new, /strategies/:id/edit)

**Purpose:** Create or edit strategies through a config-driven form.

**Sections (scrollable single page):**

```
1. Identity
   - Name (text input)
   - Description (text area)
   - Market (radio: Equities / Forex / Both)
   - Timeframe (select: 1m, 5m, 15m, 1h, 4h)
   - Additional timeframes (multi-select, optional)

2. Symbols
   - Mode (radio: Specific / Watchlist / Filtered)
   - If Specific: symbol search/select with chips
   - If Watchlist: market dropdown
   - If Filtered: filter fields (min volume, min price)

3. Entry Conditions
   - Logic toggle (AND all / OR any)
   - Condition rows (dynamic, add/remove)
   - Each row: [indicator ▼] [params] [operator ▼] [right side]
   - [+ Add Condition] button
   - [+ Add Condition Group] for nesting (creates indented sub-group)

4. Exit Conditions
   - Same structure as entry conditions
   - Logic toggle (AND / OR)

5. Risk Management
   - Stop Loss: type select + value input
   - Take Profit: type select + value input
   - Trailing Stop: enable toggle + type + value
   - Max Hold: number input (bars, optional)

6. Position Sizing
   - Method (select: fixed qty, fixed $, % equity, risk-based)
   - Value input
   - Max Positions (number input)
   - Order Type (select: market, limit)

7. Schedule
   - Trading Hours (radio: Regular / Extended / Custom)
   - Re-entry Cooldown (number input, bars)

8. Validation Summary
   - Live validation results (errors in red, warnings in yellow)
   - Updates on every change (debounced 500ms)

9. Actions
   - [Save Draft] [Validate] [Enable]
   - If editing enabled strategy: [Save & Apply] (shows diff)
```

**Condition Row Component:**

```
┌─────────────────────────────────────────────────────┐
│ [Indicator ▼] [param1] [param2]  [output ▼]         │
│ [Operator ▼]                                        │
│ (● Value) [input] | (○ Indicator) [Indicator ▼]     │
│                                            [🗑️ Remove]│
└─────────────────────────────────────────────────────┘
```

When indicator is selected:
- Parameters render dynamically from catalog definition
- Sliders for bounded int/float params (with min/max from catalog)
- Dropdowns for select-type params (source: close/open/high/low/hl2/hlc3/ohlc4)
- Output dropdown appears for multi-output indicators (MACD, Bollinger)
- "Custom Formula" option replaces dropdown with text input

**Data Requirements:**

```
GET  /api/v1/strategies/indicators      → indicator catalog (on load)
GET  /api/v1/market-data/watchlist      → symbols for selection
GET  /api/v1/strategies/:id             → existing config (if editing)
POST /api/v1/strategies/validate        → real-time validation (debounced)
POST /api/v1/strategies                 → create new strategy
PUT  /api/v1/strategies/:id             → update strategy
POST /api/v1/strategies/:id/enable      → enable strategy
```

**Edit Mode for Enabled Strategies:**

Shows a diff before saving:

```
Changes (v1.2.0 → v1.3.0):
  Entry: RSI period 14 → 21
  Exit: Stop loss 2.0% → 1.5%
  ⚠ Stop loss change applies to existing positions

  [Cancel] [Save & Apply]
```

---

### View 4 — Strategy Detail (/strategies/:id)

**Purpose:** Deep dive into one strategy.

**Header:**

```
← Back to Strategies | Strategy Name | Version | Status Badge
[Pause/Resume] [Edit] [Disable] [Close All Positions]
```

**Tabs:**

```
[Performance] [Open Positions] [Signals] [Config] [Evaluation Log]
```

**Performance Tab:**

```
Stat cards: Total PnL (incl dividends), Win Rate, Total Trades, Profit Factor
Strategy equity curve chart (period selector)
Metrics grid: avg winner, avg loser, risk/reward, max drawdown,
              Sharpe, avg hold time, dividend income
Closed trades table (sortable, filterable, paginated)
```

**Open Positions Tab:**

```
Position cards with:
  Symbol, side, qty, entry price, current price
  Price PnL, dividends, total return (all color-coded)
  Stop loss / take profit levels (editable inline)
  Trailing stop status
  Bars held
  [Close ▼] dropdown (Close All, Close Partial)
  [Edit SL/TP] inline edit
```

**Signals Tab:**

```
Signal history filtered to this strategy
Same layout as the global Signals view but pre-filtered
```

**Config Tab:**

```
Current config displayed in readable form (not raw JSON)
Version history list with timestamps
Click a version to see the diff against current
```

**Evaluation Log Tab:**

```
Table: timestamp, symbols evaluated, signals emitted,
       exits triggered, duration, status
Filterable by status (success, skipped, error)
Click row to expand: per-symbol evaluation detail
```

**Data Requirements:**

```
GET /api/v1/strategies/:id                    → strategy detail
GET /api/v1/portfolio/metrics/:strategyId     → performance metrics
GET /api/v1/portfolio/equity-curve?strategyId= → strategy equity curve
GET /api/v1/portfolio/positions?strategyId=    → open positions
GET /api/v1/portfolio/pnl/realized?strategyId= → closed trades
GET /api/v1/signals?strategyId=               → signal history
GET /api/v1/strategies/:id/versions           → version history
GET /api/v1/strategies/:id/evaluations        → evaluation log
```

---

### View 5 — Signals (/signals)

**Purpose:** All signals across all strategies.

**Layout:**

```
Filters: strategy, status, symbol, signal type, source, date range
Signal table (sortable, paginated):
  Time, Symbol, Side, Type, Strategy, Status, Confidence
  Expandable rows → full payload (indicator values at signal time)
Stats summary bar: total, approved, rejected, modified, expired, approval rate
```

**Data Requirements:**

```
GET /api/v1/signals             → paginated signal list
GET /api/v1/signals/stats       → summary statistics
```

---

### View 6 — Paper Trading (/orders)

**Purpose:** Order and fill activity, forex pool status.

**Tabs:** [Orders] [Fills] [Forex Pool] [Shadow Tracking]

**Orders Tab:**

```
Order table: time, symbol, side, qty, price, status, slippage, strategy
Filterable by strategy, symbol, status, market, date range
```

**Fills Tab:**

```
Fill table: time, symbol, side, qty, ref price, fill price, fee, slippage
```

**Forex Pool Tab:**

```
Account cards showing:
  Account number, allocations (symbol + side + strategy), available status
Pair capacity summary (EUR_USD: 2/4, GBP_USD: 1/4)
```

**Shadow Tracking Tab:**

```
Shadow positions (open + closed) with PnL
Comparison table: strategy, real PnL, shadow PnL, blocked signals, missed PnL
```

**Data Requirements:**

```
GET /api/v1/paper-trading/orders            → orders
GET /api/v1/paper-trading/fills             → fills
GET /api/v1/paper-trading/forex-pool/status → pool state
GET /api/v1/paper-trading/shadow/comparison → shadow vs real
GET /api/v1/paper-trading/stats             → trading statistics
```

---

### View 7 — Portfolio (/portfolio)

**Purpose:** Positions, PnL, equity, dividends.

**Tabs:** [Positions] [PnL Analysis] [Equity] [Dividends]

**Positions Tab:**

```
Open positions table with inline actions (close, edit SL/TP)
Closed positions table (collapsible, filterable by date)
Each position shows: price PnL, dividends, total return
```

**PnL Analysis Tab:**

```
PnL summary: today, week, month, total (by strategy, by symbol)
PnL calendar heatmap (daily PnL colored green/red)
Win/loss distribution chart
```

**Equity Tab:**

```
Equity curve chart (period selector: 1d, 7d, 30d, 90d, YTD, all)
Drawdown chart (below equity curve, same time axis)
Equity breakdown: cash vs positions value vs total
```

**Dividends Tab:**

```
Recent dividend payments table
Upcoming dividends for current holdings
Dividend income summary: today, month, year, all time
Dividend income by strategy
```

**Data Requirements:**

```
GET /api/v1/portfolio/positions              → all positions
GET /api/v1/portfolio/pnl/summary            → PnL breakdown
GET /api/v1/portfolio/pnl/realized           → realized PnL entries
GET /api/v1/portfolio/equity-curve           → chart data
GET /api/v1/portfolio/summary                → equity breakdown
GET /api/v1/portfolio/dividends              → payment history
GET /api/v1/portfolio/dividends/upcoming     → upcoming
GET /api/v1/portfolio/dividends/summary      → income summary
GET /api/v1/portfolio/metrics                → performance metrics
```

---

### View 8 — Risk Dashboard (/risk)

**Purpose:** Risk state, exposure, kill switch, decisions.

**Layout:**

```
Kill switch control: prominent button + current state
Stat cards: drawdown, daily loss, total exposure, decisions today
  Each with progress bars showing current vs limit
Exposure breakdown: per-symbol and per-strategy bar charts
Recent risk decisions table (approved ✅, rejected ❌, modified ⚙️)
Risk config summary (read-only, link to settings for edit)
```

**Data Requirements:**

```
GET /api/v1/risk/overview            → current risk state
GET /api/v1/risk/exposure            → exposure breakdown
GET /api/v1/risk/decisions           → recent decisions
GET /api/v1/risk/kill-switch/status  → kill switch state
GET /api/v1/risk/drawdown            → drawdown detail
GET /api/v1/risk/config              → current limits
```

**Kill Switch Interaction:**

```
[Activate Emergency Stop] → confirmation dialog:
  "This will block ALL new trades across ALL strategies.
   Open positions will NOT be closed automatically.
   Are you sure?"
  [Cancel] [Activate Kill Switch]

When active:
  Banner: 🔴 "KILL SWITCH ACTIVE — No new trades will be placed"
  [Deactivate Kill Switch] button (also requires confirmation)
```

---

### View 9 — System Telemetry (/system, admin only)

**Purpose:** Developer/operator infrastructure view.

**Tabs:** [Health] [Pipeline] [Activity] [Jobs] [Database]

**Health Tab:**

```
System status indicator (healthy/degraded/unhealthy)
Uptime counter
Per-module pipeline status (colored dots + description)
Active alerts summary
```

**Pipeline Tab:**

```
Throughput metrics (bars, evaluations, signals, fills) with sparkline charts
Latency metrics (bar→DB, eval, signal→risk, risk→fill, fill→position)
Error rates
```

**Activity Tab:**

```
Full activity feed with filters:
  Category: All, Market Data, Strategy, Signal, Risk, Trading, Portfolio
  Severity: All, Info+, Warning+, Error+
  Strategy filter
  Symbol filter
Live-updating (10s poll or WebSocket)
```

**Jobs Tab:**

```
Background job status table:
  Job name, last run, next run, status (success/running/failed), duration
```

**Database Tab:**

```
Table sizes (rows, disk size)
Recent query performance (avg, slow query count)
```

**Data Requirements:**

```
GET /api/v1/observability/health              → system health
GET /api/v1/observability/health/pipeline     → module statuses
GET /api/v1/observability/health/latency      → latency metrics
GET /api/v1/observability/events/recent       → activity feed
GET /api/v1/observability/metrics/:name       → specific metric series
GET /api/v1/observability/alerts/active       → active alerts
GET /api/v1/observability/jobs                → job statuses
GET /api/v1/observability/database/stats      → DB statistics
```

---

### View 10 — Settings (/settings, admin only)

**Tabs:** [Risk Config] [Accounts] [Users] [Alerts] [System]

**Risk Config Tab:**

```
Editable form with all risk parameters:
  Max position size %, max symbol exposure %, max strategy exposure %
  Max total exposure %, max drawdown %, catastrophic drawdown %
  Max daily loss %, max daily loss $ amount, min position value
Save button with confirmation
Change history (audit log)
```

**Accounts Tab:**

```
Broker connection status (Alpaca, OANDA)
Forex account pool management:
  List accounts, add/remove virtual accounts
  Capital allocation per account
```

**Users Tab:**

```
User list table: email, username, role, status, last login
[Create User] button → modal with email, username, password, role
Per-user actions: suspend, activate, reset password, change role
```

**Alerts Tab:**

```
Alert rule list: name, condition, severity, enabled toggle
Edit alert thresholds inline
Alert history (triggered, acknowledged, resolved)
```

**System Tab:**

```
Universe filter configuration (min volume, min price, exchanges)
Schedule overrides
System information (version, environment)
```

---

## 6. Shared Component Library

### Layout Components

```
PageContainer      — standard page wrapper with padding and max-width
PageHeader         — title, description, action buttons
SectionHeader      — section divider with title
CardGrid           — responsive grid of stat cards
TabContainer       — tab navigation with content panels
SidebarLayout      — sidebar + main content layout
```

### Data Display Components

```
StatCard           — value, label, subtitle, trend (up/down), optional progress bar
                     value uses monospace font and color-coding for PnL
DataTable          — sortable columns, filterable, paginated
                     column types: text, number, price, pnl, timestamp, status, actions
                     expandable rows for detail
StatusPill         — colored badge: enabled(green), disabled(gray),
                     paused(yellow), error(red), draft(blue)
ProgressBar        — horizontal bar with filled portion and threshold marker
                     used for drawdown/exposure (shows current vs limit)
PnlValue           — formatted number, monospace, green/red, always show sign
PriceValue         — formatted price, monospace, appropriate decimals per market
PercentValue       — formatted %, optional color coding
TimeAgo            — relative timestamp ("12s ago"), auto-updates
SymbolBadge        — symbol name with market indicator icon
EmptyState         — illustration + message + action button
                     "No strategies yet. Create your first strategy."
LoadingState       — skeleton loader matching expected content shape
                     NOT a spinner. Skeletons give spatial context.
ErrorState         — error icon + message + [Retry] button
```

### Form Components

```
TextInput          — standard text input with label and validation
NumberInput        — numeric input with min/max, optional slider
SelectInput        — dropdown with search (for indicator selection)
MultiSelect        — multi-choice with chips (for symbol selection)
RadioGroup         — horizontal or vertical radio options
Toggle             — on/off switch (for enable/disable)
SymbolSearch       — symbol search with autocomplete from watchlist
ConditionRow       — the condition builder row (indicator + operator + value)
ConditionGroup     — nested condition group with AND/OR toggle
FormulaInput       — text input with syntax highlighting for expressions
SliderInput        — range slider with numeric display
```

### Interactive Components

```
ConfirmDialog      — modal requiring confirmation for destructive actions
                     "Are you sure?" with context and [Cancel] [Confirm]
AlertBanner        — top-of-page alert with severity color and dismiss
ActivityFeedItem   — emoji + timestamp + summary, clickable
ChartContainer     — Recharts wrapper with standard dark theme styling,
                     period selector, loading/empty states
Tooltip            — hover info for truncated text or contextual help
DropdownMenu       — action menu (Close Position → Close All, Close Partial)
```

### Chart Styling (Recharts)

```
Background:   transparent (uses card surface color)
Grid lines:   #2a2d3a (same as border color)
Axis text:    #a1a1aa (secondary text), 12px
Line color:   #3b82f6 (accent blue) for primary series
Area fill:    #3b82f6 with 10% opacity
Green line:   #22c55e for positive/equity
Red line:     #ef4444 for negative/drawdown
Tooltip:      dark surface with border, same as card styling
```

---

## 7. State Management

### TanStack Query (Server State)

All data from the API is fetched and cached with TanStack Query.

```typescript
// Example: fetch strategies
const { data, isLoading, error } = useQuery({
  queryKey: ['strategies'],
  queryFn: () => api.get('/strategies'),
  staleTime: 30_000,      // 30 seconds before considered stale
  refetchInterval: 60_000, // refetch every 60 seconds
});
```

Standard staleTime and refetchInterval per data type:

```
Portfolio summary:     staleTime 30s,  refetch 60s
Equity curve:          staleTime 60s,  refetch 300s
Strategy list:         staleTime 30s,  refetch 60s
Positions:             staleTime 15s,  refetch 30s
Signals:               staleTime 10s,  refetch 10s
Activity feed:         staleTime 5s,   refetch 10s
Risk overview:         staleTime 15s,  refetch 30s
System health:         staleTime 10s,  refetch 10s
Indicator catalog:     staleTime 3600s (rarely changes)
```

Background refetching is enabled. Stale data is shown while fresh data loads.

### Zustand (UI State)

UI-only state that doesn't come from the server:

```typescript
interface UIStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  
  // Per-view filter state
  signalFilters: SignalFilterState;
  orderFilters: OrderFilterState;
  
  // Chart preferences
  equityCurvePeriod: '1d' | '7d' | '30d' | '90d' | 'all';
  
  // Activity feed
  activityFeedPaused: boolean;
}
```

Never put server data in Zustand. Never use TanStack Query for UI state.

---

## 8. Frontend Folder Structure

```
frontend/src/
    app/
        App.tsx                  ← root component, providers, router
        router.tsx               ← route definitions
        providers.tsx            ← QueryClient, Zustand, theme providers
    layouts/
        AppShell.tsx             ← sidebar + content + status bar + alert banner
        AuthLayout.tsx           ← login page layout (no sidebar)
    pages/
        Dashboard.tsx
        StrategyList.tsx
        StrategyBuilder.tsx
        StrategyDetail.tsx
        Signals.tsx
        Orders.tsx
        Portfolio.tsx
        Risk.tsx
        System.tsx               (admin)
        Settings.tsx             (admin)
        Login.tsx
        NotFound.tsx
        Forbidden.tsx
    features/
        auth/
            useAuth.ts           ← login, logout, token management
            AuthGuard.tsx        ← route protection component
            AdminGuard.tsx       ← admin route protection
        dashboard/
            StatCards.tsx
            EquityCurveChart.tsx
            StrategyStatusList.tsx
            ActivityFeed.tsx
        strategies/
            StrategyCard.tsx
            ConditionBuilder.tsx  ← the condition row/group components
            IndicatorSelect.tsx
            OperatorSelect.tsx
            SymbolSelector.tsx
            FormulaInput.tsx
            RiskManagementForm.tsx
            PositionSizingForm.tsx
            StrategyDiff.tsx     ← config version diff display
            ValidationSummary.tsx
        signals/
            SignalTable.tsx
            SignalDetail.tsx
            SignalStats.tsx
        orders/
            OrderTable.tsx
            FillTable.tsx
            ForexPoolStatus.tsx
            ShadowComparison.tsx
        portfolio/
            PositionCard.tsx
            PositionTable.tsx
            PnlSummary.tsx
            PnlCalendar.tsx
            EquityCurve.tsx
            DrawdownChart.tsx
            DividendTable.tsx
            ClosePositionDialog.tsx
            EditStopLossDialog.tsx
        risk/
            RiskStatCards.tsx
            ExposureBreakdown.tsx
            RiskDecisionTable.tsx
            KillSwitchControl.tsx
            RiskConfigForm.tsx
        system/
            PipelineStatus.tsx
            ThroughputMetrics.tsx
            LatencyMetrics.tsx
            BackgroundJobs.tsx
            DatabaseStats.tsx
        settings/
            UserManagement.tsx
            AlertRuleEditor.tsx
            BrokerAccountManager.tsx
    components/
        ui/                      ← shadcn/ui base components
        StatCard.tsx
        DataTable.tsx
        StatusPill.tsx
        ProgressBar.tsx
        PnlValue.tsx
        PriceValue.tsx
        PercentValue.tsx
        TimeAgo.tsx
        SymbolBadge.tsx
        EmptyState.tsx
        LoadingState.tsx
        ErrorState.tsx
        ConfirmDialog.tsx
        AlertBanner.tsx
        ActivityFeedItem.tsx
        ChartContainer.tsx
    lib/
        api.ts                   ← API client with auth headers, base URL
        formatters.ts            ← price, PnL, percent, number formatting
        constants.ts             ← color values, refresh intervals
        types.ts                 ← shared TypeScript types
        utils.ts                 ← general utilities
    types/
        strategy.ts
        signal.ts
        order.ts
        position.ts
        portfolio.ts
        risk.ts
        market-data.ts
        auth.ts
        observability.ts
```

---

## 9. API Client

### Configuration

```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Auth interceptor: attach access token
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: handle 401 (refresh token), unwrap envelope
api.interceptors.response.use(
  (response) => response.data.data,  // unwrap { data: ... } envelope
  async (error) => {
    if (error.response?.status === 401) {
      // attempt token refresh
      // if refresh fails, redirect to login
    }
    // unwrap error envelope
    throw error.response?.data?.error || error;
  }
);
```

### Type Safety

Every API response has a corresponding TypeScript type:

```typescript
interface Strategy {
  id: string;
  key: string;
  name: string;
  status: 'draft' | 'enabled' | 'paused' | 'disabled';
  currentVersion: string;
  market: 'equities' | 'forex' | 'both';
  createdAt: string;
  updatedAt: string;
}

interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  };
}
```

---

## 10. Responsive Behavior

```
Large desktop (>1440px):
  Sidebar expanded by default
  Full multi-column layouts
  All features available

Medium desktop (1024-1440px):
  Sidebar collapsed to icons by default
  Slightly narrower content area
  All features available

Tablet (768-1024px):
  Sidebar hidden, hamburger menu
  Single column layouts where needed
  Strategy builder may be cramped but functional

Mobile (<768px):
  Not a priority for MVP
  Basic navigation should work
  Strategy builder is desktop-only (show message on mobile)
```

The strategy builder shows a message on small screens:

```
"Strategy Builder is designed for desktop use.
 Please use a larger screen to create or edit strategies."
```

---

## 11. Loading, Empty, and Error States

Every view must handle three non-happy-path states:

### Loading

Skeleton loaders matching expected content shape. Not spinners.

```
StatCard loading:    gray pulsing rectangle where value would be
DataTable loading:   gray pulsing rows matching column widths
Chart loading:       gray pulsing rectangle matching chart dimensions
Activity feed:       gray pulsing rows with emoji-width circle + text lines
```

### Empty

Descriptive message with action suggestion:

```
Strategy list empty:    "No strategies yet. Create your first strategy."
                        [+ New Strategy] button
Signals empty:          "No signals generated yet. Enable a strategy to start."
Positions empty:        "No open positions. Signals will create positions
                         when approved by risk."
Activity feed empty:    "No recent activity. System events will appear here."
```

### Error

Error message with retry:

```
"Failed to load positions." [Retry]
"Connection error. Check your network." [Retry]
```

Never show a blank screen. Never show an unhandled exception.
Never show a raw error message from the API.

---

## 12. Data Refresh Strategy

```
View                    Refresh Method     Interval
─────────────────────────────────────────────────────
Dashboard summary       polling            60s
Dashboard equity curve  polling            300s
Dashboard activity feed polling            10s
Strategy list           polling            60s
Strategy detail metrics polling            60s
Strategy positions      polling            30s
Signals                 polling            10s
Orders/Fills            polling            30s
Portfolio positions     polling            30s
Portfolio equity curve  polling            300s
Risk overview           polling            30s
System telemetry        polling            10s
System activity feed    polling            10s
```

All polling uses TanStack Query refetchInterval.
WebSocket push for activity feed and signals is a future enhancement.

---

## Acceptance Criteria

This spec is accepted when:

- App shell layout (sidebar, alert banner, status bar) is defined
- Navigation structure with routes is explicit
- Theme colors, fonts, and formatting conventions are specified
- All 10 views are described with layout, data requirements, and interactions
- Strategy builder form structure and dynamic behavior is detailed
- Condition builder component behavior is specified
- Shared component library is enumerated with descriptions
- State management rules (TanStack Query vs Zustand) are clear
- Frontend folder structure is defined
- API client configuration (auth, envelope unwrapping) is specified
- Loading, empty, and error states are required for every view
- Responsive behavior expectations are set
- Data refresh intervals per view are documented
- Chart styling conventions are defined
- Financial number formatting rules are specified
- A builder agent can scaffold and implement the frontend without asking
  design or layout questions
