# Ratatoskr Trading Platform

Professional web-based trading platform for quantitative and algorithmic traders.

## Overview

Ratatoskr is a research-first, paper-trading-first platform supporting:
- Multi-broker market data (Alpaca for equities/options, OANDA for forex)
- Config-driven strategy building (no code required)
- Signal generation with risk management
- Paper trading with honest simulation
- Portfolio tracking with full PnL accounting
- Real-time operator dashboards

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Infrastructure:** Docker Compose

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

## Project Structure

```
backend/         Python FastAPI application
frontend/        React TypeScript SPA
shared/          Cross-boundary schemas and contracts
infra/           Docker, scripts, environment config
tests/           Unit, integration, and e2e tests
docs/            Documentation
studio/          AI development studio (specs, tasks, state files)
```

## Operations Runbook

### Connecting Alpaca (Equities)

1. Create a free Alpaca paper trading account at https://alpaca.markets
2. Generate API keys in the dashboard (Paper Trading section)
3. Add to `.env`:
   ```
   ALPACA_API_KEY=your-key
   ALPACA_API_SECRET=your-secret
   ALPACA_BASE_URL=https://paper-api.alpaca.markets
   ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/iex
   ```
   Use `v2/iex` for free accounts, `v2/sip` for paid (full market data).
4. Restart the backend
5. Check health: `curl http://localhost:8000/api/v1/health`
6. Check watchlist: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/market-data/watchlist`

### Connecting OANDA (Forex)

1. Create an OANDA fxPractice account at https://www.oanda.com
2. Generate an API access token in Account Settings → API Management
3. Note your practice account ID (format: `101-001-XXXXX-001`)
4. Add to `.env`:
   ```
   OANDA_ACCESS_TOKEN=your-token
   OANDA_ACCOUNT_ID=your-main-account-id
   OANDA_BASE_URL=https://api-fxpractice.oanda.com
   OANDA_STREAM_URL=https://stream-fxpractice.oanda.com
   ```
5. Restart the backend
6. Forex data should stream immediately (forex runs 24/5: Sunday 10 PM – Friday 10 PM UTC)

### Forex Account Pool

The system maintains a pool of OANDA sub-accounts to handle FIFO netting constraints. Each account can hold one position per pair. When all accounts for a pair are full, new signals are rejected and tracked as shadow positions.

**To map real OANDA sub-accounts to pool slots:**

1. Create additional sub-accounts in OANDA's interface (up to 4)
2. Add to `.env`:
   ```
   OANDA_POOL_ACCOUNT_1=101-001-XXXXX-001
   OANDA_POOL_ACCOUNT_2=101-001-XXXXX-002
   OANDA_POOL_ACCOUNT_3=101-001-XXXXX-003
   OANDA_POOL_ACCOUNT_4=101-001-XXXXX-004
   ```
3. Leave slots empty to use virtual/simulated accounts (mixed mode supported)
4. Check pool status: `GET /api/v1/paper-trading/forex-pool/status`

### Troubleshooting

- **No bars streaming:** Check if market is open (equities: 9:30 AM – 4:00 PM ET; forex: Sunday 10 PM – Friday 10 PM UTC). Outside hours, no bars are expected.
- **WebSocket disconnects:** Check logs for reconnection attempts. The system auto-reconnects with exponential backoff.
- **Universe filter empty:** Lower `UNIVERSE_FILTER_EQUITIES_MIN_VOLUME` or check Alpaca API connectivity.
- **"unconfigured" broker status in health:** Broker API keys are not set in `.env`. App runs without them — broker features are disabled.
- **Rate limiting (429 errors):** The system handles rate limits automatically with exponential backoff. If persistent, reduce concurrent requests.
- **No forex data:** Verify OANDA token hasn't expired. Practice tokens may need periodic regeneration.
- **Pool full:** All accounts for a pair are occupied. Check `GET /api/v1/paper-trading/forex-pool/status`. Shadow tracking records what would have happened.
- **Orders rejected:** Check OANDA account has sufficient margin. Practice accounts start with virtual funds.

## Pre-Live Checklist

Before enabling strategies with real broker execution:

### Automated Check

```bash
uv run python scripts/readiness_check.py
```

### Manual Review

- [ ] Review risk limits in Settings -> Risk Configuration
- [ ] Set max drawdown and daily loss limits appropriate for your account
- [ ] Review position size limits per symbol and per strategy
- [ ] Start with one simple strategy and monitor before adding more
- [ ] Verify the kill switch works (activate -> verify trading stops -> deactivate)
- [ ] Check audit trail captures all trade events (`GET /signals/:id/trace`)
- [ ] Run reconciliation check (`GET /paper-trading/reconciliation`)
- [ ] Review all enabled strategies and their conditions

### Security

- [ ] Change admin password from default
- [ ] Generate a strong JWT secret: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `CORS_ALLOWED_ORIGINS` to your frontend domain
- [ ] Ensure `.env` is NOT committed to git

## Production Deployment (DigitalOcean)

### Prerequisites
- DigitalOcean Droplet (2GB+ RAM, Ubuntu 22.04+)
- Domain with A record pointing to the Droplet IP

### Initial Setup

1. SSH into the Droplet:
   ```bash
   ssh root@your-droplet-ip
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
   nano .env  # Fill in ALL values — especially passwords, JWT secret, broker keys
   ```

5. Deploy:
   ```bash
   ./scripts/deploy.sh
   ```

6. Visit `https://your-domain`

### Updating

```bash
su - ratatoskr
cd /opt/ratatoskr
./scripts/update.sh
```

### Monitoring

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Check health
curl https://your-domain/api/v1/health

# Run readiness check
docker compose -f docker-compose.prod.yml exec backend \
    python -c "exec(open('/app/scripts/readiness_check.py').read())"
```

### Backup Database

```bash
docker compose -f docker-compose.prod.yml exec db \
    pg_dump -U ratatoskr ratatoskr_prod > backup_$(date +%Y%m%d).sql
```

## Documentation

- Engineering specs: `studio/SPECS/`
- Project state: `studio/STUDIO/`
- Architecture decisions: `studio/STUDIO/DECISIONS.md`
