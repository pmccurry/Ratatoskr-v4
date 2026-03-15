# TASK-037 — VPS Deployment (DigitalOcean + Docker Compose + SSL)

## Goal

Deploy the full Ratatoskr stack to a DigitalOcean VPS with Docker Compose, SSL via Let's Encrypt, and a custom domain. After this task, the platform is accessible at `https://production.ratatoskr.trade` with persistent broker connections, live data streaming, and a real frontend.

## Deployment Target

```
Droplet IP:  64.23.179.83
Domain:      production.ratatoskr.trade
GitHub:      https://github.com/pmccurry/Ratatoskr-v4.git
OS:          Ubuntu (fresh droplet, nothing installed)
```

## Depends On

TASK-036c (all connectivity bugs fixed)

## Scope

**In scope:**
- `scripts/server-setup.sh` — one-shot server provisioning script (Docker, firewall, swap, user)
- `docker-compose.prod.yml` — production-optimized compose with nginx reverse proxy, certbot, auto-renewal
- Production nginx config with SSL termination, API proxy, SPA fallback
- Deployment script (`scripts/deploy.sh`) for initial deployment and SSL bootstrap
- Update script (`scripts/update.sh`) for code changes
- `.env.production.example` — production-specific env template
- `README.md` deployment section
- Frontend environment config (API base URL pointing to real domain)

**Out of scope:**
- CI/CD pipeline (GitHub Actions, etc.)
- Kubernetes
- Multi-server / load balancing
- Monitoring infrastructure (Prometheus, Grafana)
- Application code changes (except frontend API base URL config)

---

## Deliverables

### D0 — `scripts/server-setup.sh` (run once on fresh droplet)

This script is run manually by the operator on the fresh DigitalOcean droplet. It installs everything needed.

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "  Ratatoskr Server Setup"
echo "  Target: 64.23.179.83"
echo "=========================================="

# === System Updates ===
echo "Updating system..."
apt-get update && apt-get upgrade -y

# === Install Docker ===
echo "Installing Docker..."
curl -fsSL https://get.docker.com | sh

# === Install Docker Compose plugin ===
# (Included with modern Docker, but verify)
docker compose version || {
    echo "Installing Docker Compose plugin..."
    apt-get install -y docker-compose-plugin
}

# === Create swap (2GB — helps on small droplets) ===
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# === Firewall ===
echo "Configuring firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# === Create app user ===
if ! id "ratatoskr" &>/dev/null; then
    echo "Creating ratatoskr user..."
    useradd -m -s /bin/bash -G docker ratatoskr
fi

# === Create app directory ===
mkdir -p /opt/ratatoskr
chown ratatoskr:ratatoskr /opt/ratatoskr

# === Install git ===
apt-get install -y git

echo ""
echo "=========================================="
echo "  Server setup complete!"
echo ""
echo "  Next steps:"
echo "  1. su - ratatoskr"
echo "  2. cd /opt/ratatoskr"
echo "  3. git clone https://github.com/pmccurry/Ratatoskr-v4.git ."
echo "  4. cp .env.production.example .env"
echo "  5. nano .env  (fill in all values)"
echo "  6. ./scripts/deploy.sh"
echo "=========================================="
```

Make executable: `chmod +x scripts/server-setup.sh`

**Operator runs this via:**
```bash
ssh root@64.23.179.83
# Copy and paste the script, or:
curl -sSL https://raw.githubusercontent.com/pmccurry/Ratatoskr-v4/main/scripts/server-setup.sh | bash
```

### D1 — `docker-compose.prod.yml`

Production compose file with 5 services:

```yaml
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # No port exposure — only accessible from internal network

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    restart: unless-stopped
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    # No port exposure — nginx proxies to it

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: ${VITE_API_BASE_URL:-/api/v1}
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    # No port exposure — nginx proxies to it

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/prod.conf:/etc/nginx/conf.d/default.conf:ro
      - certbot_data:/var/www/certbot:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - frontend
      - backend

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_data:/var/www/certbot
      - certbot_certs:/etc/letsencrypt
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  postgres_data:
  certbot_data:
  certbot_certs:
```

Key differences from dev compose:
- **No port exposure** on db, backend, frontend — nginx is the only entry point
- **nginx service** handles SSL termination, proxies to backend and frontend
- **certbot service** handles Let's Encrypt certificate renewal
- **restart: unless-stopped** — survives VPS reboots
- **Build arg** passes `VITE_API_BASE_URL` to frontend build

### D2 — `nginx/prod.conf`

Production nginx config with SSL:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name ${DOMAIN};

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }

    # Frontend (SPA)
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;
}
```

**Note:** The `${DOMAIN}` placeholder needs to be replaced. Use `envsubst` in the deploy script or a templated conf.

### D3 — `.env.production.example`

Production-specific env template:

```env
# === Domain ===
DOMAIN=production.ratatoskr.trade
CERTBOT_EMAIL=admin@ratatoskr.trade

# === Environment ===
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# === Database ===
POSTGRES_USER=ratatoskr
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=ratatoskr_prod
DATABASE_URL=postgresql+asyncpg://ratatoskr:CHANGE_ME_STRONG_PASSWORD@db:5432/ratatoskr_prod

# === Auth ===
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
AUTH_JWT_SECRET_KEY=CHANGE_ME_GENERATE_WITH_COMMAND_ABOVE
ADMIN_SEED_EMAIL=admin@ratatoskr.trade
ADMIN_SEED_PASSWORD=CHANGE_ME_STRONG_PASSWORD

# === CORS ===
CORS_ALLOWED_ORIGINS=https://production.ratatoskr.trade

# === Frontend ===
VITE_API_BASE_URL=/api/v1

# === Alpaca ===
ALPACA_API_KEY=
ALPACA_API_SECRET=
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/iex

# === OANDA ===
OANDA_ACCESS_TOKEN=
OANDA_ACCOUNT_ID=
OANDA_BASE_URL=https://api-fxpractice.oanda.com
OANDA_STREAM_URL=https://stream-fxpractice.oanda.com

# (Include all other variables from .env.example with production defaults)
```

### D4 — `scripts/deploy.sh`

Initial deployment and update script:

```bash
#!/bin/bash
set -e

# === Configuration ===
DOMAIN="${DOMAIN:?Set DOMAIN in .env}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:?Set CERTBOT_EMAIL in .env}"

echo "=========================================="
echo "  Ratatoskr Deployment"
echo "  Domain: $DOMAIN"
echo "=========================================="

# === Step 1: Load environment ===
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.production.example to .env and fill in values."
    exit 1
fi
set -a; source .env; set +a

# === Step 2: Generate nginx conf from template ===
echo "Generating nginx config..."
mkdir -p nginx
envsubst '${DOMAIN}' < nginx/prod.conf.template > nginx/prod.conf

# === Step 3: Initial SSL certificate (first time only) ===
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ] && [ ! -f "certbot_initialized" ]; then
    echo "Obtaining initial SSL certificate..."
    
    # Start nginx with HTTP-only config for ACME challenge
    docker compose -f docker-compose.prod.yml up -d nginx
    
    # Get certificate
    docker compose -f docker-compose.prod.yml run --rm certbot \
        certonly --webroot --webroot-path=/var/www/certbot \
        --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email \
        -d "$DOMAIN"
    
    touch certbot_initialized
    
    # Restart nginx with SSL config
    docker compose -f docker-compose.prod.yml restart nginx
fi

# === Step 4: Build and start all services ===
echo "Building and starting services..."
docker compose -f docker-compose.prod.yml up -d --build

# === Step 5: Wait for backend health ===
echo "Waiting for backend..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.prod.yml exec backend python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" 2>/dev/null; then
        echo "Backend healthy!"
        break
    fi
    sleep 2
done

# === Step 6: Run migrations ===
echo "Running migrations..."
docker compose -f docker-compose.prod.yml exec backend \
    python -m alembic upgrade head

# === Step 7: Seed admin user ===
echo "Seeding admin user..."
docker compose -f docker-compose.prod.yml exec backend \
    python /app/scripts/seed_admin.py || true

# === Step 8: Verify ===
echo ""
echo "=========================================="
echo "  Deployment complete!"
echo "  https://$DOMAIN"
echo "  Health: https://$DOMAIN/api/v1/health"
echo "=========================================="
```

Make executable: `chmod +x scripts/deploy.sh`

### D5 — `scripts/update.sh`

Quick update script for code changes (no SSL re-init):

```bash
#!/bin/bash
set -e
set -a; source .env; set +a

echo "Pulling latest code..."
git pull

echo "Rebuilding and restarting..."
docker compose -f docker-compose.prod.yml up -d --build

echo "Running migrations..."
docker compose -f docker-compose.prod.yml exec backend \
    python -m alembic upgrade head || true

echo "Done! https://$DOMAIN"
```

### D6 — `nginx/prod.conf.template`

Same as D2 but with `${DOMAIN}` as literal placeholder for `envsubst`:

```nginx
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;
}
```

### D7 — Frontend API base URL configuration

The frontend needs to know the API URL at build time. Verify that `frontend/src/lib/api.ts` (or equivalent) uses:

```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
});
```

The `VITE_API_BASE_URL=/api/v1` is passed as a build arg in `docker-compose.prod.yml`. Since nginx proxies `/api/` to the backend, the relative path `/api/v1` works in both local dev and production.

If the frontend currently uses `http://localhost:8000/api/v1` hardcoded anywhere, it must be changed to use the env var.

### D8 — README deployment section

```markdown
## Production Deployment (DigitalOcean)

### Prerequisites
- DigitalOcean Droplet (2GB+ RAM, Ubuntu 22.04+)
- Domain `production.ratatoskr.trade` with A record pointing to `64.23.179.83`

### Initial Setup

1. SSH into the Droplet:
   ```bash
   ssh root@64.23.179.83
   ```

2. Run server setup:
   ```bash
   curl -sSL https://raw.githubusercontent.com/pmccurry/Ratatoskr-v4/main/scripts/server-setup.sh | bash
   ```

3. Switch to app user and clone:
   ```bash
   su - ratatoskr
   cd /opt/ratatoskr
   git clone https://github.com/pmccurry/Ratatoskr-v4.git .
   ```

4. Create production env:
   ```bash
   cp .env.production.example .env
   nano .env  # Fill in all values — especially passwords, JWT secret, broker keys
   ```

5. Deploy:
   ```bash
   ./scripts/deploy.sh
   ```

6. Visit `https://production.ratatoskr.trade`

### Updating

```bash
ssh root@64.23.179.83
su - ratatoskr
cd /opt/ratatoskr
./scripts/update.sh
```

### Monitoring

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Check health
curl https://production.ratatoskr.trade/api/v1/health

# Run readiness check
docker compose -f docker-compose.prod.yml exec backend \
    python /app/scripts/readiness_check.py
```

### Backup Database

```bash
docker compose -f docker-compose.prod.yml exec db \
    pg_dump -U ratatoskr ratatoskr_prod > backup_$(date +%Y%m%d).sql
```
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `scripts/server-setup.sh` installs Docker, configures firewall (80/443/SSH), creates swap, creates app user |
| AC2 | `docker-compose.prod.yml` defines 5 services: db, backend, frontend, nginx, certbot |
| AC3 | Only nginx exposes ports (80, 443) — db/backend/frontend are internal only |
| AC4 | `nginx/prod.conf.template` has HTTP→HTTPS redirect, SSL config, API proxy, SPA fallback |
| AC5 | `nginx/init.conf` exists for HTTP-only SSL bootstrap phase |
| AC6 | Security headers present: X-Frame-Options, X-Content-Type-Options, HSTS |
| AC7 | `.env.production.example` has ALL variables from `.env.example` plus DOMAIN, CERTBOT_EMAIL, with CHANGE_ME placeholders for secrets |
| AC8 | `CORS_ALLOWED_ORIGINS` defaults to `https://production.ratatoskr.trade` |
| AC9 | `scripts/deploy.sh` handles: env check, nginx config generation, SSL cert bootstrap, build, migrations, seed |
| AC10 | `scripts/update.sh` handles: git pull, rebuild, migrations |
| AC11 | Frontend uses `VITE_API_BASE_URL` env var (not hardcoded localhost) |
| AC12 | Certbot auto-renewal runs in background |
| AC13 | All services have `restart: unless-stopped` |
| AC14 | README has deployment section with DigitalOcean instructions referencing real domain and IP |
| AC15 | No application logic modified (only infra/config/scripts) |
| AC16 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/server-setup.sh` | One-shot server provisioning (Docker, firewall, swap, user) |
| `docker-compose.prod.yml` | Production compose with nginx + certbot |
| `nginx/prod.conf.template` | SSL nginx config template (envsubst replaces DOMAIN) |
| `nginx/init.conf` | HTTP-only nginx config for SSL bootstrap phase |
| `.env.production.example` | Production env template with real domain and all variables |
| `scripts/deploy.sh` | Initial deployment script with SSL bootstrap |
| `scripts/update.sh` | Code update script |

## Files to Modify

| File | What Changes |
|------|-------------|
| `frontend/src/lib/api.ts` | Verify uses `VITE_API_BASE_URL` env var (fix if hardcoded) |
| `frontend/Dockerfile` | Add `ARG VITE_API_BASE_URL` and `ENV VITE_API_BASE_URL` before build step |
| `README.md` | Add deployment section |

## Files NOT to Touch

- Backend application code
- Frontend components/pages
- Test files
- Studio files

---

## Builder Notes

## Builder Notes

- **The domain is `production.ratatoskr.trade` and the IP is `64.23.179.83`.** Use these exact values in `.env.production.example`. The deploy script uses `${DOMAIN}` from `.env` for `envsubst`.
- **The GitHub repo is `https://github.com/pmccurry/Ratatoskr-v4.git`.** Reference this in server-setup.sh and README.
- **The builder cannot SSH into the droplet.** All files are produced in the repo. The operator runs the scripts manually on the VPS.
- **SSL bootstrap chicken-and-egg:** Nginx needs certs to start HTTPS, but certbot needs nginx to serve the ACME challenge. The deploy script handles this by first starting nginx with HTTP-only, getting the cert, then restarting with the full SSL config. Create a separate `nginx/init.conf` for the HTTP-only bootstrap phase.
- **Dockerfile.backend build context:** The production compose uses the same `Dockerfile.backend` from TASK-023. The build context is the repo root.
- **Frontend build arg:** `VITE_API_BASE_URL` must be available at build time (not runtime) because Vite inlines env vars during the build. Pass it as a Docker build arg.
- **Seed script path:** In Docker, the seed script needs to be accessible. Check the Dockerfile.backend to see if `scripts/` is copied. If not, add a COPY line or mount as volume.
- **The `.env.production.example` must include ALL variables** from the existing `.env.example` with production-appropriate defaults, plus the new deployment variables (DOMAIN, CERTBOT_EMAIL). Include every variable, not just the highlights.

## References

- CLAUDE.md — "Infra: Docker Compose"
- TASK-023 — Dockerfile.backend, frontend/Dockerfile, docker-compose.yml (dev)
- TASK-025 — CORS hardening, JWT production guard, environment variable
- TASK-035 — Readiness check script
- cross_cutting_specs.md §3 — Configuration System
