# ROADMAP

## Phase 1 — Research Platform and Studio Foundation

### Milestone 1 — Studio Bootstrap ✅ COMPLETE
- canonical studio files created
- all agent prompts defined (user-managed)
- all module specs complete (10 spec files)
- all architectural decisions documented (24 decisions)
- status board, roadmap, glossary current

### Milestone 2 — Repo Bootstrap ✅ COMPLETE
- repo skeleton matching architecture spec
- backend Python project config (uv, pyproject.toml)
- frontend Vite + React + TypeScript scaffold
- Docker Compose for app + database
- studio folders populated with canonical files and specs
- environment example files
- docs and test folder structure

### Milestone 3 — Runnable Foundation ✅ COMPLETE
- FastAPI entrypoint with health check
- frontend dev server rendering app shell
- Docker Compose: app + Postgres running
- database connection pool configured
- Alembic migrations initialized
- common module (config, database, errors, base models)

### Milestone 4 — Auth and Database Foundation ✅ COMPLETE
- user model and auth module implementation
- JWT access tokens + refresh tokens
- login/logout/refresh endpoints
- FastAPI auth dependencies (get_current_user, require_admin)
- row-level security pattern in place
- initial Alembic migrations for users and refresh_tokens

### Milestone 5 — Market Data Foundation ✅ COMPLETE
- broker adapter abstraction (base interface)
- Alpaca adapter (REST + WebSocket)
- OANDA adapter (REST + WebSocket)
- market symbol model and watchlist model
- universe filter (equities daily job, forex static config)
- WebSocket manager with reconnection
- bar storage (ohlcv_bars table, write pipeline)
- timeframe aggregation engine
- historical backfill runner with rate limiting
- market data health monitoring
- dividend announcement fetching (corporate actions)

### Milestone 6 — Strategy Engine ✅ COMPLETE
- indicator library (all MVP indicators implemented)
- condition engine (all operators: comparison, crossover, range)
- formula expression parser and evaluator
- strategy CRUD with config-driven model
- strategy validation (indicators, formulas, symbols, sanity checks)
- strategy lifecycle (draft, enabled, paused, disabled)
- strategy versioning
- strategy runner (scheduled evaluation loop)
- safety monitor for orphaned positions
- position overrides (per-position stop loss/take profit)

## Phase 2 — Paper Trading MVP

### Milestone 7 — Signals and Risk ✅ COMPLETE
- signal creation, validation, deduplication, expiry
- signal lifecycle management
- risk engine with all 12 ordered checks
- risk decision persistence
- kill switch (global and per-strategy)
- risk configuration (database-stored, admin-editable)
- drawdown monitoring and daily loss tracking

### Milestone 8 — Paper Trading Engine ✅ COMPLETE
- executor abstraction (simulated + Alpaca paper)
- internal fill simulation (slippage, fees)
- Alpaca paper trading API integration (equities)
- forex account pool manager (allocation, release, contention)
- shadow tracking for contention-blocked signals
- order and fill lifecycle
- cash management

### Milestone 9 — Portfolio Accounting ✅ COMPLETE
- position tracking (open, scale, close)
- mark-to-market cycle
- realized and unrealized PnL calculation
- equity calculation and portfolio snapshots
- peak equity and drawdown tracking
- realized PnL ledger
- dividend payment processing
- stock split position adjustment
- options expiration handling
- performance metrics calculation

## Phase 3 — Dashboard and Operator Layer

### Milestone 10 — Observability ✅ COMPLETE
- structured event log (audit events from all modules)
- event emission service (async, non-blocking)
- system metrics collection
- alert rules, evaluation engine, notification channels
- application logging configuration

### Milestone 11 — Frontend Shell ✅ COMPLETE
- app shell (sidebar nav, alert banner, status bar)
- routing and auth guards
- shared component library (stat cards, data tables, status pills, etc.)
- theme and styling system
- API client with auth interceptor

### Milestone 12 — Frontend Views ✅ COMPLETE
- dashboard home
- strategy list and detail views
- strategy builder UI (condition builder, indicator select, formula input)
- signals view
- paper trading / orders view (including forex pool status)
- portfolio view (positions, PnL, equity curve, dividends)
- risk dashboard (exposure, drawdown, kill switch)
- system telemetry (admin, pipeline, activity feed)
- settings (risk config, accounts, users, alerts)

## Phase 4 — Hardening and Live Preparation

### Milestone 13 — Testing and Validation ✅ COMPLETE
- comprehensive unit test suite
- integration tests for critical paths
- end-to-end API flow tests
- frontend component tests
- Playwright browser tests

### Milestone 14 — Live Trading Preparation ✅ COMPLETE
- hardened execution abstraction
- real OANDA account mapping for forex pool
- live Alpaca API integration
- stronger auditability
- deployment hardening
- pre-live readiness checklist

## Current Phase
All phases complete (1–4)

## Current Milestone
All milestones complete (1–14). MVP is feature-complete and hardened for live preparation.
