#!/bin/bash
set -e

# === Load environment ===
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.production.example to .env and fill in values."
    exit 1
fi
set -a; source .env; set +a

DOMAIN="${DOMAIN:?Set DOMAIN in .env}"

echo "=========================================="
echo "  Ratatoskr Deployment"
echo "  Domain: $DOMAIN"
echo "=========================================="

# === Step 1: Build images ===
echo "Building images..."
docker compose -f docker-compose.prod.yml build

# === Step 2: Start database and wait for healthy ===
echo "Starting database..."
docker compose -f docker-compose.prod.yml up -d db
echo "Waiting for database..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U "${POSTGRES_USER:-postgres}" 2>/dev/null; then
        echo "Database ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# === Step 3: Run migrations (before backend starts) ===
echo "Running migrations..."
docker compose -f docker-compose.prod.yml run --rm -T backend \
    python -m alembic upgrade head

# === Step 4: Seed admin user ===
echo "Seeding admin user..."
docker compose -f docker-compose.prod.yml run --rm -T backend \
    python -c "
import asyncio
from app.auth.seed import seed_admin_user
asyncio.run(seed_admin_user())
" 2>/dev/null || echo "Admin seed skipped (may already exist)"

# === Step 5: Start all services ===
echo "Starting all services..."
docker compose -f docker-compose.prod.yml up -d

# === Step 6: Wait for backend health ===
echo "Waiting for backend..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.prod.yml exec -T backend \
        python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" 2>/dev/null; then
        echo "Backend healthy!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "=========================================="
echo "  Deployment complete!"
echo "  https://$DOMAIN"
echo "  Health: https://$DOMAIN/api/v1/health"
echo "=========================================="
