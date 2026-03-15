# TASK-038 — Live Site Bug Fixes (Health, Status Bar, Missing Endpoints, Dashboard)

## Goal

Fix all remaining UI and API issues visible on the live production site. After this task, the System Telemetry page shows accurate module health, the status bar shows correct broker connectivity, the Jobs and Database tabs render data, the Settings system tab loads, and the dashboard shows initial portfolio equity.

## Depends On

TASK-037 (deployed to VPS)

## Scope

**In scope:**
- Fix health reporting for market_data and strategies modules (currently "Unknown")
- Add missing `/api/v1/observability/jobs` endpoint
- Add missing `/api/v1/observability/database/stats` endpoint
- Fix Settings system tab 404
- Fix status bar broker connectivity display (shows "Disconnected" when backend reports connected)
- Fix alert logic for WebSocket — no alert when brokers have 0 symbols (expected after hours)
- Dashboard shows initial cash/equity from PAPER_TRADING_INITIAL_CASH config
- Add backfill job status to Jobs tab or a dedicated view

**Out of scope:**
- OANDA sub-account creation (operational, not code)
- Dev workflow (separate task)
- New features beyond what the existing UI expects

---

## Bug Fixes

### BF-1 — market_data and strategies show "Unknown" in System Health

**Problem:** The System Health page shows market_data and strategies as "Unknown" with red dots. Other modules (signals, risk, paper_trading, portfolio) show "Running."

**Root cause:** The health endpoint (`/api/v1/health` or `/api/v1/observability/health`) doesn't include status for market_data and strategies modules. These modules either don't register their status with the health system, or the health aggregator doesn't query them.

**Investigation:**
1. Check how signals/risk/paper_trading/portfolio report their status (they work)
2. Find where market_data and strategies should register (likely in their startup functions)
3. Add the same status reporting pattern

**Fix:** Add health status registration for market_data and strategies modules. At minimum, they should report "running" after successful startup and "error" if startup failed.

### BF-2 — Missing `/api/v1/observability/jobs` endpoint (404)

**Problem:** Jobs tab shows "Failed to load background jobs" because the endpoint doesn't exist.

**Expected by frontend:** `GET /api/v1/observability/jobs` returning a list of background job statuses:
```json
{
  "data": [
    {
      "name": "strategy_runner",
      "status": "running",
      "lastRun": "2025-03-15T10:00:00Z",
      "interval": "60s",
      "errors": 0
    },
    {
      "name": "oanda_backfill",
      "status": "completed",
      "lastRun": "2025-03-15T09:00:00Z",
      "progress": "40/40 jobs"
    }
  ]
}
```

**Fix:** Create the endpoint in the observability router. It should aggregate status from:
- Strategy runner (running/stopped, last evaluation time)
- Safety monitor (running/stopped)
- Signal expiry checker (running/stopped)
- Mark-to-market cycle (running/stopped)
- Snapshot cycle (running/stopped)
- Event batch writer (running/stopped)
- Metric collector (running/stopped)
- Alert evaluation loop (running/stopped)
- WebSocket connections (per broker: connected/disconnected, uptime)
- Backfill jobs (from backfill_jobs table: pending/running/completed/failed counts)

If individual background tasks don't expose their status, return what's available and document what's missing.

### BF-3 — Missing `/api/v1/observability/database/stats` endpoint (404)

**Problem:** Database tab shows "Failed to load database stats" because the endpoint doesn't exist.

**Expected by frontend:** `GET /api/v1/observability/database/stats` returning database statistics:
```json
{
  "data": {
    "connectionPool": {
      "size": 20,
      "checkedOut": 3,
      "overflow": 0
    },
    "tables": [
      {
        "name": "ohlcv_bars",
        "rowCount": 357640,
        "sizeBytes": 158000000
      },
      {
        "name": "audit_events",
        "rowCount": 1200,
        "sizeBytes": 5000000
      }
    ],
    "totalSizeBytes": 200000000,
    "migrationsApplied": 10,
    "migrationsCurrent": true
  }
}
```

**Fix:** Create the endpoint in the observability router. Query:
- `SELECT relname, n_live_tup FROM pg_stat_user_tables` for row counts
- `SELECT pg_total_relation_size(relid) FROM pg_stat_user_tables` for table sizes
- `SELECT pg_database_size(current_database())` for total DB size
- SQLAlchemy pool status: `engine.pool.status()` for connection pool info
- Alembic current version for migration status

### BF-4 — Settings system tab returns 404

**Problem:** Clicking the system-related tab in Settings navigates to a route that doesn't exist.

**Investigation:**
1. Check what URL the Settings page navigates to for the system tab
2. Check if the route exists in the router config
3. Check if the component exists but the route isn't wired

**Fix:** Either wire the missing route or redirect to the System page if it's a duplicate.

### BF-5 — Status bar shows "Disconnected" when backend reports connected

**Problem:** Bottom status bar shows "🔴 Alpaca Disconnected" and "🔴 OANDA Disconnected" even when OANDA is streaming and the health endpoint reports connected.

**Root cause:** The status bar likely reads broker status from a different endpoint or field than the System Health page. Possible issues:
- Reading from `/api/v1/health` which returns `"not_started"` for Alpaca (correct — no symbols to subscribe)
- But also shows OANDA as disconnected when it's actually connected
- The field name mismatch (BF-1 from TASK-032: `subscribedSymbols` key was fixed but may not be deployed)

**Investigation:**
1. Check what API call the status bar component makes
2. Check what field it reads for broker status
3. Compare against what the health endpoint actually returns

**Fix:** Make the status bar read from the correct field. For Alpaca with 0 symbols, show "No symbols" or "Waiting for market hours" instead of "Disconnected."

### BF-6 — Alert "WebSocket disconnected during market hours" is a false positive

**Problem:** The red alert banner says "WebSocket disconnected during market hours" but it's 4 AM ET — not market hours. The alert fires because Alpaca has 0 symbols subscribed (volume filter returned nothing after hours).

**Root cause:** The alert rule checks if WebSocket is disconnected but doesn't account for:
- 0 symbols = WebSocket intentionally not started
- After-hours = no equities data expected

**Fix:** The alert should only fire when:
- Market IS open (check market hours: 9:30 AM - 4:00 PM ET)
- AND the broker has symbols to subscribe to (watchlist > 0)
- AND the WebSocket is disconnected

If market is closed OR symbols = 0, suppress the alert.

### BF-7 — Dashboard doesn't show initial equity/cash

**Problem:** Dashboard stat cards show "—" for Total Equity. Even with no trades, the portfolio should show the initial cash balance from `PAPER_TRADING_INITIAL_CASH` (default $100,000).

**Root cause:** The portfolio summary endpoint (`/api/v1/portfolio/summary`) likely returns null for equity when no portfolio snapshots exist. But it should return the initial cash as equity.

**Investigation:**
1. Check what `/api/v1/portfolio/summary` returns with no trades
2. The portfolio service should initialize cash on first access or at startup

**Fix:** When no portfolio data exists, the summary endpoint should return:
```json
{
  "data": {
    "totalEquity": 100000.00,
    "cash": 100000.00,
    "openPositions": 0,
    "unrealizedPnl": 0,
    "realizedPnlTotal": 0,
    "drawdownPercent": 0,
    "todayPnl": 0
  }
}
```

Either seed the initial cash balance during startup (via portfolio module initialization), or have the endpoint fall back to `PAPER_TRADING_INITIAL_CASH` when no portfolio records exist.

### BF-8 — Backfill status visibility

**Problem:** When the system starts, backfill runs for several minutes but there's no way to see its progress from the UI.

**Fix:** Include backfill job status in the `/api/v1/observability/jobs` endpoint (BF-2). The backfill_jobs table already tracks per-symbol/timeframe status. Query it and return:

```json
{
  "name": "historical_backfill",
  "status": "running",
  "progress": {
    "completed": 32,
    "failed": 0,
    "pending": 8,
    "total": 40
  },
  "lastCompleted": "EUR_USD 1h — 6,193 bars"
}
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | market_data module reports Running/Connected status in System Health (not Unknown) |
| AC2 | strategies module reports Running status in System Health (not Unknown) |
| AC3 | `/api/v1/observability/jobs` returns 200 with background job statuses |
| AC4 | Jobs tab renders job list (not "Failed to load") |
| AC5 | `/api/v1/observability/database/stats` returns 200 with table stats and pool info |
| AC6 | Database tab renders stats (not "Failed to load") |
| AC7 | Settings system tab loads without 404 |
| AC8 | Status bar shows "Connected" when OANDA is streaming |
| AC9 | Status bar shows "No symbols" or "Waiting" for Alpaca after hours (not "Disconnected") |
| AC10 | WebSocket alert does not fire outside market hours or when 0 symbols configured |
| AC11 | Dashboard Total Equity shows initial cash ($100,000) when no trades exist |
| AC12 | Backfill progress visible in Jobs tab (completed/pending/failed counts) |
| AC13 | No frontend crashes or blank screens on any page |
| AC14 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| Observability jobs endpoint handler | Background job status aggregation |
| Observability database stats endpoint handler | DB stats via pg_stat queries |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/observability/router.py` | Add `/jobs` and `/database/stats` endpoints |
| `backend/app/main.py` or health registration | Register market_data + strategies health status |
| `backend/app/market_data/` startup | Report health status after initialization |
| `backend/app/strategies/` startup | Report health status after initialization |
| `backend/app/observability/` alert rules | Fix WebSocket alert to check market hours + symbol count |
| `backend/app/portfolio/service.py` or router | Return initial cash when no portfolio data exists |
| `frontend/src/` status bar component | Read broker status from correct field/endpoint |
| `frontend/src/pages/Settings.tsx` | Fix system tab route (if frontend issue) |

## Builder Notes

- **Check backend logs on VPS** (`docker compose -f docker-compose.prod.yml logs backend --tail=200`) for any startup errors that explain the "Unknown" module statuses.
- **The observability spec defines the Jobs and Database views** — check `observability_module_spec.md` for expected response shapes if the frontend components already exist.
- **The status bar component** is likely in `AppShell.tsx` or a `StatusBar.tsx` component. Check what API it polls and what fields it reads.
- **For the database stats endpoint**, use raw SQL via SQLAlchemy `text()` for the pg_stat queries — these are Postgres system catalog queries, not ORM operations.
- **Market hours check:** US equity market hours are 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC). The alert should only fire during this window.
- **Initial cash seeding:** The cleanest approach is to seed a `PortfolioMeta` record during startup with `cash = PAPER_TRADING_INITIAL_CASH`. If a record already exists, don't overwrite it.

## References

- observability_module_spec.md — event system, metrics, background jobs
- frontend_specs.md §View 9 — System Telemetry (Health, Pipeline, Activity, Jobs, Database tabs)
- frontend_specs.md §1 — App Shell (status bar)
- portfolio_module_spec.md — portfolio summary, initial cash
- cross_cutting_specs.md §5 — API conventions (response envelope)
