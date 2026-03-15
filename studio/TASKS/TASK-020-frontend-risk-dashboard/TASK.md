# TASK-020 — Frontend: Risk Dashboard, System Telemetry, and Settings

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Replace the Risk, System, and Settings placeholder pages with complete
views: risk dashboard with kill switch and exposure, system telemetry
with pipeline status and activity feed, and admin settings for risk
config, accounts, users, and alerts.

## Read First

1. /studio/SPECS/frontend_specs.md — section 5, Views 8-10
2. Review TASK-015 BUILDER_OUTPUT.md — existing components and types

## Constraints

- Use existing shared components from TASK-015
- System and Settings pages are admin-only (already guarded by AdminGuard)
- Do NOT modify backend code
- Do NOT touch /studio (except BUILDER_OUTPUT.md)

---

## Deliverables

### 1. Risk Dashboard Page (frontend/src/pages/Risk.tsx)

```
Kill switch control: prominent red/green button with current state
  Activate → confirmation dialog with warning text
  Deactivate → confirmation dialog

Stat cards row:
  Drawdown (% with progress bar vs limit)
  Daily Loss ($ with progress bar vs limit)
  Total Exposure (% with progress bar vs limit)
  Decisions Today (count, approved/rejected breakdown)

Exposure breakdown section:
  Per-symbol bar chart (horizontal bars showing exposure %)
  Per-strategy bar chart

Recent risk decisions table:
  Time, signal, symbol, strategy, status (✅/❌/⚙️), reason, checks passed
  Filterable by status
  Expandable rows: full decision detail with portfolio snapshot

Risk config summary (read-only card):
  Key limits displayed, [Edit in Settings →] link
```

### 2. Risk Feature Components (frontend/src/features/risk/)

**RiskStatCards.tsx** — 4 stat cards with progress bars
**ExposureBreakdown.tsx** — Per-symbol and per-strategy bar charts (Recharts)
**RiskDecisionTable.tsx** — DataTable with status icons and expandable detail
**KillSwitchControl.tsx** — Toggle button with confirmation dialogs
**RiskConfigForm.tsx** — Read-only config display (used here), editable form (in Settings)

### 3. System Telemetry Page (frontend/src/pages/System.tsx)

**Tabs:** [Health] [Pipeline] [Activity] [Jobs] [Database]

**Health Tab:**
```
System status indicator: large colored dot + "Healthy" / "Degraded" / "Unhealthy"
Uptime counter
Per-module status list: module name, colored dot, description
Active alerts summary (count by severity, link to alerts)
```

**Pipeline Tab:**
```
Throughput metrics cards: bars/min, evaluations/min, signals/min, fills/min
  Each with sparkline mini-chart (last 30 minutes)
Latency metrics cards: bar→DB, evaluation, signal→risk, risk→fill, fill→position
Error rate card
```

**Activity Tab:**
```
Full activity feed with filters:
  Category: All, Market Data, Strategy, Signal, Risk, Trading, Portfolio
  Severity: All, Info+, Warning+, Error+
  Strategy filter dropdown
  Symbol filter input
Live-updating (10s poll)
```

**Jobs Tab:**
```
Background job status table:
  Job name, last run, next run, status (success/running/failed), duration
```

**Database Tab:**
```
Table sizes: table name, row count, estimated size
```

### 4. System Feature Components (frontend/src/features/system/)

**PipelineStatus.tsx** — Per-module status indicators
**ThroughputMetrics.tsx** — Metric cards with sparkline charts
**LatencyMetrics.tsx** — Latency display cards
**BackgroundJobs.tsx** — Job status table
**DatabaseStats.tsx** — Table size display

### 5. Settings Page (frontend/src/pages/Settings.tsx)

**Tabs:** [Risk Config] [Accounts] [Users] [Alerts] [System]

Tab routing: /settings → Risk Config, /settings/risk, /settings/accounts,
/settings/users, /settings/alerts

**Risk Config Tab:**
```
Editable form with all risk parameters:
  Max position size %, max symbol exposure %, max strategy exposure %
  Max total exposure %, max drawdown %, catastrophic drawdown %
  Max daily loss %, min position value
  Each with NumberInput and current value
Save button → confirmation dialog: "Update risk configuration?"
Change history table (audit log): field, old value, new value, changed by, timestamp
```

**Accounts Tab:**
```
Broker connection status cards: Alpaca (connected/disconnected), OANDA
Forex pool account list: label, capital allocation, active status
  Capital displayed as PriceValue
```

**Users Tab:**
```
User list table: email, username, role (StatusPill), status, last login (TimeAgo)
[Create User] button → modal: email, username, password, role select
Per-user actions: suspend/activate toggle, reset password, change role
```

**Alerts Tab:**
```
Alert rule list: name, category, condition type, severity, enabled toggle
  Toggle enables/disables rule inline (PUT /observability/alert-rules/:id)
Alert history table: time, severity, summary, status, acknowledged by
  Acknowledge button for active alerts
```

**System Config Tab:**
```
System information: environment, version
Read-only display of key configuration values
```

### 6. Settings Feature Components (frontend/src/features/settings/)

**UserManagement.tsx** — User table + create modal + action buttons
**AlertRuleEditor.tsx** — Rule list with inline enable toggle + history
**BrokerAccountManager.tsx** — Broker status + forex pool accounts

### 7. Data Requirements

```
# Risk
GET /risk/overview                    → dashboard data (stale: 15s, refetch: 30s)
GET /risk/exposure                    → exposure breakdown
GET /risk/decisions                   → recent decisions
GET /risk/kill-switch/status          → kill switch state
GET /risk/drawdown                    → drawdown detail
GET /risk/config                      → current limits
POST /risk/kill-switch/activate       → activate kill switch
POST /risk/kill-switch/deactivate     → deactivate

# System
GET /observability/health             → system health (stale: 10s, refetch: 10s)
GET /observability/health/pipeline    → module statuses
GET /observability/events/recent      → activity feed (stale: 5s, refetch: 10s)
GET /observability/events             → filtered events
GET /observability/metrics/:name      → metric time series
GET /observability/alerts/active      → active alerts
GET /observability/jobs               → job statuses
GET /observability/database/stats     → DB statistics

# Settings
GET /risk/config                      → risk config for editing
PUT /risk/config                      → update risk config
GET /auth/users                       → user list (admin)
POST /auth/users                      → create user
PUT /auth/users/:id                   → update user
GET /observability/alert-rules        → alert rules
PUT /observability/alert-rules/:id    → update rule
POST /observability/alerts/:id/ack    → acknowledge alert
GET /observability/alerts             → alert history
```

---

## Acceptance Criteria

### Risk Dashboard
1. Kill switch button renders with current state (active/inactive)
2. Kill switch activate triggers confirmation dialog with warning text
3. Kill switch deactivate triggers confirmation dialog
4. Drawdown stat card shows progress bar (current vs limit)
5. Daily loss stat card shows progress bar
6. Total exposure stat card shows progress bar
7. Decisions today card shows approved/rejected counts
8. Per-symbol exposure bar chart renders
9. Per-strategy exposure bar chart renders
10. Risk decisions table renders with status icons (✅/❌/⚙️)
11. Decision rows expandable to show full detail
12. Risk config summary shows key limits as read-only

### System Telemetry
13. Health tab shows system status indicator with colored dot
14. Health tab shows per-module status list
15. Pipeline tab shows throughput metric cards
16. Pipeline tab shows latency metric cards
17. Activity tab shows full event feed with filters
18. Activity tab category and severity filters work
19. Jobs tab shows background job status table
20. Database tab shows table sizes

### Settings
21. Risk Config tab renders editable form with all parameters
22. Risk Config save triggers confirmation dialog
23. Risk Config change history table renders
24. Users tab shows user list with role badges
25. Users tab [Create User] opens modal
26. Users tab per-user actions (suspend, activate) work
27. Alerts tab shows rule list with enable/disable toggles
28. Alerts tab toggle updates rule via PUT API
29. Alerts tab history shows alert instances
30. Accounts tab shows broker connection status

### General
31. Tab navigation works on System and Settings pages
32. Settings sub-routes (/settings/risk, etc.) map to correct tabs
33. All data fetches use TanStack Query with correct intervals
34. Loading, empty, and error states handled for all sections
35. Nothing in /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

BUILDER_OUTPUT.md at /studio/TASKS/TASK-020-risk-system-settings/BUILDER_OUTPUT.md
