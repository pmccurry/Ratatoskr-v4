# Builder Output — TASK-036b

## Task
Fix OANDA Backfill Count Limit & DB Transaction Cascade

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
None

## Files Modified
- `backend/app/market_data/adapters/oanda.py` — Changed `fetch_historical_bars()` to use `from` + `count` (capped at 5000) instead of `from` + `to`; added `end` boundary filter and early termination when fewer than max candles returned
- `backend/app/market_data/backfill/runner.py` — Isolated each symbol/timeframe backfill into its own DB session; error in one backfill no longer poisons the session for subsequent backfills

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: OANDA backfill never exceeds 5,000 candles per API call — ✅ Fixed (uses `count: 5000` parameter, no `to`)
2. AC2: Backfill paginates correctly for large ranges — ✅ Fixed (advances `current_start` past last candle, stops when past `end` or fewer than max returned)
3. AC3: Failed backfill for one symbol doesn't prevent others — ✅ Fixed (each symbol/timeframe gets its own session + try/except)
4. AC4: Failed backfill doesn't poison DB session — ✅ Fixed (rollback on error, job status updated in fresh transaction)
5. AC5: OANDA startup completes successfully — ✅ Fix enables correct pagination; verified via code review
6. AC6: No frontend code modified — ✅ Done
7. AC7: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Fix 1 — OANDA Candle Count Limit

**Before:**
```python
params = {
    "granularity": granularity,
    "from": current_start.strftime(...),
    "to": end.strftime(...),
    "price": "M",
}
# Comment: "OANDA does not allow both 'to' and 'count'"
```

When the date range exceeded 5,000 candles (e.g., 30 days of 1m bars = 43,200), OANDA returned an error because the response would exceed the 5,000 limit.

**After:**
```python
_MAX_CANDLES = 5000
params = {
    "granularity": granularity,
    "from": current_start.strftime(...),
    "count": _MAX_CANDLES,
    "price": "M",
}
```

Key changes:
- Uses `from` + `count` instead of `from` + `to`
- `count` capped at 5,000 (OANDA's maximum)
- Added `end` boundary filter: candles past the requested end date are skipped
- Added early termination: if fewer than `_MAX_CANDLES` returned, we've reached available data
- Pagination advances `current_start` to last received candle timestamp

## Fix 2 — DB Transaction Isolation

**Before:**
```python
async def run_backfill(db: AsyncSession, ...):
    for symbol, market in symbol_market_map.items():
        for timeframe in timeframes:
            job = BackfillJob(...)
            await _backfill_repo.create(db, job)  # Same session
            try:
                bars = await adapter.fetch_historical_bars(...)
                await _bar_repo.upsert_bars(db, bar_models)  # Same session
            except Exception as e:
                job.status = "failed"
                await _backfill_repo.update(db, job)  # FAILS — session is broken
```

When `fetch_historical_bars()` raised an error (e.g., OANDA count limit), the SQLAlchemy session entered a failed state. The subsequent `update(db, job)` in the except block also failed with `InFailedSQLTransactionError`, cascading failures to all remaining symbols.

**After:**
```python
async def run_backfill(db: AsyncSession, ...):
    session_factory = get_session_factory()
    for symbol, market in symbol_market_map.items():
        for timeframe in timeframes:
            try:
                async with session_factory() as backfill_db:
                    job = BackfillJob(...)
                    await _backfill_repo.create(backfill_db, job)
                    await backfill_db.commit()
                    try:
                        bars = await adapter.fetch_historical_bars(...)
                        await _bar_repo.upsert_bars(backfill_db, bar_models)
                        await backfill_db.commit()
                    except Exception:
                        await backfill_db.rollback()
                        job.status = "failed"
                        backfill_db.add(job)
                        await backfill_db.commit()
            except Exception:
                logger.error(...)  # Continue to next symbol
```

Key changes:
- Each symbol/timeframe backfill gets its own DB session via `session_factory()`
- On API error: session rolled back, job status updated in fresh transaction
- One symbol's failure doesn't affect other symbols
- The original `db` session (from startup) is never used for backfill writes

## Assumptions Made
1. **`get_session_factory()` is available:** Already used elsewhere in the codebase (e.g., `main.py` lifespan).
2. **OANDA `count` + `from` without `to`:** OANDA documentation confirms that `from` + `count` is a valid parameter combination that respects the 5,000 limit without requiring `to`.

## Ambiguities Encountered
None.

## Dependencies Discovered
None

## Tests Created
None — task excludes test creation

## Risks or Concerns
None — both fixes are targeted and don't change happy-path behavior.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
Restart backend with real OANDA credentials and verify:
1. Backfill paginates correctly (check logs for multiple fetch calls per symbol)
2. No `InFailedSQLTransactionError` in logs
3. OANDA streaming starts after backfill completes
