#!/bin/bash
set -e

# === Load environment ===
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.production.example to .env and fill in values."
    exit 1
fi
set -a; source .env; set +a

DOMAIN="${DOMAIN:?Set DOMAIN in .env}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:?Set CERTBOT_EMAIL in .env}"

echo "=========================================="
echo "  Ratatoskr Deployment"
echo "  Domain: $DOMAIN"
echo "=========================================="

# === Step 1: Generate nginx config from template ===
echo "Generating nginx config..."
mkdir -p nginx
envsubst '${DOMAIN}' < nginx/prod.conf.template > nginx/prod.conf

# === Step 2: Initial SSL certificate (first time only) ===
if [ ! -f ".certbot_initialized" ]; then
    echo "Bootstrapping SSL certificate..."

    # Use HTTP-only config for ACME challenge
    cp nginx/init.conf nginx/prod.conf

    # Start only nginx and certbot prerequisites
    docker compose -f docker-compose.prod.yml up -d db
    docker compose -f docker-compose.prod.yml up -d nginx

    echo "Waiting for nginx to start..."
    sleep 5

    # Request certificate
    docker compose -f docker-compose.prod.yml run --rm certbot \
        certonly --webroot --webroot-path=/var/www/certbot \
        --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email \
        -d "$DOMAIN"

    # Restore full SSL config
    envsubst '${DOMAIN}' < nginx/prod.conf.template > nginx/prod.conf

    touch .certbot_initialized
    echo "SSL certificate obtained!"
fi

# === Step 3: Build and start all services ===
echo "Building and starting services..."
docker compose -f docker-compose.prod.yml up -d --build

# === Step 4: Wait for backend health ===
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

# === Step 5: Run migrations ===
echo "Running migrations..."
docker compose -f docker-compose.prod.yml exec -T backend \
    sh -c "cd /app/backend && python -m alembic upgrade head" || echo "Migration warning (may already be current)"

# === Step 6: Seed admin user ===
echo "Seeding admin user..."
docker compose -f docker-compose.prod.yml exec -T backend \
    python -c "
import asyncio, sys, os
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')
from app.auth.seed import seed_admin_user
asyncio.run(seed_admin_user())
" 2>/dev/null || echo "Admin seed skipped (may already exist)"

echo ""
echo "=========================================="
echo "  Deployment complete!"
echo "  https://$DOMAIN"
echo "  Health: https://$DOMAIN/api/v1/health"
echo "=========================================="
