# Builder Output — TASK-006

## Task
Market Data: Universe Filter, Watchlist, Backfill, and Broker REST

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created

backend/app/market_data/backfill/rate_limiter.py
backend/app/market_data/options/chain.py
backend/app/market_data/universe/filter.py
backend/app/market_data/universe/watchlist.py
backend/app/market_data/universe/corporate_actions.py
backend/app/market_data/backfill/runner.py

## Files Modified

backend/app/market_data/adapters/alpaca.py — replaced stub with full REST implementation (list_available_symbols, fetch_historical_bars, fetch_latest_bars_batch, fetch_option_chain, fetch_dividends, error handling with 429 retry)
backend/app/market_data/adapters/oanda.py — replaced stub with full REST implementation (list_available_symbols, fetch_historical_bars with mid-price conversion, timeframe mapping)
backend/app/market_data/service.py — implemented get_option_chain (with cache), get_dividend_yield, run_universe_filter, run_backfill, fetch_corporate_actions
backend/app/market_data/router.py — replaced 501 stubs for /backfill/trigger and /watchlist/refresh with working endpoints, added GET /options/chain/{symbol}
backend/app/common/config.py — added universe_filter_forex_pairs setting

## Files Deleted
None

## Acceptance Criteria Status
1. RateLimiter class works with configurable requests/minute and blocks when limit reached — ✅ Done (sliding window approach, acquire() blocks, NoOpRateLimiter for tests)
2. Alpaca adapter authenticates with API key headers — ✅ Done (APCA-API-KEY-ID, APCA-API-SECRET-KEY headers)
3. Alpaca adapter list_available_symbols fetches and normalizes asset data — ✅ Done (GET /v2/assets, filters tradable=true, maps to canonical format)
4. Alpaca adapter fetch_historical_bars fetches bars with pagination, converts to Decimal/UTC — ✅ Done (page_token pagination, Decimal conversion, ISO timestamp parsing)
5. Alpaca adapter fetch_latest_bars_batch handles batching (200 symbols per call) — ✅ Done (batches in groups of 200, GET /v2/stocks/bars)
6. Alpaca adapter fetch_option_chain returns structured chain data with Greeks — ✅ Done (GET /v1beta1/options/snapshots/{symbol}, delta/gamma/theta/vega/iv as Decimal)
7. Alpaca adapter fetch_dividends returns normalized dividend announcements — ✅ Done (GET /v2/corporate_actions/announcements, Decimal amounts)
8. All Alpaca adapter methods pass through the rate limiter — ✅ Done (_request() calls acquire() before every HTTP call)
9. All Alpaca adapter methods handle HTTP errors (429 retry, 4xx, 5xx, timeout) — ✅ Done (429: exponential backoff + retry, 4xx: DomainError, 5xx: MarketDataConnectionError, timeout: retry up to 3 times)
10. OANDA adapter authenticates with Bearer token — ✅ Done (Authorization: Bearer {token})
11. OANDA adapter list_available_symbols fetches and normalizes instrument data — ✅ Done (GET /v3/accounts/{id}/instruments, extracts base/quote from EUR_USD format)
12. OANDA adapter fetch_historical_bars fetches candles with timeframe mapping, converts mid prices to Decimal/UTC — ✅ Done (M1/M5/M15/H1/H4/D mapping, mid prices=(bid+ask)/2)
13. OANDA adapter fetch_option_chain returns None (permanent, not stub) — ✅ Done
14. OANDA adapter fetch_dividends returns empty list (permanent, not stub) — ✅ Done
15. All OANDA adapter methods pass through the rate limiter — ✅ Done (_request() calls acquire())
16. Universe filter runs for equities: fetches symbols, filters by exchange/volume/price, updates watchlist — ✅ Done (run_equities_filter: list symbols → exchange filter → fetch bars batch → volume/price filter → update watchlist)
17. Universe filter runs for forex: applies configured pairs list, updates watchlist — ✅ Done (run_forex_filter: list instruments → filter by UNIVERSE_FILTER_FOREX_PAIRS config → update watchlist)
18. Watchlist soft-deletes removed symbols (sets removed_at, status=inactive) — ✅ Done (_update_watchlist calls deactivate())
19. Watchlist stores filter_metadata_json explaining why each symbol passed — ✅ Done (equities: {"avg_volume": N, "last_price": N}, forex: {"source": "config"})
20. Backfill runner creates BackfillJob records and updates their status — ✅ Done (pending→running→completed/failed)
21. Backfill runner fetches bars from correct adapter based on market — ✅ Done (_get_adapter routes equities→AlpacaAdapter, forex→OandaAdapter)
22. Backfill runner respects rate limits via RateLimiter — ✅ Done (creates per-broker limiter, passes to adapter constructor)
23. Backfill runner handles per-symbol failures without halting entire process — ✅ Done (try/except per symbol, logs error, marks job failed, continues)
24. Backfill runner supports retry for failed jobs (up to max retries) — ✅ Done (needs_backfill checks retry_count < max_retries)
25. Gap backfill function exists for targeted time-range backfill — ✅ Done (backfill_gap(db, symbol, timeframe, gap_start, gap_end))
26. Corporate actions fetcher retrieves and upserts dividend announcements — ✅ Done (fetch_corporate_actions: fetches from Alpaca, upserts via DividendAnnouncementRepository)
27. Option chain cache implements TTL-based caching — ✅ Done (OptionChainCache with monotonic time, get/set/clear)
28. Service.get_option_chain uses cache with fallback to adapter — ✅ Done (check cache → if miss, fetch from AlpacaAdapter → cache → return)
29. Service.get_dividend_yield calculates annualized yield from stored dividends — ✅ Done (sum last 12 months dividends / current price * 100)
30. POST /api/v1/market-data/backfill/trigger works (admin only) — ✅ Done (require_admin, calls service.run_backfill, returns job summary)
31. POST /api/v1/market-data/watchlist/refresh works (admin only) — ✅ Done (require_admin, calls service.run_universe_filter, returns filter results)
32. GET /api/v1/market-data/options/chain/:symbol works (auth required) — ✅ Done (get_current_user, calls service.get_option_chain)
33. All financial values from broker APIs converted to Decimal (never stored as float) — ✅ Done (all Decimal(str(...)) conversions in both adapters)
34. All timestamps from broker APIs converted to timezone-aware UTC — ✅ Done (fromisoformat with +00:00 replacement for Z suffix)
35. No WebSocket connections or streaming logic implemented — ✅ Done (subscribe_bars/unsubscribe_bars/get_connection_health remain NotImplementedError)
36. No bar aggregation logic implemented — ✅ Done
37. No health monitoring implemented — ✅ Done (/health still returns 501)
38. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- Added `universe_filter_forex_pairs` to Settings in common/config.py with default value of 10 major forex pairs. This was referenced in the market_data_module_spec but not present in the existing Settings class.
- Alpaca data API endpoints use `https://data.alpaca.markets` as the base URL (separate from the trading API base URL). This is standard for Alpaca's v2 market data API.
- OANDA candle API uses "mid" prices (M parameter) — the midpoint of bid/ask. This gives a single OHLCV representation from OANDA's bid/ask/mid format.
- For OANDA fetch_historical_bars, incomplete candles are skipped (only complete=true candles are returned). This prevents partial bar data from entering the system.
- The option chain endpoint returns an empty `{"data": null}` when a symbol has no options data (rather than an error), since `fetch_option_chain` can legitimately return None.
- Both adapters create a new httpx.AsyncClient per request rather than maintaining a persistent client. This is simpler and avoids connection lifecycle concerns; a persistent client can be optimized later if needed.

## Ambiguities Encountered
None — task and specs were unambiguous for all deliverables.

## Dependencies Discovered
None — all dependencies were available (httpx already in pyproject.toml).

## Tests Created
None — not required by this task. Verified functionality through import verification and end-to-end API testing against a running Postgres instance. Broker REST calls verified to properly error with 401 when API keys are not configured (expected behavior).

## Risks or Concerns
- The Alpaca and OANDA API response formats are based on current documentation. If the broker APIs change their response structure, the adapters will need updating.
- Rate limiter uses an in-memory sliding window that resets on process restart. This is fine for a single-process deployment but would need a shared backend (Redis) for multi-process scenarios.

## Deferred Items
None — all deliverables complete.

## Recommended Next Task
TASK-007 — Market data module: WebSocket manager, bar storage pipeline, aggregation engine, and health monitoring. The REST adapters, universe filter, and backfill runner are now in place.
