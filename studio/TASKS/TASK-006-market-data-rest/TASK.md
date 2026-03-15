# TASK-006 — Market Data: Universe Filter, Watchlist, Backfill, and Broker REST

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the broker REST API integrations, universe filter, watchlist
management, historical backfill runner, and corporate actions fetching
for the market data module.

After this task:
- The Alpaca adapter can list symbols, fetch historical bars, and fetch
  corporate actions (dividends, splits) via REST API
- The OANDA adapter can list instruments and fetch historical candles via REST API
- The universe filter runs, narrows equities to a tradable watchlist,
  and persists the result
- The backfill runner fetches historical bars with rate limiting and
  populates the ohlcv_bars table
- Corporate actions (dividends, splits) are fetched from Alpaca
- Option chain snapshots can be fetched from Alpaca
- The 501 endpoints from TASK-005 that depend on REST calls now work

This task implements BROKER REST CALLS and BATCH PROCESSING only.
No WebSocket streaming, no real-time bar ingestion, no aggregation engine,
no health monitoring. Those come in TASK-007.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/market_data_module_spec.md — PRIMARY SPEC, sections 1-2 (broker abstraction, universe filter), section 5 (backfill), section 6 (options)
5. /studio/SPECS/cross_cutting_specs.md — error handling, conventions
6. Review TASK-005 BUILDER_OUTPUT.md to understand what already exists

## Constraints

- Do NOT implement WebSocket streaming or connections
- Do NOT implement the real-time bar ingestion pipeline
- Do NOT implement the bar aggregation engine
- Do NOT implement the health monitoring system
- Do NOT implement the WebSocket manager, async queue, or batch writer for streaming
- Do NOT create models or logic for any other module
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- All broker API calls must go through httpx (async HTTP client)
- All financial values from broker responses must be converted to Decimal
- All timestamps from broker responses must be converted to timezone-aware UTC
- Rate limiting must be enforced on all broker REST calls

---

## Deliverables

### 1. Rate Limiter (backend/app/market_data/backfill/rate_limiter.py)

A reusable async rate limiter for broker API calls.

```python
class RateLimiter:
    """Enforces a maximum number of requests per minute.
    
    Uses a sliding window approach. acquire() blocks until
    a request slot is available.
    """
    
    def __init__(self, max_requests_per_minute: int):
        ...
    
    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        ...
```

The rate limiter is used by both the Alpaca and OANDA adapters
for all REST API calls. Default limits:
- Alpaca: 180/min (10% buffer below the 200/min actual limit)
- OANDA: 5000/min (conservative, actual is 100/sec)

The rate limiter should be injectable so tests can use a no-op version.

### 2. Alpaca Adapter Implementation (backend/app/market_data/adapters/alpaca.py)

Replace the stub with a working implementation. Uses httpx for HTTP calls.

**Authentication:**
```
Headers:
  APCA-API-KEY-ID: {api_key}
  APCA-API-SECRET-KEY: {api_secret}
```

**list_available_symbols():**
- Endpoint: GET {base_url}/v2/assets
- Filter: status=active, tradable=true
- Map response to standardized dict format matching MarketSymbol fields
- Convert all fields to the canonical format

**fetch_historical_bars():**
- Endpoint: GET https://data.alpaca.markets/v2/stocks/{symbol}/bars
- Params: timeframe, start, end, limit (max 10000 per request)
- Handle pagination if more bars exist than the limit
- Convert all prices to Decimal
- Convert all timestamps to timezone-aware UTC datetime
- Pass through the rate limiter before each API call

**fetch_option_chain():**
- Endpoint: GET https://data.alpaca.markets/v1beta1/options/snapshots/{underlying_symbol}
- Returns latest trade, quote, and Greeks per contract
- Convert prices and Greeks to Decimal
- Return structured dict matching the option chain format from the spec

**fetch_dividends():**
- Endpoint: GET {base_url}/v2/corporate_actions/announcements
- Params: ca_types=dividend, since, until, symbol
- Map response to DividendAnnouncement field format
- Convert dates and amounts appropriately

**subscribe_bars() / unsubscribe_bars() / get_connection_health():**
- Keep as NotImplementedError — these are WebSocket operations for TASK-007

**Error handling:**
- HTTP 429 (rate limited): log warning, wait, retry (up to 3 times)
- HTTP 4xx: raise appropriate DomainError
- HTTP 5xx: log error, raise MarketDataConnectionError
- Timeout: log error, raise MarketDataConnectionError
- All errors include the endpoint URL and status code in details

### 3. OANDA Adapter Implementation (backend/app/market_data/adapters/oanda.py)

Replace the stub with a working implementation.

**Authentication:**
```
Headers:
  Authorization: Bearer {access_token}
```

**list_available_symbols():**
- Endpoint: GET {base_url}/v3/accounts/{account_id}/instruments
- Map OANDA instrument format to standardized dict
- Set market="forex", extract base_asset/quote_asset from instrument name
- Set options_enabled=false (OANDA doesn't support options)

**fetch_historical_bars():**
- Endpoint: GET {base_url}/v3/instruments/{instrument}/candles
- Params: granularity (map timeframe to OANDA format: 1m→M1, 5m→M5, etc.),
  from, to, count (max 5000)
- Convert OANDA's mid/bid/ask candle format to OHLCV
  (use mid prices: (bid+ask)/2 for open/high/low/close)
- Convert all prices to Decimal
- Convert timestamps to timezone-aware UTC
- Pass through rate limiter

**Timeframe mapping:**
```
1m  → M1
5m  → M5
15m → M15
1h  → H1
4h  → H4
1d  → D
```

**fetch_option_chain():**
- Return None (OANDA does not support options — this is permanent, not a stub)

**fetch_dividends():**
- Return empty list (OANDA forex pairs don't have dividends)

**subscribe_bars() / unsubscribe_bars() / get_connection_health():**
- Keep as NotImplementedError — WebSocket operations for TASK-007

**Error handling:**
- Same patterns as Alpaca: 429 retry, 4xx domain error, 5xx connection error

### 4. Universe Filter (backend/app/market_data/universe/filter.py)

Implements the logic that narrows available symbols to a tradable watchlist.

**For equities (Alpaca):**
```python
async def run_equities_filter(db: AsyncSession) -> int:
    """Run the equities universe filter.
    
    1. Call alpaca_adapter.list_available_symbols()
    2. Filter by: exchange in configured list (NYSE, NASDAQ, AMEX)
    3. Upsert all passing symbols into market_symbols table
    4. Fetch recent daily bars for passing symbols (batched, rate-limited)
       - Alpaca multi-bar endpoint: up to 200 symbols per request
    5. Filter by: avg volume >= min_volume, price >= min_price
    6. Update watchlist: add new qualifying symbols, deactivate removed ones
       - New symbols: create WatchlistEntry with status=active, filter_metadata_json
       - Removed symbols: set removed_at, status=inactive (soft-delete)
    7. Return count of active watchlist symbols
    """
```

**For forex (OANDA):**
```python
async def run_forex_filter(db: AsyncSession) -> int:
    """Run the forex universe filter.
    
    1. Call oanda_adapter.list_available_symbols()
    2. Filter by configured pairs list (from settings)
    3. Upsert matching symbols into market_symbols table
    4. Update watchlist: add/deactivate as needed
    5. Return count of active watchlist symbols
    """
```

**Combined entry point:**
```python
async def run_universe_filter(db: AsyncSession) -> dict:
    """Run universe filter for all markets.
    
    Returns: {"equities": count, "forex": count, "total": count}
    """
```

The filter stores metadata about why each symbol passed in
filter_metadata_json (e.g., {"avg_volume": 1230000, "last_price": 47.82}).

### 5. Watchlist Management (backend/app/market_data/universe/watchlist.py)

Higher-level watchlist operations used by the service and router.

```python
async def get_active_watchlist(db, market: str | None = None) -> list[WatchlistEntry]:
    """Get all active watchlist entries, optionally filtered by market."""

async def is_symbol_active(db, symbol: str) -> bool:
    """Check if a symbol is on the active watchlist."""

async def get_watchlist_symbols(db, market: str | None = None) -> list[str]:
    """Get just the symbol strings from the active watchlist."""

async def get_watchlist_stats(db) -> dict:
    """Return counts: total, equities, forex, recently_added, recently_removed."""
```

### 6. Backfill Runner (backend/app/market_data/backfill/runner.py)

Orchestrates historical bar fetching for watchlist symbols.

```python
async def run_backfill(
    db: AsyncSession,
    symbols: list[str] | None = None,  # None = all watchlist
    timeframes: list[str] | None = None,  # None = all configured
    force: bool = False,  # True = re-fetch even if data exists
) -> dict:
    """Run historical backfill.
    
    For each symbol/timeframe combination:
    1. Check if backfill is needed (is there a gap? is this a new symbol?)
    2. Create BackfillJob record (status=pending)
    3. Determine date range based on config:
       - 1m: BACKFILL_1M_DAYS back from now
       - 1h: BACKFILL_1H_DAYS back
       - 4h: BACKFILL_4H_DAYS back
       - 1d: BACKFILL_1D_DAYS back
    4. Fetch bars from the appropriate adapter (rate-limited)
    5. Upsert bars into ohlcv_bars table using repository.upsert_bars()
    6. Update BackfillJob status (completed/failed)
    7. Handle errors: log, update job status, continue to next symbol
    
    Returns: {"total_symbols": N, "total_bars": N, "completed": N, "failed": N}
    """
```

**Backfill determination logic:**
```python
async def needs_backfill(db, symbol: str, timeframe: str) -> bool:
    """Check if a symbol/timeframe needs backfill.
    
    Returns True if:
    - No bars exist for this symbol/timeframe
    - Latest bar is older than expected (gap detected)
    - A failed backfill job exists that should be retried
    """
```

**Gap backfill (for reconnection gaps, called from TASK-007):**
```python
async def backfill_gap(
    db: AsyncSession,
    symbol: str,
    timeframe: str,
    gap_start: datetime,
    gap_end: datetime,
) -> int:
    """Backfill a specific time gap for a symbol.
    
    Used by the WebSocket manager when it reconnects after a disconnection.
    Returns count of bars fetched.
    """
```

**Rate limiting integration:**
The runner creates a RateLimiter instance per broker and passes it to
the adapter for all fetch calls. The limiter enforces the configured
requests-per-minute ceiling.

**Error handling per symbol:**
If a backfill fails for one symbol, log the error, mark the BackfillJob
as failed, and continue with the next symbol. One failure should never
halt the entire backfill process.

**Retry logic:**
Failed jobs with retry_count < BACKFILL_MAX_RETRIES can be retried.
The runner checks for retryable failed jobs on each run.

### 7. Corporate Actions Fetcher (backend/app/market_data/universe/corporate_actions.py)

Fetches dividend and split announcements from Alpaca.

```python
async def fetch_corporate_actions(
    db: AsyncSession,
    symbols: list[str] | None = None,  # None = all equity watchlist
    lookforward_days: int = 30,
) -> dict:
    """Fetch and store corporate actions.
    
    1. Determine date range: today through lookforward_days ahead
    2. Call alpaca_adapter.fetch_dividends() for watchlist symbols
    3. Upsert results into dividend_announcements table
    4. Return: {"dividends_found": N, "new": N, "updated": N}
    """
```

### 8. Update Alpaca Adapter — Batch Symbol Bars

Add a batch method to the Alpaca adapter for fetching volume/price
data for many symbols efficiently (used by the universe filter):

```python
async def fetch_latest_bars_batch(
    self,
    symbols: list[str],
    timeframe: str = "1Day",
    limit: int = 1,
) -> dict[str, dict]:
    """Fetch the latest bar(s) for multiple symbols in one call.
    
    Endpoint: GET https://data.alpaca.markets/v2/stocks/bars
    Params: symbols (comma-separated, max 200), timeframe, limit
    
    Used by universe filter to get volume/price for filtering.
    Batches into groups of 200 to respect API limits.
    Returns: {symbol: {open, high, low, close, volume, ...}}
    """
```

### 9. Update Market Data Service (backend/app/market_data/service.py)

Implement the methods that were previously NotImplementedError:

```python
async def get_option_chain(self, underlying_symbol: str) -> dict | None:
    """Fetch option chain with caching.
    
    1. Check in-memory cache (TTL = OPTION_CACHE_TTL_SEC)
    2. If cached and fresh: return cached
    3. If stale or missing: fetch from Alpaca adapter
    4. Cache the result
    5. Return
    """

async def get_dividend_yield(self, db, symbol: str) -> Decimal | None:
    """Calculate annualized dividend yield.
    
    1. Get recent dividends for symbol (last 12 months)
    2. Sum the per-share amounts
    3. Get current price
    4. yield = annual_dividends / current_price * 100
    5. Return as Decimal, or None if no dividend data
    """
```

Also add methods for the universe filter and backfill:

```python
async def run_universe_filter(self, db) -> dict:
    """Run the universe filter for all markets."""

async def run_backfill(self, db, symbols=None, timeframes=None, force=False) -> dict:
    """Run historical backfill."""

async def fetch_corporate_actions(self, db, symbols=None) -> dict:
    """Fetch and store corporate actions."""
```

### 10. Update Market Data Router (backend/app/market_data/router.py)

Replace the 501 stubs with working endpoints:

```
POST /api/v1/market-data/backfill/trigger     → calls service.run_backfill()
                                                 (admin only, returns job summary)
POST /api/v1/market-data/watchlist/refresh     → calls service.run_universe_filter()
                                                 (admin only, returns filter results)
```

The health endpoint stays 501 — that requires WebSocket state from TASK-007.

Add a new endpoint:
```
GET /api/v1/market-data/options/chain/:symbol  → calls service.get_option_chain()
                                                 (requires auth)
```

### 11. Option Chain Cache (backend/app/market_data/options/chain.py)

Simple in-memory cache with TTL for option chain data.

```python
class OptionChainCache:
    """In-memory cache for option chain snapshots.
    
    TTL-based. If a cached chain is older than OPTION_CACHE_TTL_SEC,
    it's considered stale and will be re-fetched.
    """
    
    def get(self, underlying_symbol: str) -> dict | None:
        """Get cached chain if fresh, None if stale/missing."""
    
    def set(self, underlying_symbol: str, chain: dict) -> None:
        """Cache a chain snapshot."""
    
    def clear(self, underlying_symbol: str | None = None) -> None:
        """Clear one or all cached chains."""
```

### 12. Add httpx Dependency

Add httpx to the project dependencies if not already present.
It should already be in pyproject.toml from TASK-001, but verify.

---

## Acceptance Criteria

1. RateLimiter class works with configurable requests/minute and blocks when limit reached
2. Alpaca adapter authenticates with API key headers
3. Alpaca adapter list_available_symbols fetches and normalizes asset data
4. Alpaca adapter fetch_historical_bars fetches bars with pagination, converts to Decimal/UTC
5. Alpaca adapter fetch_latest_bars_batch handles batching (200 symbols per call)
6. Alpaca adapter fetch_option_chain returns structured chain data with Greeks
7. Alpaca adapter fetch_dividends returns normalized dividend announcements
8. All Alpaca adapter methods pass through the rate limiter
9. All Alpaca adapter methods handle HTTP errors (429 retry, 4xx, 5xx, timeout)
10. OANDA adapter authenticates with Bearer token
11. OANDA adapter list_available_symbols fetches and normalizes instrument data
12. OANDA adapter fetch_historical_bars fetches candles with timeframe mapping, converts mid prices to Decimal/UTC
13. OANDA adapter fetch_option_chain returns None (permanent, not stub)
14. OANDA adapter fetch_dividends returns empty list (permanent, not stub)
15. All OANDA adapter methods pass through the rate limiter
16. Universe filter runs for equities: fetches symbols, filters by exchange/volume/price, updates watchlist
17. Universe filter runs for forex: applies configured pairs list, updates watchlist
18. Watchlist soft-deletes removed symbols (sets removed_at, status=inactive)
19. Watchlist stores filter_metadata_json explaining why each symbol passed
20. Backfill runner creates BackfillJob records and updates their status
21. Backfill runner fetches bars from correct adapter based on market
22. Backfill runner respects rate limits via RateLimiter
23. Backfill runner handles per-symbol failures without halting entire process
24. Backfill runner supports retry for failed jobs (up to max retries)
25. Gap backfill function exists for targeted time-range backfill
26. Corporate actions fetcher retrieves and upserts dividend announcements
27. Option chain cache implements TTL-based caching
28. Service.get_option_chain uses cache with fallback to adapter
29. Service.get_dividend_yield calculates annualized yield from stored dividends
30. POST /api/v1/market-data/backfill/trigger works (admin only)
31. POST /api/v1/market-data/watchlist/refresh works (admin only)
32. GET /api/v1/market-data/options/chain/:symbol works (auth required)
33. All financial values from broker APIs converted to Decimal (never stored as float)
34. All timestamps from broker APIs converted to timezone-aware UTC
35. No WebSocket connections or streaming logic implemented
36. No bar aggregation logic implemented
37. No health monitoring implemented
38. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-006-market-data-rest/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
