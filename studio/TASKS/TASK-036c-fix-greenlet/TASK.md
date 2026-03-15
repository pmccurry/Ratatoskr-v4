# TASK-036c — Fix Greenlet Spawn Error in Paginated Backfill

## Goal

Fix the `greenlet_spawn has not been called; can't call await_only() here` error that occurs during 1m and 1h OANDA backfill. The 4h and 1d backfills work because they need fewer pages. The bug only manifests during multi-page pagination.

## Problem

```
greenlet_spawn has not been called; can't call await_only() here.
Was IO attempted in an unexpected place?
```

This hits every pair on 1m and 1h timeframes (20 failures out of 40 jobs). The 4h and 1d backfills (which need 1-2 pages) succeed.

## Root Cause Analysis

This is a SQLAlchemy async/sync context mismatch. Somewhere in the backfill pagination loop, a synchronous database operation is being called from inside an async context. Common causes:

1. **Lazy-loaded relationship access** — Accessing `job.some_relationship` without `await` triggers a sync load
2. **Implicit session flush** — Adding objects to the session triggers an auto-flush before a query
3. **Synchronous `session.execute()`** — Using `db.execute()` instead of `await db.execute()`
4. **Model attribute access after commit** — Accessing expired attributes after `commit()` triggers a sync reload
5. **`session.refresh()` without await** — Forgetting `await` on `session.refresh(obj)`

The bug manifests on multi-page backfills because the second+ page iteration re-enters the session after the first page's commit/write.

## Investigation Steps

1. Open `backend/app/market_data/backfill/runner.py`
2. Find the pagination loop inside `run_backfill()` (the per-symbol/timeframe block)
3. Look for any of these patterns inside or after the pagination loop:
   - `job.status = ...` followed by `db.commit()` (accessing `job` after commit may trigger lazy reload)
   - `db.execute(...)` without `await`
   - `session.add(...)` followed by attribute access on the added object
   - Any model relationship traversal (e.g., `job.bars`, `bar.symbol_info`)
4. Also check `backend/app/market_data/adapters/oanda.py` `fetch_historical_bars()` — ensure no DB access happens inside the fetch loop

## Fix

The most likely fix is one of:

**A) Add `expire_on_commit=False` to the backfill session:**
```python
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```
This prevents SQLAlchemy from expiring object attributes after commit, which avoids the sync reload trap.

**B) Avoid accessing committed objects:**
```python
# Instead of:
await db.commit()
job.status = "completed"  # This may trigger sync reload of job
await db.commit()

# Do:
await db.execute(
    update(BackfillJob).where(BackfillJob.id == job_id).values(status="completed")
)
await db.commit()
```

**C) Use `await db.refresh(job)` before accessing attributes after commit:**
```python
await db.commit()
await db.refresh(job)  # Explicitly async-reload
job.status = "completed"
```

**D) Ensure the bar upsert uses `await` throughout:**
```python
# Check _bar_repo.upsert_bars() and batch_insert() use await on all execute() calls
```

## Verification

After the fix, restart the backend and verify:
1. All 4 timeframes backfill successfully for all 10 OANDA pairs (40/40 jobs)
2. No `greenlet_spawn` errors in logs
3. 1m bars: ~30 days × 24h × 60m = ~43,200 per pair (paginated across ~9 pages)
4. 1h bars: ~365 days × 24h = ~8,760 per pair (paginated across ~2 pages)

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | 1m backfill completes for all OANDA pairs without greenlet_spawn error |
| AC2 | 1h backfill completes for all OANDA pairs without greenlet_spawn error |
| AC3 | 4h and 1d backfills continue to work (no regression) |
| AC4 | Fix documented with root cause and before/after in BUILDER_OUTPUT.md |
| AC5 | No frontend code modified |
| AC6 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/market_data/backfill/runner.py` | Fix async/sync context issue in pagination loop |
| Possibly `backend/app/market_data/bar_storage.py` or `bar_repo` | If the upsert has sync calls |

## Builder Notes

- **The key diagnostic:** The bug only happens on multi-page backfills (1m, 1h) and not single-page (4h, 1d). This means the issue is in the second iteration of the pagination loop or in the bar write after fetching multiple pages.
- **Add logging:** Temporarily add `logger.debug(f"Page {page_num}: fetched {len(candles)} candles for {symbol}/{timeframe}")` in the pagination loop to see exactly which page/step triggers the error.
- **`expire_on_commit=False`** is the most common fix for this class of bug in SQLAlchemy async. Try it first.
