# TASK-036b — Fix OANDA Backfill Count Limit & DB Transaction Cascade

## Goal

Fix two related bugs discovered during first live OANDA connectivity: backfill requests exceed OANDA's 5,000 candle limit, and the resulting API error cascades into a failed DB transaction that breaks subsequent queries.

## Problem

On startup with real OANDA credentials:
1. OANDA connects and streams successfully (10 forex pairs)
2. Historical backfill triggers and requests too many candles in one API call
3. OANDA returns an error (count exceeds 5,000 limit)
4. The error occurs inside a DB transaction, putting the SQLAlchemy session into a failed state
5. All subsequent DB operations on that session fail with `InFailedSQLTransactionError`

## Fixes

### Fix 1 — Cap OANDA backfill request to 5,000 candles per call

**File:** `backend/app/market_data/adapters/oanda.py` (in `fetch_historical_bars()` or equivalent)

OANDA's `/v3/instruments/{pair}/candles` endpoint accepts a `count` parameter with a max of 5,000. The backfill must paginate:

```python
MAX_CANDLES_PER_REQUEST = 5000

async def fetch_historical_bars(self, symbol, timeframe, start, end):
    bars = []
    current_start = start
    
    while current_start < end:
        params = {
            "granularity": self._map_timeframe(timeframe),
            "from": current_start.isoformat(),
            "to": end.isoformat(),
            "count": MAX_CANDLES_PER_REQUEST,
            "price": "M",
        }
        
        response = await self._request("GET", f"/v3/instruments/{symbol}/candles", params=params)
        candles = response.get("candles", [])
        
        if not candles:
            break
            
        bars.extend(self._parse_candles(candles))
        
        # Move start to after the last candle
        last_time = candles[-1]["time"]
        current_start = parse_datetime(last_time) + timedelta(seconds=1)
        
        # If we got fewer than max, we've reached the end
        if len(candles) < MAX_CANDLES_PER_REQUEST:
            break
    
    return bars
```

**Key:** Don't pass both `from`/`to` AND `count` in a way that exceeds 5,000. Either use `count` alone with pagination, or ensure the date range never spans more than 5,000 bars.

### Fix 2 — Isolate backfill DB transactions

**File:** `backend/app/market_data/backfill.py` (or wherever backfill writes bars to DB)

The backfill should catch API/DB errors per-symbol without poisoning the session for other operations:

```python
async def run_backfill(self, symbols, timeframes):
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                async with self._get_session() as db:
                    bars = await self._adapter.fetch_historical_bars(symbol, timeframe, start, end)
                    await self._bar_repo.batch_insert(db, bars)
                    await db.commit()
            except Exception as e:
                logger.warning(f"Backfill failed for {symbol}/{timeframe}: {e}")
                # Continue with next symbol — don't let one failure block all backfills
                continue
```

**Key points:**
- Each symbol/timeframe backfill gets its own DB session
- If one fails, the error is logged and the next symbol proceeds
- The failed session is discarded (not reused in a broken state)
- Never let a backfill error propagate up and crash the startup sequence

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | OANDA backfill requests never exceed 5,000 candles per API call |
| AC2 | Backfill paginates correctly when date range spans more than 5,000 candles |
| AC3 | A failed backfill for one symbol does not prevent backfill of other symbols |
| AC4 | A failed backfill does not put the DB session into a failed state for other operations |
| AC5 | OANDA startup completes successfully (streaming + backfill) with real credentials |
| AC6 | No frontend code modified |
| AC7 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/market_data/adapters/oanda.py` | Cap candle count to 5,000, paginate |
| `backend/app/market_data/backfill.py` (or equivalent) | Per-symbol session isolation, error recovery |

## Builder Notes

- **Real OANDA credentials are in `.env`.** Start the backend and verify the backfill completes without errors.
- **Check the Alpaca adapter too.** Alpaca has its own pagination (via `next_page_token`). Verify it doesn't have a similar count limit issue. If it does, fix it the same way.
- **The backfill runs on startup.** After the fix, the startup sequence should complete with: universe filter → watchlist → backfill (per symbol, with error isolation) → WebSocket connect → streaming.
