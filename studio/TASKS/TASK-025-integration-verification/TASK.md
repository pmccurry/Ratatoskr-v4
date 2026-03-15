# TASK-025 — Integration Verification and Hardening

## Goal

Verify the full stack works end-to-end without broker keys, harden security and error handling for real use, fix the formatPnl/formatPercent negative sign bug, clean up stale Docker files, and ensure background tasks start/stop cleanly. After this task, the platform is ready for real operation once broker API keys are provided.

## Depends On

TASK-024

## Scope

**In scope:**
- Fix formatPnl/formatPercent negative sign display bug (from TASK-024 Validator findings)
- Verify backend starts without crashing when broker API keys are empty
- Verify all non-broker API endpoints return correct responses
- Verify frontend renders all views with empty data (no crashes, no blank screens)
- Harden CORS settings (not allow-all in production mode)
- Validate AUTH_JWT_SECRET_KEY is not the dev default in production
- Ensure .env is in .gitignore
- Verify Alembic migration applies cleanly on fresh database
- Verify global exception handler returns generic 500 (never exposes internals)
- Verify all background tasks start and stop cleanly without crashing the app
- Delete stale Dockerfiles at `infra/docker/`
- Add `.dockerignore` for faster builds
- Verify startup order matches cross_cutting_specs.md §8

**Out of scope:**
- Broker-connected testing (requires API keys the user may not have)
- Unit test creation (separate milestone task)
- New features
- Frontend visual changes beyond the formatPnl/formatPercent fix

---

## Deliverables

### D1 — Fix formatPnl/formatPercent negative sign bug

**Problem:** `formatPnl` uses `const sign = num >= 0 ? '+' : ''` and `Math.abs(num)`. For negative numbers, sign is empty and abs strips the negative, so `-50` renders as `$50.00` instead of `-$50.00`. Same pattern in `formatPercent`.

**Fix in `frontend/src/lib/formatters.ts`:**

```typescript
// formatPnl — fix sign logic
export function formatPnl(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return '—';
  const sign = num >= 0 ? '+' : '-';
  const formatted = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}$${formatted}`;
}

// formatPercent — fix sign logic
export function formatPercent(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return '—';
  const sign = num >= 0 ? '+' : '-';
  return `${sign}${Math.abs(num).toFixed(2)}%`;
}
```

Verify: `formatPnl(-50)` → `"-$50.00"`, `formatPnl(50)` → `"+$50.00"`, `formatPnl(0)` → `"+$0.00"`.
Verify: `formatPercent(-12.5)` → `"-12.50%"`, `formatPercent(12.5)` → `"+12.50%"`.

### D2 — Backend graceful startup without broker keys

**Verify** that the backend starts without crashing when `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `OANDA_ACCESS_TOKEN`, and `OANDA_ACCOUNT_ID` are empty strings in `.env`.

**Expected behavior:**
- Backend boots successfully
- Broker-dependent modules (WebSocket manager, universe filter, backfill) log warnings but do not crash
- All non-broker endpoints respond (auth, strategies, portfolio summary, risk overview, observability health)
- Health endpoint (`/api/v1/health`) returns 200 with broker status showing "disconnected" or "unconfigured"

**If the backend crashes on empty broker keys:**
- Find the module that crashes and add a guard:
  ```python
  if not settings.alpaca_api_key:
      logger.warning("Alpaca API key not configured — broker features disabled")
      return  # skip broker initialization
  ```
- Apply to both Alpaca and OANDA initialization paths
- The guard should be in the module's startup function, not scattered across every function

**If the backend already handles this gracefully:** document it in BUILDER_OUTPUT.md and move on.

### D3 — CORS hardening

**Check** `backend/app/main.py` (or wherever CORS middleware is configured).

**Current state (likely):** `allow_origins=["*"]` for development.

**Required state:**

```python
from backend.app.config import get_settings

settings = get_settings()

# CORS
cors_origins = settings.cors_allowed_origins  # comma-separated string from env

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins.split(",") if cors_origins else ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Add to `.env.example`:**
```env
# === CORS ===
# Comma-separated origins. Defaults to localhost:3000,5173 if empty.
CORS_ALLOWED_ORIGINS=
```

**Add to Settings class** (if not already present):
```python
cors_allowed_origins: str = ""
```

**If CORS is already properly configured:** document it and move on.

### D4 — JWT secret production guard

**Check** that the backend warns or refuses to start if `AUTH_JWT_SECRET_KEY` is the dev default value in a production context.

**Add a startup validation** (in the settings validation or app startup):

```python
if settings.auth_jwt_secret_key == "dev-only-change-me-in-production-abc123":
    if settings.environment == "production":
        raise RuntimeError("AUTH_JWT_SECRET_KEY must be changed from default in production")
    else:
        logger.warning("⚠️  Using default JWT secret — change this before production use")
```

**Add to `.env.example` if not present:**
```env
# Environment: development | production
ENVIRONMENT=development
```

**Add to Settings class if not present:**
```python
environment: str = "development"
```

### D5 — Verify .gitignore

**Check** that `.gitignore` includes:
```
.env
.env.local
.env.production
__pycache__/
*.pyc
.venv/
node_modules/
dist/
.DS_Store
*.egg-info/
postgres_data/
```

If any are missing, add them.

### D6 — Verify Alembic migration on fresh database

**Test:** Drop and recreate the database, then run `alembic upgrade head`.

```bash
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS trading_platform;"
docker compose exec db psql -U postgres -c "CREATE DATABASE trading_platform;"
cd backend && uv run alembic upgrade head
```

**Expected:** Migration applies cleanly with no errors. All tables created.

**If it fails:** Fix the migration chain. Common issues:
- Broken `down_revision` chain (a migration references a non-existent parent)
- Duplicate table or column names across migrations
- Missing import in a migration file

Document the result in BUILDER_OUTPUT.md either way.

### D7 — Verify global exception handler

**Check** that `backend/app/main.py` has both exception handlers from cross_cutting_specs.md §2:

1. `DomainError` handler → returns structured error JSON with correct HTTP status
2. Generic `Exception` handler → returns 500 with `INTERNAL_ERROR` code, never exposes traceback

**Test:** Verify that if you hit an endpoint that raises an unhandled exception, the response is:
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An internal error occurred",
    "details": {}
  }
}
```

**Not:**
```
Traceback (most recent call last):
  File "..."
```

If the handlers don't exist, add them per the spec. If they exist, verify the 500 handler doesn't leak internals and move on.

### D8 — Verify background tasks start/stop cleanly

**Check** that all background tasks defined in the startup sequence (cross_cutting_specs.md §8) start and stop without errors:

Background tasks to verify:
1. Strategy runner loop
2. Safety monitor
3. Signal expiry checker
4. Mark-to-market cycle
5. Snapshot cycle
6. Event batch writer
7. Metric collector
8. Alert evaluation loop
9. WebSocket connections (if broker keys present)
10. Approved signal watcher (consumer)

**Verification approach:**
1. Start the backend
2. Check logs for each background task starting (should see log lines for each)
3. Send SIGTERM (Ctrl+C / `docker compose stop`)
4. Check logs for graceful shutdown (each task should log stopping, no unhandled exceptions)

**If any background task crashes on startup** (likely because of empty broker keys or missing data):
- Add a try/except around the task startup that logs the error and continues
- The task failure should NOT crash the entire application
- Other tasks should continue running

**If the shutdown is not graceful** (tasks don't stop, orphaned connections):
- Ensure FastAPI lifespan/shutdown hooks cancel all background tasks
- Each task should have a cancellation token or flag it checks

Document what works and what needed fixing in BUILDER_OUTPUT.md.

### D9 — Delete stale Docker files

Delete the unused Dockerfiles from the old location:
- `infra/docker/Dockerfile.backend`
- `infra/docker/Dockerfile.frontend`

If `infra/docker/` is now empty, delete the directory too. If it contains other files, leave them.

### D10 — Add `.dockerignore`

Create `.dockerignore` at repo root:

```
.git
.env
.env.*
__pycache__
*.pyc
.venv
node_modules
dist
.DS_Store
*.egg-info
postgres_data
studio
.pytest_cache
.mypy_cache
```

And `frontend/.dockerignore`:

```
node_modules
dist
.env
.env.*
```

### D11 — Verify startup order

**Check** that the application startup in `backend/app/main.py` (lifespan function or startup event) follows the order defined in cross_cutting_specs.md §8:

```
1. Load Settings → validate required
2. Initialize database pool → verify reachable
3. Initialize auth
4. Initialize market data (broker configs, universe filter, WebSocket)
5. Initialize strategy (indicators, condition engine, runner, safety monitor)
6. Initialize signals (expiry checker)
7. Initialize risk (load config, check kill switch)
8. Initialize paper trading (executor, forex pool, signal watcher)
9. Initialize portfolio (MTM, snapshots, dividend checker)
10. Initialize observability (event writer, metrics, alerts)
11. Start HTTP server
12. Emit system.ready event
```

**If the order is wrong:** reorder the initialization calls.
**If some modules aren't initialized at startup:** note which ones and whether that's intentional (e.g., broker modules skipped when keys are empty).
**If the order is correct:** document it and move on.

Shutdown should be in reverse order.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `formatPnl(-50)` returns `"-$50.00"`, `formatPnl(50)` returns `"+$50.00"` |
| AC2 | `formatPercent(-12.5)` returns `"-12.50%"`, `formatPercent(12.5)` returns `"+12.50%"` |
| AC3 | Backend starts without crashing when all broker API keys are empty strings |
| AC4 | Health endpoint returns 200 when broker keys are empty |
| AC5 | CORS middleware uses configurable origins (not hardcoded `["*"]`) |
| AC6 | `CORS_ALLOWED_ORIGINS` variable exists in `.env.example` |
| AC7 | Backend warns or refuses to start with default JWT secret in production mode |
| AC8 | `ENVIRONMENT` variable exists in `.env.example` |
| AC9 | `.gitignore` includes `.env` and standard Python/Node ignores |
| AC10 | `alembic upgrade head` applies cleanly on a fresh (empty) database |
| AC11 | Global exception handler returns generic 500 JSON (never exposes traceback) |
| AC12 | All background tasks start without crashing the application |
| AC13 | Application shuts down gracefully (no orphaned tasks, no unhandled exceptions on SIGTERM) |
| AC14 | Stale Dockerfiles at `infra/docker/` are deleted |
| AC15 | `.dockerignore` exists at repo root and `frontend/` |
| AC16 | Startup order matches cross_cutting_specs.md §8 (or deviations documented with reason) |
| AC17 | No frontend code modified except `formatters.ts` |
| AC18 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `.dockerignore` | Repo root Docker build context exclusions |
| `frontend/.dockerignore` | Frontend Docker build context exclusions |

## Files to Modify

| File | What Changes |
|------|-------------|
| `frontend/src/lib/formatters.ts` | Fix negative sign in formatPnl and formatPercent |
| `backend/app/main.py` | CORS config, JWT guard, exception handlers, startup order (as needed) |
| `backend/app/config.py` | Add `cors_allowed_origins` and `environment` settings (if missing) |
| `.env.example` | Add CORS_ALLOWED_ORIGINS and ENVIRONMENT variables |
| `.gitignore` | Add missing entries if needed |

## Files to Delete

| File | Reason |
|------|--------|
| `infra/docker/Dockerfile.backend` | Replaced by `Dockerfile.backend` at repo root (TASK-023) |
| `infra/docker/Dockerfile.frontend` | Replaced by `frontend/Dockerfile` (TASK-023) |

## Files NOT to Touch

- Frontend code except `formatters.ts`
- Studio files
- Docker Compose, Dockerfiles (the new ones), startup scripts
- Module application logic (services, repositories, routers) unless a background task needs a startup guard

---

## Builder Notes

- This task is primarily verification with targeted fixes. Many deliverables may already be correct — if so, document "already correct" in BUILDER_OUTPUT.md and move on.
- The most likely items needing real code changes: formatter fix (D1), CORS (D3), JWT guard (D4), broker startup guards (D2), and background task error handling (D8).
- For D6 (Alembic verification): if you can't drop/recreate the database in the build environment, note it as "unable to verify" rather than skipping.
- For D8 (background tasks): focus on startup behavior. If the app starts and the logs show tasks initializing without errors, that's sufficient. You don't need to verify every task's runtime behavior.
- The `.env.example` already has most variables from TASK-023. Only add the new ones (CORS_ALLOWED_ORIGINS, ENVIRONMENT).

---

## References

- cross_cutting_specs.md §2 — Error Handling (exception handlers, error codes, status mapping)
- cross_cutting_specs.md §3 — Configuration System (Settings, .env conventions)
- cross_cutting_specs.md §8 — Startup Sequence (boot order, shutdown)
- cross_cutting_specs.md §Configuration Variables Summary
- TASK-024 VALIDATION.md — formatPnl/formatPercent negative sign bug
- TASK-023 BUILDER_OUTPUT.md — stale Dockerfiles at infra/docker/, missing .dockerignore
