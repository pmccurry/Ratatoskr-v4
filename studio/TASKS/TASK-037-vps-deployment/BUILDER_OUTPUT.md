# Builder Output — TASK-037

## Task
VPS Deployment (DigitalOcean + Docker Compose + SSL)

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `scripts/server-setup.sh` — One-shot VPS provisioning (Docker, firewall, swap, app user)
- `docker-compose.prod.yml` — Production compose: 5 services (db, backend, frontend, nginx, certbot)
- `nginx/prod.conf.template` — SSL nginx config template with `${DOMAIN}` placeholder for envsubst
- `nginx/init.conf` — HTTP-only nginx config for SSL bootstrap phase
- `.env.production.example` — Complete production env template with all variables + DOMAIN/CERTBOT_EMAIL
- `scripts/deploy.sh` — Initial deployment with SSL bootstrap, build, migrations, seed
- `scripts/update.sh` — Quick update: git pull, rebuild, migrations

## Files Modified
- `frontend/Dockerfile` — Added `ARG VITE_API_BASE_URL` and `ENV VITE_API_BASE_URL` before build step
- `README.md` — Added Production Deployment section with setup, updating, monitoring, backup instructions
- `.gitignore` — Added `.certbot_initialized` and `nginx/prod.conf` (generated file)

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: `server-setup.sh` installs Docker, firewall (80/443/SSH), swap, app user — ✅ Done
2. AC2: `docker-compose.prod.yml` defines 5 services: db, backend, frontend, nginx, certbot — ✅ Done
3. AC3: Only nginx exposes ports (80, 443) — ✅ Done (db/backend/frontend have no `ports` directive)
4. AC4: `nginx/prod.conf.template` has HTTP→HTTPS redirect, SSL config, API proxy, SPA fallback — ✅ Done
5. AC5: `nginx/init.conf` exists for HTTP-only SSL bootstrap — ✅ Done
6. AC6: Security headers: X-Frame-Options, X-Content-Type-Options, HSTS — ✅ Done
7. AC7: `.env.production.example` has ALL variables from `.env.example` plus DOMAIN, CERTBOT_EMAIL — ✅ Done (all 80+ variables included)
8. AC8: CORS defaults to `https://production.ratatoskr.trade` — ✅ Done
9. AC9: `deploy.sh` handles: env check, nginx config generation, SSL bootstrap, build, migrations, seed — ✅ Done
10. AC10: `update.sh` handles: git pull, rebuild, migrations — ✅ Done
11. AC11: Frontend uses `VITE_API_BASE_URL` env var — ✅ Already correct (api.ts uses `import.meta.env.VITE_API_BASE_URL || '/api/v1'`); Dockerfile now passes build arg
12. AC12: Certbot auto-renewal runs in background — ✅ Done (entrypoint loop: `certbot renew; sleep 12h`)
13. AC13: All services have `restart: unless-stopped` — ✅ Done
14. AC14: README has deployment section — ✅ Done
15. AC15: No application logic modified — ✅ Done (only Dockerfile build arg + infra files)
16. AC16: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Architecture

```
                    ┌─────────────────────────────────┐
                    │           Internet               │
                    └───────────┬─────────────────────┘
                                │
                    ┌───────────▼─────────────────────┐
                    │    nginx (80/443)                 │
                    │    SSL termination                │
                    │    /api/ → backend:8000           │
                    │    /     → frontend:80            │
                    └──┬───────────────┬──────────────┘
                       │               │
              ┌────────▼─────┐ ┌──────▼──────┐
              │   backend    │ │  frontend   │
              │   :8000      │ │  :80        │
              │   (FastAPI)  │ │  (nginx+SPA)│
              └──────┬───────┘ └─────────────┘
                     │
              ┌──────▼───────┐
              │     db       │
              │  PostgreSQL  │
              │   :5432      │
              └──────────────┘
```

## SSL Bootstrap Flow

The deploy script handles the Let's Encrypt chicken-and-egg problem:

1. Copy `nginx/init.conf` → `nginx/prod.conf` (HTTP-only, serves ACME challenge)
2. Start nginx with HTTP-only config
3. Run `certbot certonly --webroot` to get certificate
4. Generate `nginx/prod.conf` from `prod.conf.template` (full SSL config)
5. Restart nginx with SSL config
6. Mark bootstrap complete (`.certbot_initialized`)
7. Certbot renewal runs every 12h in background

## Deploy Script Steps

1. Load `.env` and validate DOMAIN/CERTBOT_EMAIL
2. Generate nginx config via `envsubst`
3. SSL bootstrap (first time only)
4. `docker compose up -d --build` (all 5 services)
5. Wait for backend health (30 attempts, 2s interval)
6. Run Alembic migrations
7. Seed admin user
8. Print success with URLs

## Assumptions Made
1. **Domain DNS already configured:** The operator must set up an A record pointing to the Droplet IP before running `deploy.sh`.
2. **Fresh Ubuntu droplet:** `server-setup.sh` assumes a clean Ubuntu installation.
3. **Single-instance deployment:** No load balancing or multi-server setup.
4. **Seed script accessible in container:** The backend Dockerfile copies the full `backend/` directory. The seed script at `/app/scripts/` may need a volume mount or alternative approach. Used the async `seed_admin_user()` from `app.auth.seed` instead.

## Ambiguities Encountered
1. **Seed script location in Docker:** The `Dockerfile.backend` copies `backend/` to `/app/backend/`, but `scripts/seed_admin.py` is at the repo root. Used the module-level seed function from `app.auth.seed` instead.

## Dependencies Discovered
None

## Tests Created
None — infrastructure task

## Risks or Concerns
1. **certbot rate limits:** Let's Encrypt has rate limits (5 certs per week per domain). Failed bootstrap attempts count. Use `--staging` flag for testing.
2. **Database password in URL:** The DATABASE_URL contains the password. Ensure `.env` is never committed.
3. **Single point of failure:** No redundancy — Droplet restart means brief downtime (mitigated by `restart: unless-stopped`).

## Deferred Items
None — all deliverables complete

## Recommended Next Task
SSH into the Droplet, run `server-setup.sh`, then `deploy.sh`. Verify the platform is accessible at `https://production.ratatoskr.trade`.
