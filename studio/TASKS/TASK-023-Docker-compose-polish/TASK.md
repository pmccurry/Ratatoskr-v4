# TASK-023 — Docker Compose and Startup Polish

## Goal

Get the full stack bootable with one command. After this task, a fresh clone can run `docker compose up` (or `scripts/start-dev.sh`) and have Postgres running, backend serving, frontend accessible, migrations applied, and an admin user seeded — ready for the Stage 4 visual review.

## Depends On

TASK-021, TASK-022 (bug fixes complete)

## Scope

**In scope:**
- Fix `Dockerfile.backend` for correct uv-based Python setup
- Fix `Dockerfile.frontend` for nginx-served production build with SPA fallback
- Fix `docker-compose.yml` with correct service definitions, health checks, volume mounts, and networking
- Ensure `.env.example` has every variable from cross_cutting_specs.md §Configuration Variables Summary, with sensible defaults and Docker Compose service names (not localhost)
- Create `scripts/seed_admin.py` — standalone script that creates the initial admin user if none exists
- Create `scripts/start-dev.sh` — handles Postgres wait, migrations, seed, backend start, frontend start (for local dev without full Docker)
- Update `README.md` with quickstart instructions for both Docker Compose and local dev

**Out of scope:**
- Production deployment (k8s, cloud). This is dev-only.
- CI/CD pipelines
- New features or modules
- Any backend or frontend application code changes (only infra/config files)

---

## Deliverables

### D1 — `Dockerfile.backend`

Location: repo root (`Dockerfile.backend`)

```dockerfile
# Multi-stage: builder + runtime
# Builder stage:
#   - FROM python:3.12-slim
#   - Install uv (pip install uv or copy from official uv image)
#   - Set WORKDIR /app
#   - Copy pyproject.toml and uv.lock
#   - Run: uv sync --frozen --no-dev
#   - Copy application code
# Runtime stage:
#   - FROM python:3.12-slim
#   - Copy virtual env from builder
#   - Copy application code
#   - EXPOSE 8000
#   - CMD: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Key requirements:
- Uses `uv sync --frozen --no-dev` (not pip install)
- Multi-stage build to keep image small
- Working directory is `/app`
- Backend code lives at `/app/backend/`
- Entrypoint uses uvicorn pointing to `backend.app.main:app`
- If uv.lock does not exist yet, use `uv sync --no-dev` (without --frozen) and note in BUILDER_OUTPUT.md

### D2 — `Dockerfile.frontend`

Location: `frontend/Dockerfile`

```dockerfile
# Multi-stage: build + serve
# Build stage:
#   - FROM node:20-slim
#   - Set WORKDIR /app
#   - Copy package.json and package-lock.json (or pnpm-lock.yaml, whichever exists)
#   - Run: npm ci (or pnpm install --frozen-lockfile)
#   - Copy frontend source
#   - Run: npm run build (or pnpm build)
# Serve stage:
#   - FROM nginx:alpine
#   - Copy build output from builder to /usr/share/nginx/html
#   - Copy nginx.conf with SPA fallback
#   - EXPOSE 80
```

Key requirements:
- SPA fallback: all routes that don't match a static file serve `index.html`
- API proxy: requests to `/api/` proxy to the backend service
- Check which package manager is used (npm or pnpm) and use the correct commands

### D3 — `frontend/nginx.conf`

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — any route that doesn't match a file serves index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy to backend service
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### D4 — `docker-compose.yml`

Three services:

**db:**
- Image: `postgres:16-alpine`
- Environment: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` from `.env`
- Health check: `pg_isready -U ${POSTGRES_USER:-postgres}`
- Volume: `postgres_data:/var/lib/postgresql/data`
- Port: `5432:5432`

**backend:**
- Build context: `.` with dockerfile `Dockerfile.backend`
- Depends on: `db` (condition: `service_healthy`)
- Environment: loads from `.env` via `env_file: .env`
- Port: `8000:8000`
- Command (dev): `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload`
- Volumes (dev): `./backend:/app/backend` (enables live reload)
- Health check: `curl -f http://localhost:8000/api/v1/health || exit 1`
  - Use `start_period: 15s` to give the app time to boot
  - If curl is not available in the image, use `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"` instead

**frontend:**
- Build context: `./frontend` with dockerfile `Dockerfile` (relative to context)
- Depends on: `backend` (condition: `service_healthy`)
- Port: `3000:80`

Named volume: `postgres_data`

### D5 — `.env.example`

Must contain **every** variable from cross_cutting_specs.md §Configuration Variables Summary (lines 953–1091 of that file). All variables must be present. Required variables use placeholder values with comments. Optional variables have their defaults filled in.

**Critical overrides for Docker Compose:**

```env
# === Docker Compose ===
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=trading_platform

# === Database ===
# NOTE: 'db' is the Docker Compose service name. Change to 'localhost' for local dev.
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/trading_platform
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# === Admin Seed ===
ADMIN_SEED_EMAIL=admin@ratatoskr.local
ADMIN_SEED_PASSWORD=changeme123456
```

For broker credentials (ALPACA_API_KEY, ALPACA_API_SECRET, OANDA_ACCESS_TOKEN, OANDA_ACCOUNT_ID), use empty strings with comments:
```env
# Required for broker connectivity. Leave empty to run without broker features.
ALPACA_API_KEY=
ALPACA_API_SECRET=
```

For `AUTH_JWT_SECRET_KEY`, use a dev-only default with a warning comment:
```env
# CHANGE THIS IN PRODUCTION — generate with: python -c "import secrets; print(secrets.token_hex(32))"
AUTH_JWT_SECRET_KEY=dev-only-change-me-in-production-abc123
```

### D6 — `scripts/seed_admin.py`

Standalone Python script:

1. Reads `ADMIN_SEED_EMAIL` and `ADMIN_SEED_PASSWORD` from environment (falls back to `.env` via python-dotenv or manual parsing)
2. Reads `DATABASE_URL` from environment
3. Converts async DATABASE_URL to sync format (replace `postgresql+asyncpg://` with `postgresql://`)
4. Connects using **synchronous** SQLAlchemy (this is a one-shot script, not async)
5. Checks if any user with `role = 'admin'` exists in the `users` table
6. If not: creates user with bcrypt-hashed password, `role='admin'`, `status='active'`
7. If yes: prints "Admin user already exists, skipping seed" and exits 0
8. Prints confirmation with the email used

Must be runnable as: `uv run python scripts/seed_admin.py`

Import the User model from `backend.app.auth.models` if that import works from the script location. If not (due to Python path issues), use raw SQL INSERT via SQLAlchemy text() — the table is `users` with columns: `id` (UUID), `email`, `hashed_password`, `role`, `status`, `created_at`, `updated_at`.

Use bcrypt for password hashing — import from `passlib.context` (CryptContext with bcrypt scheme) matching the pattern used in `backend/app/auth/`.

### D7 — `scripts/start-dev.sh`

Bash script for local development:

```bash
#!/bin/bash
set -e

# 1. Start Postgres via Docker Compose (just the db service)
docker compose up -d db

# 2. Wait for Postgres to be healthy
echo "Waiting for Postgres..."
until docker compose exec db pg_isready -U postgres 2>/dev/null; do
  sleep 1
done
echo "Postgres ready."

# 3. Run Alembic migrations
echo "Running migrations..."
uv run alembic upgrade head

# 4. Seed admin user
echo "Seeding admin user..."
uv run python scripts/seed_admin.py

# 5. Start backend (background)
echo "Starting backend..."
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 6. Wait for backend health
echo "Waiting for backend..."
until curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; do
  sleep 1
done
echo "Backend ready."

# 7. Start frontend (background)
echo "Starting frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

# 8. Trap for clean shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose stop db" EXIT

echo ""
echo "============================================"
echo "  Ratatoskr is running!"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Login:    admin@ratatoskr.local"
echo "============================================"
echo ""

wait
```

Make executable: `chmod +x scripts/start-dev.sh`

**Important:** The script must use `DATABASE_URL` with `localhost` (not `db`). Either:
- (a) The script sets `DATABASE_URL` override before running alembic/seed, or
- (b) The README tells users to change `db` to `localhost` in `.env` when using local dev

Option (a) is preferred. Add near the top of the script:
```bash
# Override DATABASE_URL for local dev (host is localhost, not Docker service name)
export DATABASE_URL="${DATABASE_URL//db:5432/localhost:5432}"
```

### D8 — `README.md` update

Add a **Quickstart** section near the top of the existing README. Keep any existing content.

```markdown
## Quickstart

### Option A — Docker Compose (full stack)

```bash
cp .env.example .env
# Edit .env with your broker API keys (optional — app runs without them)
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Login: `admin@ratatoskr.local` / `changeme123456`

### Option B — Local development

```bash
cp .env.example .env
# Edit .env: change 'db' to 'localhost' in DATABASE_URL
./scripts/start-dev.sh
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Login: `admin@ratatoskr.local` / `changeme123456`
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `Dockerfile.backend` uses uv (not pip), multi-stage build, runs uvicorn on port 8000 |
| AC2 | `Dockerfile.frontend` builds React app and serves via nginx with SPA fallback |
| AC3 | `nginx.conf` has SPA `try_files` fallback and `/api/` proxy to backend |
| AC4 | `docker-compose.yml` defines db, backend, frontend services with correct depends_on and health checks |
| AC5 | `docker-compose.yml` db service uses `postgres:16-alpine` with named volume |
| AC6 | `.env.example` contains ALL variables from cross_cutting_specs.md config catalog (every single one from the §Configuration Variables Summary section) |
| AC7 | `.env.example` DATABASE_URL uses `db` service name, not `localhost` |
| AC8 | `.env.example` includes `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` |
| AC9 | `scripts/seed_admin.py` creates admin user if none exists, skips if already seeded |
| AC10 | `scripts/seed_admin.py` uses bcrypt for password hashing (matching auth module pattern) |
| AC11 | `scripts/start-dev.sh` starts db, waits for health, runs migrations, seeds, starts backend+frontend |
| AC12 | `scripts/start-dev.sh` has clean shutdown trap (kills background processes, stops db) |
| AC13 | `scripts/start-dev.sh` overrides DATABASE_URL to use localhost instead of Docker service name |
| AC14 | `README.md` has quickstart for both Docker Compose and local dev with login credentials |
| AC15 | No backend application code modified (only infra/config/scripts) |
| AC16 | No frontend application code modified (only Dockerfile, nginx.conf) |
| AC17 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `Dockerfile.backend` | Multi-stage Python/uv backend image |
| `frontend/Dockerfile` | Multi-stage React build + nginx serve |
| `frontend/nginx.conf` | SPA fallback + API proxy |
| `scripts/seed_admin.py` | One-shot admin user seeder |
| `scripts/start-dev.sh` | Local dev startup script |

## Files to Modify

| File | What Changes |
|------|-------------|
| `docker-compose.yml` | Full rewrite with 3 services, health checks, volumes |
| `.env.example` | Complete variable catalog from cross_cutting_specs.md |
| `README.md` | Add Quickstart section |

## Files NOT to Touch

- Anything under `backend/app/`
- Anything under `frontend/src/`
- Anything under `studio/`
- `pyproject.toml` (unless a dependency is genuinely missing for seed script)
- `alembic.ini` or `alembic/` (migrations already work)

---

## References

- `cross_cutting_specs.md` §3 — Configuration System (Settings loading, .env conventions)
- `cross_cutting_specs.md` §8 — Startup Sequence (boot order)
- `cross_cutting_specs.md` §Configuration Variables Summary — complete env var catalog
- `auth_module_spec.md` §3 — MVP Simplification (one admin user)
- `auth_module_spec.md` §5 — Authentication Flow (registration, bcrypt)
- `DECISIONS.md` — tech stack: uv, FastAPI, PostgreSQL, Vite, Docker Compose
- `CLAUDE.md` — approved modules, universal rules

---

## Builder Notes

- Check which package manager the frontend uses (npm vs pnpm) before writing the frontend Dockerfile. Use whichever lockfile exists.
- Check whether `backend/app/main.py` already has a `/api/v1/health` endpoint. If not, note in BUILDER_OUTPUT.md but do NOT create one (that would be application code).
- The seed script should be idempotent — safe to run multiple times.
- If `uv.lock` doesn't exist, note it and use `uv sync --no-dev` instead of `uv sync --frozen --no-dev`.
- The `Dockerfile.backend` build context is the repo root (not `./backend`) because the Python package references `backend.app.main:app` — the `backend/` directory must be at `/app/backend/` in the container.
