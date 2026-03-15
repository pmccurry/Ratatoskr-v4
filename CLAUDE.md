# Ratatoskr Trading Platform

## Identity
- Project: Ratatoskr Trading Platform
- Type: Professional quant/algo trading platform
- Architecture: Modular monolith (MVP)
- Phase: Research platform and studio bootstrap

## Tech Stack (Locked)
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic
- Frontend: React, Vite, TypeScript, React Router, TanStack Query, Zustand, Tailwind CSS, shadcn/ui, Recharts
- Database: PostgreSQL
- Python tooling: uv
- Testing: pytest, vitest, Playwright
- Infra: Docker Compose

## Canonical State — Read Before Any Work
@studio/STUDIO/PROJECT_STATE.md
@studio/STUDIO/DECISIONS.md
@studio/STUDIO/GLOSSARY.md
@studio/STUDIO/STATUS_BOARD.yaml
@studio/STUDIO/ROADMAP.md

## Universal Rules — NEVER Violate These
- NEVER implement live trading logic or live broker execution
- NEVER add modules outside the approved module list
- NEVER rename approved domain entities or modules
- NEVER redesign architecture without an approved decision in DECISIONS.md
- NEVER add Redis, microservices, or event bus without explicit approval
- NEVER create files outside the approved repo structure
- NEVER make changes outside the current task scope

## Data Conventions
- ALL timestamps: UTC, timezone-aware, ISO-8601
- ALL entity IDs: UUID
- ALL financial values: Decimal (NEVER float)
- ALL Python naming: snake_case
- ALL JSON/TypeScript naming: camelCase
- ALL database columns: snake_case with _id, _at, _json suffixes

## Module Architecture
- Modules communicate through service-layer calls ONLY
- No direct cross-module repository access
- No importing models from another module's internals
- Pattern: router → service → repository → database

## Approved Modules
auth, market_data, strategies, signals, risk, paper_trading, portfolio, observability, common

## Task System
- All work flows through task packets in /studio/TASKS/
- Each task has: TASK.md, BUILDER_OUTPUT.md, VALIDATION.md, LIBRARIAN_REPORT.md
- A task is NOT complete until Validator PASS and Librarian update
- Check STATUS_BOARD.yaml before starting any task — respect dependencies
