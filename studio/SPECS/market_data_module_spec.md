# MARKET_DATA_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the market data module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The market_data module owns:

- Broker adapter abstraction
- Broker-specific adapters (Alpaca, OANDA)
- Universe filter and watchlist management
- WebSocket stream connections and lifecycle
- Bar ingestion, normalization, storage, and aggregation
- Options chain data access and caching
- Historical backfill
- Market data health monitoring
- All database tables: ohlcv_bars, market_symbols, watchlist_entries, backfill_jobs

The market_data module does NOT own:

- Strategy evaluation logic
- Signal generation
- Risk decisions
- Portfolio state
- Order execution

---

## 1. Broker Abstraction

### Design

All broker-specific logic is encapsulated behind a common adapter interface.
Nothing outside the market_data module knows which broker data came from.
Strategies request bars by symbol and timeframe. The market data service routes
to the correct adapter internally.

### Adapter Interface

Every broker adapter must implement:

- list_available_symbols() → list of tradable symbols with metadata
- subscribe_bars(symbols: list[str]) → start streaming 1m bars
- unsubscribe_bars(symbols: list[str]) → stop streaming specific symbols
- fetch_historical_bars(symbol, timeframe, start, end) → list of bars
- fetch_option_chain(underlying_symbol) → option chain snapshot (if supported)
- get_connection_health() → connection status object

### Symbol-to-Broker Routing

Each symbol record in the database has a `market` field (equities, forex).
The market data service maintains a mapping:

- equities → AlpacaAdapter
- forex → OandaAdapter

Adding a new broker means adding a new adapter file and registering the
market-to-adapter mapping.

### Folder Structure

```
backend/app/market_data/
    __init__.py
    service.py              ← main market data service, routes to adapters
    models.py               ← SQLAlchemy models
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← market data specific configuration
    health.py               ← health monitoring system
    adapters/
        __init__.py
        base.py             ← abstract adapter interface
        alpaca.py            ← Alpaca implementation (equities + options)
        oanda.py             ← OANDA implementation (forex)
    streams/
        __init__.py
        manager.py           ← WebSocket connection lifecycle manager
        bar_processor.py     ← normalize, validate, queue bars
    options/
        __init__.py
        chain.py             ← fetch/cache option chains
        contracts.py         ← contract discovery and filtering
    backfill/
        __init__.py
        runner.py            ← backfill orchestration
        rate_limiter.py      ← enforced API rate limiting
    universe/
        __init__.py
        filter.py            ← universe filter logic
        watchlist.py         ← watchlist management
    aggregation/
        __init__.py
        engine.py            ← timeframe aggregation logic
```

### Credential Management

Broker credentials are loaded from environment variables via the config system.
Never stored in code or database.

```
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/sip
OANDA_ACCESS_TOKEN=...
OANDA_ACCOUNT_ID=...
OANDA_BASE_URL=https://api-fxpractice.oanda.com
OANDA_STREAM_URL=https://stream-fxpractice.oanda.com
```

---

## 2. Universe Filter

### Purpose

Narrow the full set of available symbols from each broker to a curated
watchlist of symbols worth monitoring. Only watchlist symbols receive
streaming data and are available for strategy evaluation.

### Equities (Alpaca)

**Frequency:** Runs once daily, before market open (e.g., 9:00 AM ET).

**Process:**

1. Call Alpaca asset listing endpoint (1 REST call, returns all assets)
2. Filter in code by:
   - status = active
   - tradable = true
   - exchange in [NYSE, NASDAQ, AMEX] (exclude OTC/pink sheets)
   - This reduces ~13,000 to ~4,000-5,000 symbols
3. Fetch most recent daily bar for remaining symbols in batches
   - Alpaca multi-bar endpoint: up to 200 symbols per call
   - ~4,500 symbols ÷ 200 = ~23 API calls
   - At 200 requests/min, completes in under 10 seconds
4. Filter by:
   - Average daily volume >= configurable threshold (default: 500,000 shares)
   - Price >= configurable minimum (default: $5.00)
5. Write surviving symbols to the watchlist table
6. Log: symbols added, symbols removed, total count

**Expected output:** 300-800 symbols depending on filter settings.

**Configuration:**

```
UNIVERSE_FILTER_EQUITIES_MIN_VOLUME=500000
UNIVERSE_FILTER_EQUITIES_MIN_PRICE=5.00
UNIVERSE_FILTER_EQUITIES_EXCHANGES=NYSE,NASDAQ,AMEX
UNIVERSE_FILTER_EQUITIES_SCHEDULE=0 9 * * 1-5  (cron: 9 AM ET, weekdays)
```

### Forex (OANDA)

**Frequency:** Static or semi-static configuration. No daily job required.

**Process:**

The forex universe is naturally small (~70 pairs on OANDA). The watchlist
is defined by a configured list of pairs, not a dynamic filter.

```
UNIVERSE_FILTER_FOREX_PAIRS=EUR_USD,GBP_USD,USD_JPY,USD_CHF,AUD_USD,USD_CAD,NZD_USD,EUR_GBP,EUR_JPY,GBP_JPY,...
```

Changes require a config update and restart or a future admin UI.

### Watchlist Data Model

```
WatchlistEntry:
  - id: UUID
  - symbol: str
  - market: str (equities | forex)
  - broker: str (alpaca | oanda)
  - status: str (active | inactive)
  - added_at: datetime (UTC, timezone-aware)
  - removed_at: datetime, nullable (soft-delete for audit trail)
  - filter_metadata_json: dict (why it passed — volume, price, etc.)
  - updated_at: datetime (UTC, timezone-aware)

Uniqueness: (symbol, market, broker) where status = active
```

**Design decisions:**

- Soft-delete with removed_at timestamp, never hard-delete. If a strategy
  had positions in a symbol that later fell off the watchlist, you need
  to know when and why.
- filter_metadata_json stores the values that caused the symbol to pass
  (e.g., {"avg_volume": 1230000, "last_price": 47.82}). This enables
  debugging when symbols disappear from the watchlist.
- The watchlist is the single source of truth for "what symbols does the
  system care about." WebSocket subscriptions, strategy evaluation, and
  data fetching all reference the watchlist.

### Strategy-Specific Symbol Lists

The system watchlist is the superset. Each strategy config includes its own
symbol filter or explicit symbol list — a subset of the system watchlist.

```
System Watchlist (superset, 300-800 symbols)
  └── Strategy A config: symbols = [AAPL, MSFT, GOOGL, ...]
  └── Strategy B config: symbols = [EUR_USD, GBP_JPY]
  └── Strategy C config: market = equities, min_volume = 1000000
```

Strategies can only reference symbols on the system watchlist.
If a symbol isn't on the watchlist, it doesn't exist to the system.

---

## 3. WebSocket Manager

### Purpose

Maintain persistent WebSocket connections to each broker's streaming API.
Receive real-time 1m bar data and feed it into the bar storage pipeline.

### Connection Architecture

One WebSocket connection per broker:

```
WebSocketManager
  ├── AlpacaStreamConnection (1 connection, N equity symbols)
  └── OandaStreamConnection  (1 connection, N forex pairs)
```

Both Alpaca and OANDA support WebSocket streaming. This eliminates the need
for REST polling for real-time data, avoiding rate limit concerns for
data ingestion entirely.

### Connection Lifecycle

**Startup:**

1. Read the active watchlist from the database
2. Group symbols by broker
3. Open one WebSocket connection per broker
4. Authenticate each connection using adapter credentials
5. Subscribe to 1m bar streams for the relevant symbols
6. Log: connection established, symbols subscribed, timestamp

**Steady state:**

- Receive bar data as it arrives from each broker
- Deserialize using the broker adapter's normalization logic
- Push normalized bars into an async queue for processing
- Log a heartbeat every 60 seconds with stats

**Reconnection (exponential backoff with ceiling):**

```
On disconnect:
  1. Log disconnect with timestamp and reason
  2. Wait WS_RECONNECT_INITIAL_DELAY_SEC (default: 1)
  3. Attempt reconnect
  4. If failed: multiply wait by WS_RECONNECT_BACKOFF_MULTIPLIER (default: 2)
  5. Cap wait at WS_RECONNECT_MAX_DELAY_SEC (default: 60)
  6. On success: re-authenticate, re-subscribe
  7. Log reconnection with gap duration
  8. Trigger gap backfill for the missed period
```

**Shutdown:**

- Cleanly close all WebSocket connections
- Drain remaining bars from the async queue
- Log shutdown timestamp

### Subscription Management

When the watchlist changes (daily universe filter adds/removes symbols),
update subscriptions on the live connection without dropping it.

```
On watchlist update:
  1. Compute diff: current subscriptions vs new watchlist
  2. Unsubscribe from removed symbols
  3. Subscribe to added symbols
  4. Log changes (added count, removed count)
  5. Trigger backfill for newly added symbols
```

Current subscription state is tracked in memory (ephemeral runtime state).

### Async Model

Since FastAPI runs on asyncio, the WebSocket manager also uses async.
Each broker connection runs as an async task started at application boot.

```
On app startup:
  - start AlpacaStreamConnection as async task
  - start OandaStreamConnection as async task

On app shutdown:
  - cancel both tasks gracefully
```

### Bar Receive Queue

Critical design: bar processing (DB writes) must not block the WebSocket
receive loop. If writing to the database takes too long, the receive loop
falls behind and misses incoming messages.

Solution: receive bars into an async queue, drain the queue in a separate
async task.

```
WebSocket receive loop → async queue → batch DB writer task
```

The queue has a maximum size (WS_BAR_QUEUE_MAX_SIZE, default: 10,000).
If the queue approaches capacity, log a backpressure warning.

### Configuration

```
WS_RECONNECT_INITIAL_DELAY_SEC=1
WS_RECONNECT_MAX_DELAY_SEC=60
WS_RECONNECT_BACKOFF_MULTIPLIER=2
WS_HEARTBEAT_INTERVAL_SEC=60
WS_STALE_DATA_THRESHOLD_SEC=120
WS_BAR_QUEUE_MAX_SIZE=10000
```

### Rate Limits (Reference)

**Alpaca:**
- REST API: 200 requests per minute, burst limit 10/second
- WebSocket: 1 connection per data endpoint (no message limit)
- Paid plans can increase REST to 1,000/min

**OANDA:**
- REST API: 100 requests per second on persistent connections
- Max 2 new connections per second
- Streaming: 1 connection, up to 4 price updates/second per instrument

WebSocket streaming avoids REST rate limit concerns for data ingestion.
REST budget is reserved for: universe filter, backfill, order placement,
account queries, and option chain fetches.

---

## 4. Bar Storage

### Write Path

```
WebSocket → deserialize → normalize → validate → async queue → batch write → DB → aggregate
```

**Deserialize:** Broker adapter converts raw WebSocket JSON into Python objects.
Alpaca and OANDA have different message formats; each adapter handles its own.

**Normalize:** Convert to canonical OHLCVBar schema:
- Parse timestamps to timezone-aware UTC datetime
- Map broker-specific field names to canonical names
- Ensure symbol format matches the watchlist record

**Validate before writing:**
- Symbol is on the active watchlist (reject stray data)
- Timestamp is reasonable (not in the future, not wildly in the past)
- OHLCV values are non-negative
- Check for duplicates (same symbol + timeframe + ts)

Validation failures are logged as warnings but do not crash the pipeline.
Bad data is dropped with a log entry, never silently swallowed, never
an unhandled exception.

### OHLCVBar Data Model

```
OHLCVBar:
  - id: UUID
  - symbol: str
  - market: str (equities | forex)
  - timeframe: str (1m | 5m | 15m | 1h | 4h | 1d)
  - ts: datetime (bar open timestamp, UTC, timezone-aware)
  - open: Decimal
  - high: Decimal
  - low: Decimal
  - close: Decimal
  - volume: Decimal
  - source: str (alpaca | oanda)
  - is_aggregated: bool (default false)
  - created_at: datetime (UTC, timezone-aware)

Uniqueness constraint: UNIQUE (symbol, timeframe, ts)
Primary query index: INDEX on (symbol, timeframe, ts)
```

**Field notes:**

- `market` is denormalized from the watchlist for query convenience
  (filter "all equity bars" without joining)
- `is_aggregated` distinguishes bars from the broker stream (false) from
  bars computed by aggregation logic (true). Useful for debugging.
- `volume` is Decimal to handle fractional volume in forex/crypto
- All financial values use Decimal, never float

### Duplicate Handling

**Policy: upsert (INSERT ON CONFLICT UPDATE)**

If a bar arrives for a symbol/timeframe/ts that already exists, overwrite it.
The broker's latest data is more authoritative than previously stored data
(bars can be corrected/updated after initial emission).

Log every upsert so it's auditable, but do not error.

### Batch Writing

Instead of one DB insert per bar, accumulate bars and flush in batches:

```
Async queue → batch writer (every 2-3 seconds) → DB bulk upsert
```

Batch size: 50-100 bars per flush.
This reduces database round-trips. At peak load (~300 symbols streaming
1m bars), that's ~5 bars/second — trivial for PostgreSQL, but batching
is still good practice.

After each batch write, trigger aggregation checks for any completed
higher-timeframe windows.

Log per batch: "wrote 87 bars, aggregated 12 5m bars, 3 15m bars"

### Timeframe Aggregation

**Policy: aggregate on write, always from 1m bars.**

When a 1m bar is written that completes a higher-timeframe window,
the aggregation engine builds the higher-timeframe bar immediately.

Supported timeframes built from 1m:

```
1m (from stream, is_aggregated = false)
  → 5m  (every 5 completed 1m bars)
  → 15m (every 15 completed 1m bars)
  → 1h  (every 60 completed 1m bars)
  → 4h  (every 240 completed 1m bars)
  → 1d  (all 1m bars in the trading session)
```

**Aggregation logic:**

```
Given N consecutive 1m bars within a timeframe window:
  open   = first bar's open
  high   = max of all bars' highs
  low    = min of all bars' lows
  close  = last bar's close
  volume = sum of all bars' volumes
  ts     = window start timestamp
  is_aggregated = true
```

**All higher timeframes aggregate directly from 1m, not cascading.**
Do not build 15m from 5m. Build all from 1m. This avoids compounding
rounding or timing errors.

**Incomplete windows:**

If not all 1m bars exist for a timeframe window, do NOT build it.
Wait until the set is complete. A gap in data produces a gap in
aggregated bars — never fabricate partial bars.

Log a warning when a gap is detected (expected 1m bar did not arrive
within a reasonable window after its expected time).

### Read Path

Strategies query bars through the market data service:

```python
bars = await market_data_service.get_bars(
    symbol="AAPL",
    timeframe="1h",
    limit=200
)

bars = await market_data_service.get_bars(
    symbol="EUR_USD",
    timeframe="5m",
    start=datetime(2025, 1, 1, tzinfo=timezone.utc),
    end=datetime(2025, 3, 10, tzinfo=timezone.utc)
)
```

Strategies never write SQL directly. The service handles the query.

Underlying query pattern:

```sql
SELECT * FROM ohlcv_bars
WHERE symbol = :symbol
  AND timeframe = :timeframe
ORDER BY ts DESC
LIMIT :limit
```

The composite index on (symbol, timeframe, ts) covers this pattern.

### Data Retention (Future)

Not required for MVP, but noted as a future concern:

- 1m bars: keep 3-6 months, then archive or delete
- 5m, 15m bars: keep 1 year
- 1h and above: keep indefinitely (small volume, useful for backtesting)

Do not design anything that assumes infinite 1m bar retention.

---

## 5. Historical Backfill

### Purpose

When the system first launches, or when a new symbol is added, fetch
enough historical bar data that strategies have a working runway from
the moment they start evaluating.

### Required History Depth

```
1m bars:   30 calendar days
5m bars:   derived from 1m (aggregated during backfill)
15m bars:  derived from 1m (aggregated during backfill)
1h bars:   1 year (fetched directly from broker)
4h bars:   1 year (fetched directly from broker)
1d bars:   2 years (fetched directly from broker)
```

**Rationale:** A strategy using a 200-period moving average on 1h bars
needs ~200 hours (~8-9 trading days). The above provides generous
buffer for any reasonable indicator lookback.

**Hybrid fetch strategy:**

- 1m bars: fetch from broker, then aggregate locally to build 5m and 15m
- 1h, 4h, 1d bars: fetch directly from broker at native resolution

This minimizes API calls while providing accurate data at every timeframe.

### Backfill Process for Alpaca (Equities)

Alpaca historical bars endpoint: up to 10,000 bars per request.

Per-symbol API calls:
- 1m (30 days): ~12,000 bars → 2 API calls
- 1h (1 year): ~1,700 bars → 1 API call
- 4h (1 year): ~425 bars → 1 API call
- 1d (2 years): ~504 bars → 1 API call
- **Total per symbol: ~5 API calls**

For 300 watchlist symbols:
- ~1,500 API calls total
- At 180 requests/min (with headroom): ~8-9 minutes

After 1m bars are stored, run aggregation to build 5m and 15m bars.

### Backfill Process for OANDA (Forex)

OANDA candle endpoint: up to 5,000 bars per request.
With 20-30 forex pairs: ~100-150 API calls. Under 1 minute.

### Rate Limiting

The backfill runner has an explicit, enforced rate limiter:

```python
class RateLimiter:
    max_requests_per_minute: int  # 180 (10% headroom below Alpaca's 200)

    async def acquire(self):
        # blocks until a request slot is available
```

Every API call passes through this limiter. The 10% buffer below the
actual broker limit leaves headroom for other operations that might
be running simultaneously (e.g., the universe filter).

### When Backfill Runs

**Scenario 1 — First launch:**
No data exists. System detects empty ohlcv_bars table and triggers full
backfill. Strategies do NOT start evaluating until backfill is complete.

**Scenario 2 — New symbol added to watchlist:**
Daily universe filter adds a symbol. System detects no history for this
symbol. WebSocket subscription starts immediately (don't miss live data).
Backfill runs in background to fill historical data.

**Scenario 3 — Reconnection gap:**
WebSocket dropped for N minutes. On reconnect, system identifies the
last received bar timestamp per symbol and backfills the gap via REST.
Small, targeted backfill — a few API calls per affected symbol.

### Backfill Job Tracking

```
BackfillJob:
  - id: UUID
  - symbol: str
  - market: str
  - timeframe: str
  - start_date: datetime
  - end_date: datetime
  - status: str (pending | running | completed | failed)
  - bars_fetched: int
  - started_at: datetime, nullable
  - completed_at: datetime, nullable
  - error_message: str, nullable
  - retry_count: int (default 0)
  - created_at: datetime

Index: (symbol, timeframe, status)
```

This enables observability: "the 1m backfill for MSFT failed at 10:03
with a 429 error, retried at 10:04, completed at 10:05."

### Backfill Observability (Dashboard)

```
Backfill Status:
  Equities: 247/312 symbols complete (79%)
  Forex: complete
  Estimated time remaining: 1m 30s
  Failed jobs: 2 (TSLA 1m — 429 rate limit, retrying)

  Strategy readiness:
    momentum_5m: READY (all required symbols backfilled)
    breakout_1h: WAITING (14 symbols pending)
```

### Configuration

```
BACKFILL_1M_DAYS=30
BACKFILL_1H_DAYS=365
BACKFILL_4H_DAYS=365
BACKFILL_1D_DAYS=730
BACKFILL_RATE_LIMIT_BUFFER_PERCENT=10
BACKFILL_MAX_RETRIES=3
BACKFILL_RETRY_DELAY_SEC=30
```

---

## 6. Options Data

### Design Philosophy

Options data is NOT streamed through the same pipeline as equity/forex bars.
It has a fundamentally different shape (chain of contracts per underlying),
much higher data volume, and a different access pattern (on-demand, not
continuous streaming).

### Data Access Pattern

Options data is fetched **on demand** when needed, not streamed continuously.

**Scenario 1 — Strategy uses equity signal, expresses as option:**
Strategy signal says "buy AAPL." Strategy config says "express as ATM call,
30 DTE." At signal time, fetch the option chain for AAPL (1 API call), find
the matching contract, include contract symbol in the signal.

**Scenario 2 — Options-aware scanning:**
Strategy scans for high IV rank across its watchlist. Runs on a schedule
(e.g., every 15 minutes). Fetches option chain snapshot per symbol. For
50 symbols: 50 API calls per 15 minutes. Well within rate limits.

**Scenario 3 — Active position monitoring:**
Open options positions need current Greeks. Periodically fetch snapshots
for held contracts only. 10 positions = 10 API calls every few minutes.

### Caching

Option chains are cached in-memory with a short TTL to prevent
redundant API calls:

```
Option chain request for AAPL:
  1. Check cache — is there a chain less than OPTION_CACHE_TTL_SEC old?
  2. If yes → return cached data
  3. If no → fetch from broker, cache, return
```

Cache is in-memory (not database). This is ephemeral, fast-access data.

```
OPTION_CACHE_TTL_SEC=60
```

### Options Data Models

```
OptionContract:
  - id: UUID
  - symbol: str (OCC symbol, e.g., "AAPL250620C00190000")
  - underlying_symbol: str
  - expiration_date: date
  - strike_price: Decimal
  - contract_type: str (call | put)
  - status: str (active | expired)
  - created_at: datetime
  - updated_at: datetime

OptionSnapshot:
  - id: UUID
  - contract_symbol: str
  - underlying_symbol: str
  - latest_price: Decimal
  - bid: Decimal
  - ask: Decimal
  - volume: int
  - open_interest: int
  - implied_volatility: Decimal
  - delta: Decimal
  - gamma: Decimal
  - theta: Decimal
  - vega: Decimal
  - fetched_at: datetime
  - created_at: datetime
```

### Persistence Policy

- Real-time snapshots: NOT persisted. Fetched, used, cached briefly, discarded.
- Snapshots at trade entry/exit: PERSISTED. When a signal results in an order,
  record the Greeks at that moment for audit purposes. Tied to the signal or
  order record.
- Historical options data for backtesting: separate concern, addressed in
  backtesting module spec.

### Integration with Pipeline

Options data does not change the core pipeline flow:

```
Universe Filter → Market Data (bar streams) → Strategies → Risk → Execution
                          ↑
                    Options Chain (on-demand, when strategies request it)
```

Strategies that trade options have an additional data dependency: they call
market_data_service.get_option_chain(symbol) during evaluation. The market
data module handles the fetch, caching, and adapter routing internally.

Portfolio accounting differences for options (expiration, assignment, exercise)
are a portfolio module concern, not a market data concern.

---

## 7. Health Monitoring

### Purpose

Provide continuous, queryable health status for the entire market data module.
Every component of the system can check whether market data is trustworthy
before acting on it.

### Failure Modes Detected

1. **Silent death:** WebSocket connected at TCP level but no data flowing.
   Detected by checking last_message_at against staleness threshold.

2. **Partial failure:** Connection alive but specific symbols stopped streaming.
   Detected by per-symbol freshness scan.

3. **Stale data:** Bars arriving but delayed. Detected by comparing bar
   timestamps to current time.

4. **Write pipeline failure:** Bars arrive but fail to persist. Queue fills up.
   Detected by monitoring queue depth and write error counts.

5. **Aggregation failure:** Higher-timeframe bars not building. Detected by
   tracking aggregation success/failure counts.

### Health Status Object

```
MarketDataHealth:
  overall_status: healthy | degraded | unhealthy

  connections:
    alpaca:
      status: connected | disconnected | reconnecting
      connected_since: datetime
      last_message_at: datetime
      subscribed_symbols: int
      bars_received_last_minute: int
    oanda:
      status: connected | disconnected | reconnecting
      connected_since: datetime
      last_message_at: datetime
      subscribed_symbols: int
      bars_received_last_minute: int

  data_freshness:
    symbols_with_stale_data: list[str]
    staleness_threshold_sec: int
    last_check_at: datetime

  write_pipeline:
    queue_depth: int
    queue_max: int
    bars_written_last_minute: int
    write_errors_last_minute: int
    last_successful_write_at: datetime

  aggregation:
    aggregations_completed_last_minute: int
    aggregations_failed_last_minute: int
    last_successful_aggregation_at: datetime

  backfill:
    status: idle | running | failed
    pending_symbols: int
    last_completed_at: datetime
```

### Market-Aware Staleness Checks

Staleness detection must account for market hours:

**Equities:**
- Active during market hours only (9:30 AM - 4:00 PM ET, weekdays)
- Staleness threshold: 120 seconds
- Outside market hours: suppress alerts (no data expected)

**Forex:**
- Active Sunday 5 PM ET through Friday 5 PM ET
- Staleness threshold: 120 seconds
- Weekend: suppress alerts

### Per-Symbol Freshness Check

Runs every MARKET_DATA_STALE_CHECK_INTERVAL_SEC (default: 60 seconds).

```sql
SELECT symbol, MAX(ts) as latest_bar
FROM ohlcv_bars
WHERE timeframe = '1m'
  AND symbol IN (... active watchlist ...)
GROUP BY symbol
HAVING MAX(ts) < NOW() - INTERVAL ':threshold seconds'
```

Results feed the `symbols_with_stale_data` list.

### Write Pipeline Health Levels

```
queue_depth < 20% of max  → healthy
queue_depth 20-80% of max → degraded (log warning)
queue_depth > 80% of max  → unhealthy (log error, possible data loss)
```

### Overall Status Derivation

```
HEALTHY:
  - All connections active
  - No stale symbols (during market hours)
  - Queue depth low
  - No write errors
  - Aggregation current

DEGRADED:
  - One connection reconnecting, OR
  - A few symbols stale (< 10%), OR
  - Queue depth elevated (20-80%), OR
  - Occasional write errors
  - System is still functional but needs attention

UNHEALTHY:
  - Connection down for > 5 minutes, OR
  - More than 10% of symbols stale, OR
  - Queue near capacity (> 80%), OR
  - Sustained write errors, OR
  - Backfill failed and strategies lack required data
```

### Strategy Gate Integration

Strategies check market data health before each evaluation cycle:

```
Before running strategy X:
  1. Check market_data_health.overall_status
  2. If UNHEALTHY → skip evaluation, log reason
  3. If DEGRADED → check if THIS strategy's symbols are affected
     → if affected: skip, log
     → if not affected: proceed with warning
  4. If HEALTHY → proceed normally
```

A strategy running on stale data is worse than a strategy not running.

### Health API Endpoint

```
GET /api/v1/market-data/health

Response:
{
  "overall_status": "healthy",
  "connections": {
    "alpaca": {
      "status": "connected",
      "connected_since": "2025-03-10T09:29:45Z",
      "uptime_seconds": 14523,
      "bars_received_last_minute": 312,
      "subscribed_symbols": 312
    },
    "oanda": {
      "status": "connected",
      "connected_since": "2025-03-10T09:29:47Z",
      "uptime_seconds": 14521,
      "bars_received_last_minute": 28,
      "subscribed_symbols": 28
    }
  },
  "stale_symbols": [],
  "write_pipeline": {
    "queue_depth": 12,
    "queue_max": 10000,
    "bars_written_last_minute": 340,
    "write_errors_last_minute": 0
  },
  "backfill": {
    "status": "idle",
    "pending_symbols": 0
  }
}
```

### Health Event Log

Every health state transition is logged as a structured event:

```
market_data.connection.established
market_data.connection.lost
market_data.connection.reconnecting
market_data.connection.recovered
market_data.symbol.stale         (with symbol name)
market_data.symbol.recovered
market_data.queue.backpressure_warning
market_data.queue.backpressure_critical
market_data.write.error          (with details)
market_data.aggregation.failed
market_data.health.degraded
market_data.health.unhealthy
market_data.health.recovered
```

These feed both the dashboard logs view and the audit_events table.

### Configuration

```
MARKET_DATA_STALE_THRESHOLD_SEC=120
MARKET_DATA_STALE_CHECK_INTERVAL_SEC=60
MARKET_DATA_QUEUE_WARN_PERCENT=20
MARKET_DATA_QUEUE_CRITICAL_PERCENT=80
MARKET_DATA_HEALTH_CHECK_INTERVAL_SEC=30
```

---

## 8. System Startup Sequence

The complete boot sequence for the market data module:

```
1. Load config
   → broker credentials, rate limits, thresholds

2. Run universe filter
   → fetch available symbols from each broker
   → apply filter rules
   → write/update watchlist table

3. Check backfill status for each watchlist symbol
   → identify symbols needing full or partial backfill

4. Run backfill (rate-limited)
   → fetch historical bars from broker REST APIs
   → write to ohlcv_bars table
   → aggregate higher timeframes from 1m data
   → log progress, update BackfillJob records

5. Start WebSocket connections
   → open connection per broker
   → authenticate
   → subscribe to all watchlist symbols
   → bars flow: WebSocket → async queue → batch writer → DB → aggregation

6. Start health monitoring
   → begin periodic health checks
   → begin per-symbol freshness scans

7. Mark market data service as READY
   → strategies can now begin evaluating
   → dashboard can display live pipeline status
```

Nothing evaluates, no signals fire, no trades happen until step 7.

---

## 9. All Configuration Variables

```env
# === Broker Credentials ===
ALPACA_API_KEY=
ALPACA_API_SECRET=
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/sip
OANDA_ACCESS_TOKEN=
OANDA_ACCOUNT_ID=
OANDA_BASE_URL=https://api-fxpractice.oanda.com
OANDA_STREAM_URL=https://stream-fxpractice.oanda.com

# === Universe Filter ===
UNIVERSE_FILTER_EQUITIES_MIN_VOLUME=500000
UNIVERSE_FILTER_EQUITIES_MIN_PRICE=5.00
UNIVERSE_FILTER_EQUITIES_EXCHANGES=NYSE,NASDAQ,AMEX
UNIVERSE_FILTER_EQUITIES_SCHEDULE=0 9 * * 1-5

# === WebSocket ===
WS_RECONNECT_INITIAL_DELAY_SEC=1
WS_RECONNECT_MAX_DELAY_SEC=60
WS_RECONNECT_BACKOFF_MULTIPLIER=2
WS_HEARTBEAT_INTERVAL_SEC=60
WS_STALE_DATA_THRESHOLD_SEC=120
WS_BAR_QUEUE_MAX_SIZE=10000

# === Bar Storage ===
BAR_BATCH_WRITE_SIZE=100
BAR_BATCH_WRITE_INTERVAL_SEC=3

# === Backfill ===
BACKFILL_1M_DAYS=30
BACKFILL_1H_DAYS=365
BACKFILL_4H_DAYS=365
BACKFILL_1D_DAYS=730
BACKFILL_RATE_LIMIT_BUFFER_PERCENT=10
BACKFILL_MAX_RETRIES=3
BACKFILL_RETRY_DELAY_SEC=30

# === Options ===
OPTION_CACHE_TTL_SEC=60

# === Health Monitoring ===
MARKET_DATA_STALE_THRESHOLD_SEC=120
MARKET_DATA_STALE_CHECK_INTERVAL_SEC=60
MARKET_DATA_QUEUE_WARN_PERCENT=20
MARKET_DATA_QUEUE_CRITICAL_PERCENT=80
MARKET_DATA_HEALTH_CHECK_INTERVAL_SEC=30
```

---

## 10. Database Tables Owned by This Module

| Table | Purpose |
|---|---|
| market_symbols | Symbol metadata (exchange, base/quote asset, status) |
| watchlist_entries | Curated active watchlist with filter metadata |
| ohlcv_bars | All bar data (streamed and aggregated) |
| backfill_jobs | Backfill job tracking and status |
| option_contracts | Option contract metadata (when discovered) |
| option_snapshots | Option chain snapshots tied to trades (audit) |

---

## 11. API Endpoints Owned by This Module

```
GET  /api/v1/market-data/health              → health status object
GET  /api/v1/market-data/watchlist            → current active watchlist
GET  /api/v1/market-data/bars                 → query bars (symbol, timeframe, limit/range)
GET  /api/v1/market-data/symbols              → list known symbols with metadata
GET  /api/v1/market-data/backfill/status      → current backfill job status
GET  /api/v1/market-data/options/chain/:symbol → option chain for underlying
POST /api/v1/market-data/backfill/trigger     → manually trigger backfill (admin)
POST /api/v1/market-data/watchlist/refresh    → manually trigger universe filter (admin)
```

---

## Acceptance Criteria

This spec is accepted when:

- Broker abstraction interface is defined
- Adapter folder structure is explicit
- Universe filter rules and frequency are defined for each market
- Watchlist data model is complete
- WebSocket lifecycle (connect, reconnect, subscribe, shutdown) is specified
- Bar write path (deserialize → normalize → validate → batch write) is explicit
- Aggregation policy (on write, from 1m, never partial) is locked
- Backfill triggers, depth, and rate limiting are defined
- Options data access pattern (on-demand, cached, not streamed) is defined
- Health monitoring covers all failure modes
- Strategy gate (don't evaluate on unhealthy data) is specified
- Startup sequence is defined end-to-end
- All configuration variables are listed
- All database tables and API endpoints are enumerated
- A builder agent can implement this module without asking engineering design questions
