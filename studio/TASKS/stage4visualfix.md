# TASK-023a — Docker Startup Hotfix

## Goal

Fix 3 bugs in the TASK-023 Docker/startup deliverables that prevent the app from booting.

## Depends On

TASK-023

## Scope

Three targeted fixes. Nothing else.

---

## Fix 1 — Database name mismatch

**Problem:** `.env.example` has `DATABASE_URL` pointing to a database named `ratatoskr`, but `POSTGRES_DB` is set to `trading_platform`. Docker Compose creates `trading_platform`, the backend tries to connect to `ratatoskr`, connection fails.

**Fix:** In `.env.example`, ensure DATABASE_URL uses `trading_platform` as the database name, matching `POSTGRES_DB`:

```env
POSTGRES_DB=trading_platform
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/trading_platform
```

Both must say `trading_platform`. This is the name defined in cross_cutting_specs.md.

---

## Fix 2 — Seed script execution path

**Problem:** `scripts/start-dev.sh` runs `uv run python scripts/seed_admin.py` from the repo root. But `uv` looks for `pyproject.toml` in the current directory — which at repo root either doesn't exist or isn't the backend's. The script fails to find dependencies.

**Fix:** In `scripts/start-dev.sh`, run the seed script from `backend/`:

```bash
# Before (broken):
uv run python scripts/seed_admin.py

# After (fixed):
cd backend && uv run python ../scripts/seed_admin.py && cd ..
```

Apply the same pattern to the alembic migration line if it doesn't already `cd backend`.

---

## Fix 3 — DATABASE_URL override is a no-op

**Problem:** `scripts/start-dev.sh` line 5 does `export DATABASE_URL="${DATABASE_URL//db:5432/localhost:5432}"`. But if the `.env` file already has `localhost` in the URL (which it does after the builder's implementation), this substitution matches nothing and does nothing. The real design is: `.env.example` uses `db` (for Docker Compose), and `start-dev.sh` overrides to `localhost` (for local dev).

**Fix:** After Fix 1 makes `.env.example` use `db:5432`, the override becomes functional. But the script also needs to load the `.env` values first, otherwise `DATABASE_URL` is empty in the shell and the substitution produces an empty string.

Add to `scripts/start-dev.sh` before the override line:

```bash
# Load .env into shell environment
set -a
source .env 2>/dev/null || true
set +a

# Override for local dev (Docker service name → localhost)
export DATABASE_URL="${DATABASE_URL//db:5432/localhost:5432}"
```

The `set -a` / `set +a` causes all sourced variables to be exported automatically.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `.env.example` DATABASE_URL database name matches POSTGRES_DB (both `trading_platform`) |
| AC2 | `scripts/start-dev.sh` runs seed script from `backend/` directory (or equivalent working path) |
| AC3 | `scripts/start-dev.sh` sources `.env` before the DATABASE_URL override substitution |
| AC4 | `scripts/start-dev.sh` DATABASE_URL override correctly substitutes `db:5432` → `localhost:5432` |
| AC5 | No backend application code modified |
| AC6 | No frontend application code modified |

## Files to Modify

| File | What Changes |
|------|-------------|
| `.env.example` | Fix database name in DATABASE_URL to `trading_platform` |
| `scripts/start-dev.sh` | Source `.env`, fix seed script path |

## Files NOT to Touch

Everything else.
