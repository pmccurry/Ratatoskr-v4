#!/bin/bash
set -e
set -a; source .env; set +a

echo "Pulling latest code..."
git pull

echo "Regenerating nginx config..."
envsubst '${DOMAIN}' < nginx/prod.conf.template > nginx/prod.conf

echo "Rebuilding and restarting..."
docker compose -f docker-compose.prod.yml up -d --build

echo "Waiting for backend..."
sleep 10

echo "Running migrations..."
docker compose -f docker-compose.prod.yml exec -T backend \
    sh -c "cd /app/backend && python -m alembic upgrade head" || true

echo "Done! https://${DOMAIN}"
