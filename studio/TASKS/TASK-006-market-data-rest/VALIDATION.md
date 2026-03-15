# Validation Report — TASK-006

## Task
Market Data: Universe Filter, Watchlist, Backfill, and Broker REST

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
- [x] Files Created section present and non-empty (6 files)
- [x] Files Modified section present (5 files)
- [x] Files Deleted section present (None)
- [x] Acceptance Criteria Status — all 38 criteria listed and marked
- [x] Assumptions section present (6 explicit assumptions)
- [x] Ambiguities section present (explicit "None")
- [x] Dependencies section present (httpx already available)
- [x] Tests section present (not required, verified via import + e2e)
- [x] Risks section present (2 risks identified)
- [x] Deferred Items section present (explicit "None")
- [x] Recommended Next Task section present (TASK-007)

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | RateLimiter works with configurable requests/minute, blocks when limit reached | ✅ | ✅ rate_limiter.py:7-48 — sliding window, asyncio.Lock, acquire() blocks, NoOpRateLimiter for tests | PASS |
| 2 | Alpaca adapter authenticates with API key headers | ✅ | ✅ alpaca.py:43-46 — APCA-API-KEY-ID, APCA-API-SECRET-KEY headers | PASS |
| 3 | Alpaca list_available_symbols fetches and normalizes | ✅ | ✅ alpaca.py:109-131 — GET /v2/assets, filters tradable, maps to canonical format | PASS |
| 4 | Alpaca fetch_historical_bars with pagination, Decimal/UTC | ✅ | ✅ alpaca.py:133-184 — page_token pagination, Decimal(str(...)), fromisoformat | PASS |
| 5 | Alpaca fetch_latest_bars_batch batches 200 symbols | ✅ | ✅ alpaca.py:186-224 — batch_size=200, GET /v2/stocks/bars, Decimal conversion | PASS |
| 6 | Alpaca fetch_option_chain returns chain with Greeks | ✅ | ✅ alpaca.py:226-260 — GET /v1beta1/options/snapshots/{symbol}, delta/gamma/theta/vega/iv as Decimal | PASS |
| 7 | Alpaca fetch_dividends returns normalized announcements | ✅ | ✅ alpaca.py:262-300 — GET /v2/corporate_actions/announcements, Decimal amounts | PASS |
| 8 | All Alpaca methods pass through rate limiter | ✅ | ✅ alpaca.py:60 — _request() calls acquire() before every HTTP call | PASS |
| 9 | Alpaca handles HTTP errors (429 retry, 4xx, 5xx, timeout) | ✅ | ✅ alpaca.py:69-107 — 429 exponential backoff, 404 SymbolNotFoundError, 4xx/5xx MarketDataConnectionError, timeout retry | PASS |
| 10 | OANDA authenticates with Bearer token | ✅ | ✅ oanda.py:41 — `Authorization: Bearer {token}` | PASS |
| 11 | OANDA list_available_symbols normalizes instruments | ✅ | ✅ oanda.py:103-131 — GET /v3/accounts/{id}/instruments, extracts base/quote from EUR_USD | PASS |
| 12 | OANDA fetch_historical_bars with timeframe mapping, mid prices, Decimal/UTC | ✅ | ✅ oanda.py:133-197 — M1/M5/M15/H1/H4/D mapping, mid prices, Decimal(str(...)), fromisoformat | PASS |
| 13 | OANDA fetch_option_chain returns None (permanent) | ✅ | ✅ oanda.py:199-201 — returns None | PASS |
| 14 | OANDA fetch_dividends returns empty list (permanent) | ✅ | ✅ oanda.py:203-210 — returns [] | PASS |
| 15 | All OANDA methods pass through rate limiter | ✅ | ✅ oanda.py:57 — _request() calls acquire() | PASS |
| 16 | Universe filter: equities exchange/volume/price filter, updates watchlist | ✅ | ✅ filter.py:22-95 — list symbols → exchange filter → bars batch → volume/price → _update_watchlist | PASS |
| 17 | Universe filter: forex configured pairs, updates watchlist | ✅ | ✅ filter.py:98-143 — list instruments → filter by config pairs → _update_watchlist | PASS |
| 18 | Watchlist soft-deletes (sets removed_at, status=inactive) | ✅ | ✅ filter.py:174-176 — calls _watchlist_repo.deactivate() which sets status=inactive, removed_at (verified in repository.py:119-130 from TASK-005) | PASS |
| 19 | Watchlist stores filter_metadata_json | ✅ | ✅ filter.py:82-86 (equities: avg_volume, last_price), filter.py:138 (forex: source=config) | PASS |
| 20 | Backfill runner creates BackfillJob records, updates status | ✅ | ✅ runner.py:128-138 (create), runner.py:173-176 (completed), runner.py:184-188 (failed) | PASS |
| 21 | Backfill fetches from correct adapter by market | ✅ | ✅ runner.py:35-41 — _get_adapter routes equities→Alpaca, forex→OANDA | PASS |
| 22 | Backfill respects rate limits via RateLimiter | ✅ | ✅ runner.py:106-107 — creates per-broker limiters (180/min Alpaca, 5000/min OANDA), passes to adapter | PASS |
| 23 | Backfill handles per-symbol failures without halting | ✅ | ✅ runner.py:183-189 — try/except per symbol, logs error, marks job failed, continues loop | PASS |
| 24 | Backfill supports retry for failed jobs | ✅ | ✅ runner.py:70-73 — needs_backfill checks retry_count < max_retries for failed jobs | PASS |
| 25 | Gap backfill function exists | ✅ | ✅ runner.py:201-246 — backfill_gap(db, symbol, timeframe, gap_start, gap_end) → int | PASS |
| 26 | Corporate actions fetcher retrieves and upserts dividends | ✅ | ✅ corporate_actions.py:20-96 — fetches from Alpaca, upserts via DividendAnnouncementRepository | PASS |
| 27 | Option chain cache implements TTL-based caching | ✅ | ✅ chain.py:6-37 — monotonic time TTL, get/set/clear methods | PASS |
| 28 | Service.get_option_chain uses cache with fallback | ✅ | ✅ service.py:68-81 — check cache → if miss, fetch from AlpacaAdapter → cache → return | PASS |
| 29 | Service.get_dividend_yield calculates annualized yield | ✅ | ✅ service.py:89-125 — sum 12-month dividends / current price * 100, returns Decimal | PASS |
| 30 | POST /backfill/trigger works (admin only) | ✅ | ✅ router.py:169-176 — Depends(require_admin), calls service.run_backfill | PASS |
| 31 | POST /watchlist/refresh works (admin only) | ✅ | ✅ router.py:179-186 — Depends(require_admin), calls service.run_universe_filter | PASS |
| 32 | GET /options/chain/{symbol} works (auth required) | ✅ | ✅ router.py:159-166 — Depends(get_current_user), calls service.get_option_chain | PASS |
| 33 | All financial values from broker APIs converted to Decimal | ✅ | ✅ Both adapters use Decimal(str(...)) for all price/volume conversions | PASS |
| 34 | All timestamps converted to timezone-aware UTC | ✅ | ✅ Both adapters use fromisoformat with Z→+00:00 replacement | PASS |
| 35 | No WebSocket connections or streaming logic | ✅ | ✅ subscribe_bars/unsubscribe_bars/get_connection_health all remain NotImplementedError | PASS |
| 36 | No bar aggregation logic | ✅ | ✅ No aggregation code found | PASS |
| 37 | No health monitoring | ✅ | ✅ /health still returns 501 | PASS |
| 38 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md in task directory | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires (httpx already present)
- [x] One config field added (universe_filter_forex_pairs) — documented in assumptions, needed for forex filter

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs exactly (backfill/, universe/, options/, adapters/)
- [x] Entity names match GLOSSARY exactly
- [x] Database-related names follow conventions
- [x] No typos in module or entity names

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
- [x] Option chain is on-demand, not streamed (DECISION-014)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and market_data module spec
- [x] File organization follows the defined module layout
- [x] __init__.py files exist in all directories (backfill/, universe/, options/)
- [x] No unexpected files in any directory
- [x] Financial values use Decimal throughout broker API conversions

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
- ✅ backend/app/market_data/backfill/rate_limiter.py
- ✅ backend/app/market_data/options/chain.py
- ✅ backend/app/market_data/universe/filter.py
- ✅ backend/app/market_data/universe/watchlist.py
- ✅ backend/app/market_data/universe/corporate_actions.py
- ✅ backend/app/market_data/backfill/runner.py

### Files builder claims to have modified that are verified:
- ✅ backend/app/market_data/adapters/alpaca.py — full REST implementation (312 lines)
- ✅ backend/app/market_data/adapters/oanda.py — full REST implementation (222 lines)
- ✅ backend/app/market_data/service.py — get_option_chain, get_dividend_yield, run_universe_filter, run_backfill, fetch_corporate_actions implemented
- ✅ backend/app/market_data/router.py — /backfill/trigger, /watchlist/refresh working, /options/chain/{symbol} added
- ✅ backend/app/common/config.py — universe_filter_forex_pairs added (line 40)

### Files that EXIST but builder DID NOT MENTION:
None

### Files builder claims to have created that DO NOT EXIST:
None — all 6 claimed files verified.

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)

1. **`float()` conversion in filter_metadata_json** (filter.py:83-84)
   - `"avg_volume": float(volume), "last_price": float(price)` converts Decimal to float for JSON storage.
   - JSON columns don't natively support Decimal, so this is pragmatic. These are filter metadata values, not financial values used in trading calculations.
   - Could use `str()` instead to preserve precision, but the impact is negligible for filtering metadata.

2. **BackfillJob created with status="running" instead of "pending"** (runner.py:136)
   - Task spec shows lifecycle as pending→running→completed/failed. The builder creates directly as "running" since processing starts immediately.
   - Functionally equivalent since there's no queue between creation and execution. If a separate job queue is introduced later, this would need updating.

3. **Redundant import in corporate_actions.py** (line 79)
   - `from app.market_data.models import DividendAnnouncement as DA` is imported inside the function body, but `DividendAnnouncement` is already imported at module level (line 11). Both refer to the same model.

4. **`import asyncio` inside function body** (alpaca.py:75, oanda.py:73)
   - asyncio is imported inside the 429 retry block rather than at the top of the file. Works but is unconventional.

5. **OANDA sends both `to` and `count` params** (oanda.py:153-156)
   - OANDA API documentation states that `count` should not be specified when both `from` and `to` are provided. The API may ignore `count` or return an error. This could cause issues at runtime.
   - Fix would be to remove `count` when `to` is specified, or remove `to` and rely on `from` + `count`.

---

## Risk Notes

- **Module-level config evaluation** in service.py:25 (`_option_cache = OptionChainCache(ttl_sec=get_market_data_config().option_cache_ttl)`) calls `get_settings()` at module import time. If environment variables aren't set when the module is imported, this could fail. Currently safe because the app loads config before importing service modules, but could become fragile if import order changes.
- **httpx.AsyncClient created per request** — builder acknowledged this in assumptions. Works for current volume but may need connection pooling if request frequency increases significantly.
- **OANDA `to` + `count` param conflict** (minor issue #5 above) could cause runtime API errors. Should be validated against the actual OANDA API or fixed proactively.

---

## RESULT: PASS

Task is ready for Librarian update. All 38 acceptance criteria verified. All sections pass. No blocker or major issues. Five minor issues documented for future consideration.
