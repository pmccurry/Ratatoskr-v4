# TASK-036a — Fix Alpaca Universe Filter

## Goal

Fix the universe filter that fails with `Symbol 'assets' not found` on startup. This is blocking the entire data pipeline — no symbols → no WebSocket subscriptions → no market data → no strategy evaluation.

## Problem

On startup with real Alpaca API keys:
```
WARNING: Universe filter failed during startup: Symbol 'assets' not found
Market data module started: 0 symbols, 0 brokers
```

The Alpaca adapter's `list_available_symbols()` method is failing when trying to call the `/v2/assets` endpoint. The error "Symbol 'assets' not found" suggests the code is treating `"assets"` as a symbol lookup instead of calling the assets list endpoint.

## Investigation

1. Open `backend/app/market_data/adapters/alpaca.py`
2. Find the `list_available_symbols()` method (or equivalent — might be called `get_assets()`, `fetch_symbols()`, etc.)
3. Check how it constructs the API call to Alpaca's assets endpoint
4. The correct Alpaca REST endpoint is: `GET https://paper-api.alpaca.markets/v2/assets`
   - Headers: `APCA-API-KEY-ID: {key}`, `APCA-API-SECRET-KEY: {secret}`
   - Optional query param: `?status=active`
   - Returns: JSON array of asset objects

## Likely Root Causes

**Most likely:** The adapter is using a generic `get()` method that interprets the path segment as a symbol lookup rather than a REST endpoint path. For example:
```python
# WRONG — treats "assets" as a symbol parameter
result = await self.client.get("assets")  # routes to /v2/stocks/assets or similar

# RIGHT — calls the assets list endpoint directly
response = await httpx.get(f"{self.base_url}/v2/assets", headers=self.auth_headers)
```

**Other possibilities:**
- The base URL is being double-prefixed (e.g., `/v2/v2/assets`)
- The `alpaca-py` or `alpaca-trade-api` SDK method name is wrong
- The HTTP client is routing through a market data endpoint instead of the trading API endpoint

## Fix

Whatever the root cause, the fix must result in:
1. A successful `GET` to `https://paper-api.alpaca.markets/v2/assets?status=active`
2. The response parsed into a list of symbols with: symbol, name, exchange, tradable status
3. Filtered by the universe filter config (min volume, min price, exchanges)
4. Symbols added to the watchlist
5. WebSocket connections initiated for the watchlist symbols

## Verification

After the fix, restart the backend with real Alpaca keys and verify:

1. **Logs show:**
   - Universe filter ran successfully with N symbols
   - WebSocket connected and authenticated
   - Subscribed to symbols

2. **Health endpoint shows:**
   ```bash
   curl http://localhost:8000/api/v1/health | python -m json.tool
   ```
   - `brokers.alpaca.status: "connected"` (or similar)
   - `subscribedSymbols > 0`

3. **Watchlist populated:**
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/market-data/watchlist
   ```
   - Returns a non-empty list of equity symbols

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Universe filter runs without error on startup with real Alpaca keys |
| AC2 | Watchlist is populated with equity symbols after startup |
| AC3 | Alpaca WebSocket connects and authenticates after watchlist is populated |
| AC4 | Health endpoint shows Alpaca status as connected (not "not_started") |
| AC5 | The fix is documented with before/after in BUILDER_OUTPUT.md |
| AC6 | No frontend code modified |
| AC7 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/market_data/adapters/alpaca.py` | Fix the assets endpoint call |
| Possibly `backend/app/market_data/universe_filter.py` or equivalent | If the filter logic itself has the bug |

## Builder Notes

- **Real Alpaca keys are in `.env`.** Start the backend and verify the fix works with actual API responses.
- **Print the actual HTTP request** being made if needed — add a temporary `logger.info(f"Calling: {url}")` to see exactly what URL is being hit.
- **Alpaca has two base URLs:** Trading API (`paper-api.alpaca.markets`) for assets/orders, and Data API (`data.alpaca.markets`) for bars/quotes. The assets endpoint is on the **trading** API, not the data API.
- **Test with the actual startup flow** — don't just test the function in isolation. The bug manifests during the module startup sequence.
