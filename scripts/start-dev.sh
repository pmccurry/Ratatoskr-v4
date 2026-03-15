#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env into shell environment
set -a
source "$REPO_ROOT/.env" 2>/dev/null || true
set +a

# Override DATABASE_URL for local dev (Docker service name → localhost)
export DATABASE_URL="${DATABASE_URL//db:5432/localhost:5432}"

# 1. Start Postgres via Docker Compose (just the db service)
docker compose -f "$REPO_ROOT/docker-compose.yml" up -d db

# 2. Wait for Postgres to be healthy
echo "Waiting for Postgres..."
until docker compose -f "$REPO_ROOT/docker-compose.yml" exec db pg_isready -U postgres 2>/dev/null; do
  sleep 1
done
echo "Postgres ready."

# 3. Run Alembic migrations
echo "Running migrations..."
(cd "$REPO_ROOT/backend" && uv run alembic upgrade head)

# 4. Seed admin user
echo "Seeding admin user..."
(cd "$REPO_ROOT/backend" && uv run python "$REPO_ROOT/scripts/seed_admin.py")

# 5. Start backend (background)
echo "Starting backend..."
(cd "$REPO_ROOT/backend" && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# 6. Wait for backend health
echo "Waiting for backend..."
until curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; do
  sleep 1
done
echo "Backend ready."

# 7. Start frontend (background)
echo "Starting frontend..."
(cd "$REPO_ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

# 8. Trap for clean shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose -f '$REPO_ROOT/docker-compose.yml' stop db" EXIT

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
