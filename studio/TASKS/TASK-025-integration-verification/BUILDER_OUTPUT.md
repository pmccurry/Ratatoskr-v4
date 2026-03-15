# Builder Output — TASK-025

## Task
Integration Verification and Hardening

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `.dockerignore` — repo root Docker build context exclusions
- `frontend/.dockerignore` — frontend Docker build context exclusions

## Files Modified
- `frontend/src/lib/formatters.ts` — Fixed negative sign bug in `formatPnl` and `formatPercent`
- `backend/app/main.py` — CORS hardening (configurable origins), JWT secret production guard
- `backend/app/common/config.py` — Added `environment` and `cors_allowed_origins` settings
- `.env.example` — Added `ENVIRONMENT` and `CORS_ALLOWED_ORIGINS` variables
- `.gitignore` — Added `.env.production` to ignore list

## Files Deleted
- `infra/docker/Dockerfile.backend` — stale, replaced by `Dockerfile.backend` at repo root (TASK-023)
- `infra/docker/Dockerfile.frontend` — stale, replaced by `frontend/Dockerfile` (TASK-023)
- `infra/docker/` — directory removed (now empty)

## Acceptance Criteria Status
1. AC1: `formatPnl(-50)` returns `"-$50.00"`, `formatPnl(50)` returns `"+$50.00"` — ✅ Done (sign logic fixed: `num >= 0 ? '+' : '-'` with `Math.abs()`)
2. AC2: `formatPercent(-12.5)` returns `"-12.50%"`, `formatPercent(12.5)` returns `"+12.50%"` — ✅ Done (same sign fix pattern)
3. AC3: Backend starts without crashing when all broker API keys are empty strings — ✅ Already correct (all module startups wrapped in try/except in main.py lifespan; market data startup has additional try/except around universe filter, backfill, and per-broker WebSocket connections)
4. AC4: Health endpoint returns 200 when broker keys are empty — ✅ Already correct (health check only verifies database connectivity, not broker status)
5. AC5: CORS middleware uses configurable origins (not hardcoded `["*"]`) — ✅ Done (reads `cors_allowed_origins` from Settings, defaults to `localhost:3000,5173`)
6. AC6: `CORS_ALLOWED_ORIGINS` variable exists in `.env.example` — ✅ Done
7. AC7: Backend warns or refuses to start with default JWT secret in production mode — ✅ Done (raises `RuntimeError` if `environment == "production"` and secret is default; logs warning otherwise)
8. AC8: `ENVIRONMENT` variable exists in `.env.example` — ✅ Done
9. AC9: `.gitignore` includes `.env` and standard Python/Node ignores — ✅ Already correct (had `.env`, `.env.local`, `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `dist/`, `.DS_Store`, `*.egg-info/`, `postgres_data/`); added `.env.production`
10. AC10: `alembic upgrade head` applies cleanly on a fresh (empty) database — ✅ Verified migration chain is complete and unbroken (10 migrations, all `down_revision` links valid: `None → 3f535bf → 7a15366 → a1b2c3d → b2c3d4e → c3d4e5f → d4e5f6a → e5f6a7b → f6a7b8c → g7b8c9d → h8c9d0e`). Unable to run live test (no Postgres in build environment).
11. AC11: Global exception handler returns generic 500 JSON (never exposes traceback) — ✅ Already correct (`unhandled_error_handler` in `errors.py` returns `{"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred", "details": {}}}` with status 500; traceback only logged server-side via `logger.exception`)
12. AC12: All background tasks start without crashing the application — ✅ Already correct (every module startup is wrapped in try/except in `main.py` lifespan with `(non-fatal)` logging; market data has per-broker try/except for WebSocket connections)
13. AC13: Application shuts down gracefully (no orphaned tasks, no unhandled exceptions on SIGTERM) — ✅ Already correct (shutdown in reverse order: portfolio → paper trading → risk → signals → strategies → market data → observability → database engine; each wrapped in try/except)
14. AC14: Stale Dockerfiles at `infra/docker/` are deleted — ✅ Done (both files and empty directory removed)
15. AC15: `.dockerignore` exists at repo root and `frontend/` — ✅ Done
16. AC16: Startup order matches cross_cutting_specs.md §8 (or deviations documented with reason) — ✅ Done with documented deviation (see below)
17. AC17: No frontend code modified except `formatters.ts` — ✅ Done
18. AC18: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **CORS default origins:** When `CORS_ALLOWED_ORIGINS` is empty, defaults to `["http://localhost:3000", "http://localhost:5173"]` — covering both Docker Compose (nginx on 3000) and local dev (Vite on 5173).
2. **Environment setting:** Defaults to `"development"`. The JWT guard only blocks startup in `"production"` mode — in development mode it just logs a warning.
3. **Alembic verification:** Verified migration chain integrity by inspecting all `revision`/`down_revision` links. Could not run `alembic upgrade head` live (no Postgres available in build environment). Chain is unbroken across all 10 migrations.

## Ambiguities Encountered
None — task and specs were unambiguous.

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Startup Order Analysis

**Spec order (cross_cutting_specs.md §8):**
1. Settings, 2. Database, 3. Auth, 4. Market Data, 5. Strategy, 6. Signals, 7. Risk, 8. Paper Trading, 9. Portfolio, 10. Observability, 11. HTTP Server, 12. system.ready

**Actual order in main.py:**
1. Settings ✅, 2. Database (implicit via SQLAlchemy) ✅, 3. Auth (implicit via router import) ✅, **DEVIATION: Observability starts here (before market data)**, 4. Market Data ✅, 5. Strategy ✅, 6. Signals ✅, 7. Risk ✅, 8. Paper Trading ✅, 9. Portfolio ✅, 10. (observability already started), 11. HTTP Server (implicit via uvicorn) ✅

**Deviation documented:** Observability starts FIRST instead of 10th. This is intentional and architecturally correct — other modules emit audit events during startup, so the event emitter must be running before them. The code comment explicitly states: "Start observability FIRST — other modules need the event emitter." No change made.

**Shutdown order:** Reverse of startup — portfolio → paper trading → risk → signals → strategies → market data → observability → database engine. Correct.

## Risks or Concerns
1. **Migration filename/revision mismatch:** Two migration files have filenames that don't match their internal revision IDs (e.g., `a1b2c3d4e5f6_create_portfolio_analytics_tables.py` has revision `g7b8c9d0e1f2`). Alembic uses the internal revision ID, so this works correctly, but it could confuse humans reading the filesystem.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
Milestone 13 — Testing and Validation: Begin writing the comprehensive test suite, starting with unit tests for critical paths (auth, risk engine, formatters).
