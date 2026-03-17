# PROJECT_STATE

## Project Identity

Project Name: Ratatoskr Trading Platform
Project Type: Professional web-based trading platform for quantitative and algorithmic traders
Primary Objective: Build a research-first, paper-trading-first platform with architecture that can later support live trading

## Mission

Design and build a professional quant/algo trading platform that supports:
- market data ingestion (Alpaca for equities/options, OANDA for forex)
- historical data normalization and storage
- config-driven strategy building (no code required for most strategies)
- backtesting (future phase)
- signal generation with deduplication and expiry
- paper trading with honest simulation (broker constraints enforced)
- risk management with 12 ordered checks
- portfolio and PnL tracking with dividend and corporate action support
- operator dashboards with real-time telemetry
- observability, alerting, and auditability

## Target Users

- individual quantitative traders
- systematic strategy developers
- small algorithmic trading teams
- operators supervising automated strategies
- future: non-technical users building strategies through UI

## Non-Goals

- social trading / copy trading
- gamified retail investing UX
- meme trading product design
- beginner-first educational flows
- live broker or exchange execution in v1

## Current Phase

All phases complete (Phases 1–4). MVP feature-complete and hardened for live preparation.

## Current Milestone

All milestones complete (1–14). All phases complete (1–4). All backend modules implemented. All frontend views implemented. Platform feature-complete and hardened for live preparation. 585 tests across all layers: 302 backend unit, 60 integration, 68 E2E API, 112 frontend unit, 43 Playwright browser. Rate limiting, request size limits, JSON logging, broker connectivity verified, audit trail verified, reconciliation endpoint, automated readiness check script.

## Approved Product Direction

The product must be:
- dark theme, calm, modern SaaS-like
- desktop-first with graceful tablet degradation
- high-signal, data-dense but readable
- operator-friendly with real-time telemetry
- dual-audience: trader views + admin/developer telemetry views

The product is not a retail brokerage clone.

## Approved Architecture Direction

- modular monolith for MVP
- explicit bounded modules with service-layer interfaces
- spec-first and contract-first development
- config-driven strategies as the primary path (class-based as escape hatch)
- deterministic workflows
- reproducible research outputs
- paper trading before live trading
- honest paper simulation (enforces same constraints as live)
- strong observability and auditability
- no silent failures in trading logic

## Approved Technical Stack

Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic
Frontend: React, Vite, TypeScript, React Router, TanStack Query, Zustand, Tailwind CSS, shadcn/ui, Recharts
Database: PostgreSQL
Python Tooling: uv
Testing: pytest (backend), vitest (frontend), Playwright (e2e)
Lint/Format: Ruff (Python), ESLint + Prettier (frontend)
Infra: Docker Compose, .env-based config

## Approved Core Modules

- auth (users, roles, JWT, row-level security)
- market_data (broker abstraction, universe filter, WebSocket streaming, bars, backfill, options, health)
- strategies (config-driven builder, indicator library, condition engine, formula parser, runner, safety monitor)
- signals (validation, deduplication, expiry, lifecycle, risk handoff)
- risk (12 ordered checks, kill switch, drawdown, exposure, daily loss)
- paper_trading (executor abstraction, forex account pool, shadow tracking, fill simulation)
- portfolio (positions, PnL, mark-to-market, snapshots, dividends, splits, metrics)
- observability (structured events, metrics, alerts, notifications, telemetry)
- common (config, database, errors, shared utilities)
- backtesting (bar replay engine, fill simulation, position sizing, performance metrics, equity curve)
- frontend dashboard (10 views, strategy builder UI, component library)
- shared schemas and contracts

## Broker Integrations

- Alpaca: equities, options (paper trading via broker API, market data via WebSocket + REST)
- OANDA: forex (paper trading via internal simulation with account pool, market data via WebSocket + REST)

## Key Design Decisions Made During Spec Phase

- WebSocket streaming for real-time market data (not REST polling)
- Store 1m bars, aggregate higher timeframes on write
- On-demand option chain data with caching (not streamed)
- Config-driven strategies as primary path (indicator catalog + condition engine + formula parser)
- Class-based custom strategies as deferred escape hatch (sandboxed code editor, future)
- Forex account pool model to handle US FIFO netting constraints
- Shadow tracking for contention-blocked forex signals (fair strategy comparison)
- Broker paper trading for equities (Alpaca), internal simulation for forex (with pool constraints)
- Safety monitor for orphaned positions (strategy paused/disabled/errored)
- Position overrides for per-position stop loss/take profit adjustments
- Manual close always flows through pipeline (logged and audited)
- Kill switch blocks entries but always allows exits
- Emoji-prefixed event summaries for at-a-glance activity feed scanning

## Current Constraints

- no live trading execution
- no broker integration for live orders yet
- no microservices unless explicitly approved later
- all work must follow canonical studio files
- all coding work must be done through scoped task packets
- no off-scope architectural improvisation

## Completed Spec Files

All module specs are complete and ready for implementation:

1. market_data_module_spec.md
2. strategy_module_spec.md
3. signals_module_spec.md
4. risk_engine_module_spec.md
5. paper_trading_module_spec.md
6. portfolio_module_spec.md
7. observability_module_spec.md
8. auth_module_spec.md
9. cross_cutting_specs.md
10. frontend_specs.md

## Open Questions

None at this time. All architectural and engineering decisions for MVP have been made.
Future decisions (sandboxed code editor, per-user forex pools, advanced options handling)
are documented as deferred enhancements in the relevant specs.

## Last Updated

2026-03-16 (TASK-041d complete — fixed strategy save payload wrapper and exit validation. Frontend now wraps config under config key for update path. Validator and runner check risk_management.stop_loss/take_profit as fallback exit mechanisms.)
