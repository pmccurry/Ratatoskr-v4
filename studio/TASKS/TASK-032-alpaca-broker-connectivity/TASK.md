# TASK-032 — Alpaca Broker Connectivity & Real Data Pipeline

## Goal

Verify and fix the complete Alpaca integration end-to-end: WebSocket connection, bar streaming, universe filter, historical backfill, strategy evaluation against real data, and paper trading order execution through the Alpaca API. After this task, equities market data flows and paper trades execute through Alpaca's sandbox.

## Depends On

TASK-031

## Scope

**In scope:**
- Verify Alpaca WebSocket connects and authenticates with real API keys
- Verify universe filter runs and populates the watchlist
- Verify bar data streams, normalizes, and persists to database
- Verify historical backfill runs and populates OHLCV bars
- Verify health endpoint shows Alpaca connection status
- Verify Alpaca paper trading executor submits orders and receives fills
- Fix any errors encountered in the above steps
- Document the verified pipeline in a runbook section of README

**Out of scope:**
- OANDA / forex connectivity (TASK-033)
- Frontend changes
- New features
- Test creation

---

## Deliverables

### D1 — Verify Alpaca WebSocket connection

**Steps:**
1. Set `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env` with real Alpaca paper trading keys
2. Set `ALPACA_BASE_URL=https://paper-api.alpaca.markets`
3. Set `ALPACA_DATA_WS_URL=wss://stream.data.alpaca.markets/v2/sip` (or `v2/iex` for free tier)
4. Start backend
5. Check logs for WebSocket connection established, authentication success, subscription to symbols

**Expected log output:**
```
INFO  market_data.ws: Alpaca WebSocket connected
INFO  market_data.ws: Alpaca WebSocket authenticated
INFO  market_data.ws: Subscribed to N symbols
```

**If it fails:** Debug and fix. Common issues:
- Wrong WebSocket URL (SIP vs IEX endpoint)
- Authentication format wrong (Alpaca expects specific JSON auth message)
- SSL/TLS issues
- API key format issues (paper vs live keys)

Document what works and what was fixed.

### D2 — Verify universe filter

**Steps:**
1. With Alpaca keys configured, start backend
2. Check logs for universe filter execution
3. Query `GET /api/v1/market-data/watchlist` to see populated symbols
4. Verify symbols match filter criteria (min volume, min price, exchanges)

**Expected:** Watchlist populated with actively traded equities from NYSE/NASDAQ/AMEX matching the filter criteria in config.

**If it fails:** 
- Check if the Alpaca assets endpoint (`/v2/assets`) is being called correctly
- Check if filter criteria are too restrictive (lower `UNIVERSE_FILTER_EQUITIES_MIN_VOLUME` for testing)
- Check if the response format from Alpaca matches what the adapter expects

### D3 — Verify bar data streaming and storage

**Steps:**
1. After WebSocket connects and symbols are subscribed
2. Wait for market hours (or use extended hours if configured)
3. Check logs for bars received
4. Query `GET /api/v1/market-data/bars?symbol=AAPL&timeframe=1m&limit=5` to verify bars are persisted
5. Verify bar fields: open, high, low, close, volume are all present and Decimal

**If outside market hours:** Verify that:
- The WebSocket connection stays alive
- No bars are expected (market closed is normal)
- The stale data threshold doesn't trigger false alerts

**If it fails:**
- Check bar deserialization (Alpaca bar format → internal format)
- Check the async queue → DB writer pipeline
- Check for database errors on insert

### D4 — Verify historical backfill

**Steps:**
1. Check if backfill runs on startup for symbols in the watchlist
2. Query bars for a symbol to verify historical data exists
3. Verify backfill respects configured depth (`BACKFILL_1M_DAYS=30`, etc.)
4. Check rate limit handling (Alpaca limits API calls per minute)

**Expected:** After startup, symbols have historical bars at configured timeframes.

**If it fails:**
- Check Alpaca historical bars endpoint format
- Check rate limit handling (backoff/retry)
- Check date range calculations

### D5 — Verify health endpoint with broker status

**Steps:**
1. Query `GET /api/v1/health`
2. Verify response includes broker connectivity information

**Current state (from TASK-025):** Health check only verifies database. Broker status is not reported.

**Enhancement (if not already present):** Add broker connection status to health endpoint:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "brokers": {
    "alpaca": { "status": "connected", "subscribedSymbols": 150 },
    "oanda": { "status": "unconfigured" }
  }
}
```

If the health endpoint already reports broker status, document it.
If not, add broker status to the health response. This is a minor backend change — acceptable for this task.

### D6 — Verify Alpaca paper trading execution

**Steps:**
1. Create and enable a strategy with a simple condition (e.g., RSI < 30 on a liquid stock)
2. Either wait for real evaluation, or manually trigger evaluation for testing
3. When a signal is generated → verify it flows through risk → reaches paper trading
4. Verify the Alpaca paper executor submits the order to `https://paper-api.alpaca.markets/v2/orders`
5. Verify the fill returns and position appears in portfolio

**If manual triggering is needed:**
- Can insert a signal directly via DB or internal service call
- Set signal status to `risk_approved`
- Verify the approved signal watcher picks it up and routes to executor

**If it fails:**
- Check Alpaca order API request format
- Check authentication on the trading API (same keys as data)
- Check order response parsing
- Check fill callback/polling mechanism

### D7 — README runbook section

Add an "Operations Runbook" section to README.md:

```markdown
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
4. Restart the backend
5. Check health: `curl http://localhost:8000/api/v1/health`
6. Check watchlist: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/market-data/watchlist`

### Troubleshooting

- **No bars streaming:** Check if market is open (9:30 AM - 4:00 PM ET). Outside hours, no bars are expected.
- **WebSocket disconnects:** Check logs for reconnection attempts. The system auto-reconnects with exponential backoff.
- **Universe filter empty:** Lower `UNIVERSE_FILTER_EQUITIES_MIN_VOLUME` or check Alpaca API connectivity.
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Backend starts without errors when Alpaca API keys are configured |
| AC2 | Alpaca WebSocket connects and authenticates (visible in logs) |
| AC3 | Universe filter runs and populates watchlist with equity symbols |
| AC4 | Bar data streams from Alpaca and persists to database (or documented as market-hours-dependent) |
| AC5 | Historical backfill populates bars for watchlist symbols |
| AC6 | Health endpoint reports Alpaca connection status |
| AC7 | Alpaca paper trading executor can submit an order (or failure path documented with fix) |
| AC8 | README has Alpaca connectivity runbook section |
| AC9 | All fixes are documented in BUILDER_OUTPUT.md with before/after |
| AC10 | No frontend code modified |
| AC11 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

None expected — this is a verification task. New files only if health endpoint enhancement requires one.

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/main.py` or health route | Add broker status to health endpoint (if not present) |
| `.env.example` | Verify Alpaca variables have correct defaults and comments |
| `README.md` | Add Alpaca runbook section |
| Other backend files | Only if fixes needed (document in BUILDER_OUTPUT.md) |

## Builder Notes

- **You need real Alpaca paper trading API keys.** Check if they're in the `.env`. If not, the task cannot be completed — document what was verified without keys and what requires them.
- **Market hours matter.** If testing outside US market hours (9:30 AM - 4:00 PM ET), bar streaming won't produce data. This is expected behavior, not a bug. Document accordingly.
- **Free tier vs paid.** Free Alpaca accounts use the IEX feed (`v2/iex`), paid use SIP (`v2/sip`). The IEX feed has fewer symbols and delayed data. Both work for our purposes. Check which endpoint works with the configured keys.
- **This is primarily a verification task.** Most code already exists. Your job is to run it, see what happens, fix what breaks, and document the outcome.

## References

- market_data_module_spec.md §1 — Broker Abstraction
- market_data_module_spec.md §3 — WebSocket Manager
- market_data_module_spec.md §4 — Bar Storage
- market_data_module_spec.md §5 — Historical Backfill
- market_data_module_spec.md §6 — Health Monitoring
- paper_trading_module_spec.md §3 — Broker Paper Trading (Alpaca)
- cross_cutting_specs.md §8 — Startup Sequence
