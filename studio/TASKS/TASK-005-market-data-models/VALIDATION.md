# Validation Report — TASK-005

## Task
Market Data: Models, Schemas, and Broker Abstraction

## Validation History
- **v1 (2026-03-13):** FAIL — `Mapped[float]` type hints on 7 financial fields in models.py violated "ALL financial values: Decimal (NEVER float)" convention
- **v2 (2026-03-13):** Re-validation after fix — all 7 fields changed to `Mapped[Decimal]`, `from decimal import Decimal` added

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present and non-empty
- [x] Files Modified section present
- [x] Files Deleted section present
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (4 explicit assumptions documented)
- [x] Ambiguities section present (explicit "None")
- [x] Dependencies section present (explicit "None")
- [x] Tests section present (explains not required, verified via e2e)
- [x] Risks section present (explicit "None")
- [x] Deferred Items section present (explicit "None")
- [x] Recommended Next Task section present (TASK-006)

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | MarketSymbol model exists with all fields, unique constraint on (symbol, market, broker) | ✅ | ✅ models.py:23-42 — all fields present, UniqueConstraint("symbol", "market", "broker", name="uq_market_symbols_symbol_market_broker") | PASS |
| 2 | WatchlistEntry model exists with all fields, proper indexes | ✅ | ✅ models.py:45-63 — all fields, composite index + status index | PASS |
| 3 | OHLCVBar model exists with all Numeric fields (not Float), unique constraint on (symbol, timeframe, ts) | ✅ | ✅ models.py:66-86 — SQLAlchemy column type `Numeric`, Python type hints `Mapped[Decimal]` (fixed in v2), UniqueConstraint present | PASS |
| 4 | BackfillJob model exists with all fields and status tracking | ✅ | ✅ models.py:89-109 — all fields present, status defaults to "pending" | PASS |
| 5 | DividendAnnouncement model exists with all fields, unique on corporate_action_id | ✅ | ✅ models.py:112-135 — unique=True on corporate_action_id, all fields present | PASS |
| 6 | All financial fields use SQLAlchemy Numeric type | ✅ | ✅ Migration: sa.Numeric() for open, high, low, close, volume (ohlcv_bars), cash_amount, stock_rate (dividend_announcements). Models: `Mapped[Decimal]` + `Numeric` column type. | PASS |
| 7 | Alembic migration creates all five tables and applies cleanly | ✅ | ✅ Migration 7a15366e61ae — creates all 5 tables with correct columns, indexes, constraints. Proper downgrade included. | PASS |
| 8 | BrokerAdapter abstract base class defines all methods from the spec | ✅ | ✅ adapters/base.py — 9 abstract methods: broker_name, supported_markets, list_available_symbols, fetch_historical_bars, subscribe_bars, unsubscribe_bars, get_connection_health, fetch_option_chain, fetch_dividends | PASS |
| 9 | Alpaca and OANDA adapter stubs exist, inherit from BrokerAdapter, raise NotImplementedError | ✅ | ✅ alpaca.py: all methods raise NotImplementedError with task references. oanda.py: same pattern, fetch_option_chain returns None (OANDA doesn't support options — reasonable). | PASS |
| 10 | All Pydantic response schemas exist with camelCase aliases | ✅ | ✅ schemas.py — MarketSymbolResponse, WatchlistEntryResponse, OHLCVBarResponse, BackfillJobResponse, DividendAnnouncementResponse, MarketDataHealthResponse all present with Field(alias=...) | PASS |
| 11 | BarQueryParams validates symbol (required), timeframe (required), limit (default 200, max 10000) | ✅ | ✅ schemas.py:122-129 — symbol: str, timeframe: str, limit: int = Field(default=200, ge=1, le=10000) | PASS |
| 12 | MarketDataConfig extracts all market-data settings from global Settings | ✅ | ✅ config.py — 28 settings across broker creds, universe filter, WebSocket, bar storage, backfill, options, health, corporate actions | PASS |
| 13 | All five repository classes exist with complete method signatures | ✅ | ✅ repository.py — MarketSymbolRepository (6 methods), WatchlistRepository (5 methods), OHLCVBarRepository (4 methods), BackfillJobRepository (5 methods), DividendAnnouncementRepository (4 methods) | PASS |
| 14 | OHLCVBarRepository.upsert_bars uses INSERT ON CONFLICT for bulk upsert | ✅ | ✅ repository.py:196-233 — pg_insert().on_conflict_do_update(constraint="uq_ohlcv_bars_symbol_timeframe_ts") | PASS |
| 15 | MarketDataService has all inter-module interface methods defined | ✅ | ✅ service.py — get_bars, get_latest_close, is_symbol_on_watchlist, get_watchlist, get_health, get_option_chain, get_upcoming_dividends, get_dividend_yield, get_next_ex_date | PASS |
| 16 | Service methods backed by DB reads are implemented | ✅ | ✅ get_bars, get_latest_close, is_symbol_on_watchlist, get_watchlist, get_upcoming_dividends, get_next_ex_date all delegate to repositories | PASS |
| 17 | Service methods requiring broker calls raise NotImplementedError with task reference | ✅ | ✅ get_health → TASK-007, get_option_chain → TASK-006, get_dividend_yield → TASK-006 | PASS |
| 18 | Market data router endpoints exist with correct auth dependencies | ✅ | ✅ router.py — all GET endpoints use Depends(get_current_user), POST endpoints use Depends(require_admin) | PASS |
| 19 | DB-backed endpoints return data in standard envelope format | ✅ | ✅ All DB-backed endpoints return {"data": [...]} with pagination where applicable | PASS |
| 20 | Unimplemented endpoints return 501 | ✅ | ✅ /health (501), /backfill/trigger (501), /watchlist/refresh (501) — all return error envelope | PASS |
| 21 | Market data error classes exist and are registered in common error mapping | ✅ | ✅ errors.py — 4 error classes. common/errors.py — MARKET_DATA_SYMBOL_NOT_FOUND→404, MARKET_DATA_STALE→503, MARKET_DATA_BACKFILL_FAILED→500, MARKET_DATA_CONNECTION_ERROR→503 | PASS |
| 22 | Alembic env.py imports market_data models | ✅ | ✅ migrations/env.py:15 — `import app.market_data.models  # noqa: F401` | PASS |
| 23 | No WebSocket, broker API, or backfill execution logic implemented | ✅ | ✅ No HTTP calls, no WebSocket connections, no execution logic found | PASS |
| 24 | No models or logic for other modules created | ✅ | ✅ All files within backend/app/market_data/ | PASS |
| 25 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md in task directory | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs exactly
- [x] Entity names match GLOSSARY exactly (MarketSymbol, WatchlistEntry, OHLCVBar, BackfillJob, DividendAnnouncement, BrokerAdapter)
- [x] Database-related names follow conventions (_id, _at, _json suffixes)
- [x] No typos in module or entity names
- [x] Error class naming: Builder used `MarketDataConnectionError` instead of task spec's `ConnectionError` — this is better since it avoids shadowing Python's built-in `ConnectionError`

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] Python tooling uses uv (DECISION-010)
- [x] API is REST-first (DECISION-011)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and market_data module spec
- [x] File organization follows the defined module layout (models, schemas, errors, config, repository, service, router, adapters/)
- [x] __init__.py files exist (market_data/__init__.py, adapters/__init__.py)
- [x] Financial value type convention satisfied — all 7 financial fields use `Mapped[Decimal]` (fixed in v2)

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
- ✅ backend/app/market_data/models.py
- ✅ backend/app/market_data/schemas.py
- ✅ backend/app/market_data/errors.py
- ✅ backend/app/market_data/config.py
- ✅ backend/app/market_data/repository.py
- ✅ backend/app/market_data/service.py
- ✅ backend/app/market_data/adapters/base.py
- ✅ backend/app/market_data/adapters/alpaca.py
- ✅ backend/app/market_data/adapters/oanda.py
- ✅ backend/migrations/versions/7a15366e61ae_create_market_data_tables.py

### Files builder claims to have modified that are verified:
- ✅ backend/app/market_data/router.py — real endpoints replacing stub
- ✅ backend/app/common/errors.py — MARKET_DATA_STALE→503, MARKET_DATA_CONNECTION_ERROR→503
- ✅ backend/migrations/env.py — `import app.market_data.models` added

### Files that EXIST but builder DID NOT MENTION:
None — all files in the directory are either pre-existing (from TASK-001 scaffold: __init__.py, subdirectories) or builder-created.

### Files builder claims to have created that DO NOT EXIST:
None — all 10 claimed files verified.

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None (v1 major issue resolved — `Mapped[float]` → `Mapped[Decimal]` on all 7 financial fields)

### Minor (note for future, does not block)

1. **OHLCVBar inherits `updated_at` from BaseModel despite task spec saying "NO updated_at"**
   - Builder acknowledged in assumptions: removing it would require not inheriting from BaseModel, which contradicts another requirement ("All models inherit from BaseModel").
   - Acceptable trade-off. The column exists but has no `onupdate` trigger specific to bars.
   - If this becomes a performance concern on the largest table, it can be addressed by introducing a `LeanBaseModel` without `updated_at`.

2. **Error status code corrections from pre-existing values**
   - Builder changed MARKET_DATA_STALE from 422→503 and MARKET_DATA_CONNECTION_ERROR from 500→503 in common/errors.py.
   - These changes align with the task spec (503 is semantically correct for stale/unavailable data).
   - Noted as informational — the pre-existing values from TASK-002 scaffold were placeholders.

---

## Risk Notes

- The OHLCVBar `updated_at` column adds marginal storage overhead to what will be the largest table. Monitor if this becomes a concern at scale.
- No tests were created for this task. The builder verified via e2e against a running Postgres instance. Future tasks (TASK-006/007) building on this layer should include tests that exercise these models and repositories.

---

## RESULT: PASS

Task is ready for Librarian update. All 25 acceptance criteria verified. All sections pass. No blocker or major issues remain. The v1 `Mapped[float]` convention violation has been corrected to `Mapped[Decimal]`.
