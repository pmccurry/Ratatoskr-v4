"""Backfill runner — orchestrates historical bar fetching."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.adapters.alpaca import AlpacaAdapter
from app.market_data.adapters.oanda import OandaAdapter
from app.market_data.backfill.rate_limiter import RateLimiter
from app.market_data.config import get_market_data_config
from app.market_data.models import BackfillJob, OHLCVBar
from app.market_data.repository import (
    BackfillJobRepository,
    OHLCVBarRepository,
    WatchlistRepository,
)

logger = logging.getLogger(__name__)

_backfill_repo = BackfillJobRepository()
_bar_repo = OHLCVBarRepository()
_watchlist_repo = WatchlistRepository()

# Timeframes to backfill and their config key for lookback days
_TIMEFRAME_CONFIGS = {
    "1m": "backfill_1m_days",
    "1h": "backfill_1h_days",
    "4h": "backfill_4h_days",
    "1d": "backfill_1d_days",
}


def _get_adapter(market: str, rate_limiter: RateLimiter):
    """Get the appropriate adapter for a market."""
    if market == "equities":
        return AlpacaAdapter(rate_limiter=rate_limiter)
    elif market == "forex":
        return OandaAdapter(rate_limiter=rate_limiter)
    raise ValueError(f"Unknown market: {market}")


async def needs_backfill(
    db: AsyncSession, symbol: str, timeframe: str
) -> bool:
    """Check if a symbol/timeframe needs backfill."""
    cfg = get_market_data_config()
    config_key = _TIMEFRAME_CONFIGS.get(timeframe)
    if not config_key:
        return False

    lookback_days = getattr(cfg, config_key)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    latest_ts = await _bar_repo.get_latest_timestamp(db, symbol, timeframe)
    if latest_ts is None:
        return True  # No data at all

    # Check if latest bar is older than expected
    # For 1m bars, expect data within the last day (during market hours)
    # For daily bars, within the last week
    staleness_map = {"1m": 2, "1h": 7, "4h": 14, "1d": 7}
    max_staleness_days = staleness_map.get(timeframe, 7)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=max_staleness_days)
    if latest_ts < stale_cutoff:
        return True

    # Check for retryable failed jobs
    job = await _backfill_repo.get_by_symbol(db, symbol, timeframe)
    if job and job.status == "failed" and job.retry_count < cfg.backfill_max_retries:
        return True

    return False


async def run_backfill(
    db: AsyncSession,
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None,
    force: bool = False,
) -> dict:
    """Run historical backfill.

    For each symbol/timeframe, fetch bars from the appropriate adapter
    and upsert into the database.
    """
    cfg = get_market_data_config()

    # Determine symbols to backfill
    if symbols is None:
        watchlist = await _watchlist_repo.get_active(db)
        symbol_market_map = {e.symbol: e.market for e in watchlist}
    else:
        # Look up market for each symbol
        symbol_market_map = {}
        for sym in symbols:
            entry = await _watchlist_repo.get_by_symbol(db, sym)
            if entry:
                symbol_market_map[sym] = entry.market

    if timeframes is None:
        timeframes = list(_TIMEFRAME_CONFIGS.keys())

    # Create rate limiters per broker
    alpaca_limiter = RateLimiter(max_requests_per_minute=180)
    oanda_limiter = RateLimiter(max_requests_per_minute=5000)

    total_bars = 0
    completed = 0
    failed = 0

    # Use separate DB sessions per symbol/timeframe to prevent one failure
    # from poisoning the session for subsequent backfills
    from app.common.database import get_session_factory
    session_factory = get_session_factory()

    for symbol, market in symbol_market_map.items():
        for timeframe in timeframes:
            config_key = _TIMEFRAME_CONFIGS.get(timeframe)
            if not config_key:
                continue

            # Check if backfill needed (unless forced)
            if not force and not await needs_backfill(db, symbol, timeframe):
                continue

            lookback_days = getattr(cfg, config_key)
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=lookback_days)

            try:
                async with session_factory() as backfill_db:
                    # Create job record
                    job = BackfillJob(
                        id=uuid4(),
                        symbol=symbol,
                        market=market,
                        timeframe=timeframe,
                        start_date=start,
                        end_date=end,
                        status="running",
                        started_at=datetime.now(timezone.utc),
                    )
                    await _backfill_repo.create(backfill_db, job)
                    await backfill_db.commit()

                    job_id = job.id  # Capture ID before any session issues

                    try:
                        limiter = alpaca_limiter if market == "equities" else oanda_limiter
                        adapter = _get_adapter(market, limiter)

                        bars_data = await adapter.fetch_historical_bars(
                            symbol=symbol,
                            timeframe=timeframe,
                            start=start,
                            end=end,
                        )

                        bar_models = [
                            OHLCVBar(
                                id=uuid4(),
                                symbol=b["symbol"],
                                market=market,
                                timeframe=b["timeframe"],
                                ts=b["ts"],
                                open=b["open"],
                                high=b["high"],
                                low=b["low"],
                                close=b["close"],
                                volume=b["volume"],
                                source="alpaca" if market == "equities" else "oanda",
                                is_aggregated=False,
                            )
                            for b in bars_data
                        ]

                        # Batch upsert to avoid huge single INSERT statements
                        _BATCH_SIZE = 1000
                        count = 0
                        for i in range(0, len(bar_models), _BATCH_SIZE):
                            batch = bar_models[i:i + _BATCH_SIZE]
                            count += await _bar_repo.upsert_bars(backfill_db, batch)
                        total_bars += count

                        # Use raw UPDATE to avoid greenlet_spawn on expired ORM object
                        from sqlalchemy import update
                        await backfill_db.execute(
                            update(BackfillJob)
                            .where(BackfillJob.id == job_id)
                            .values(
                                status="completed",
                                bars_fetched=count,
                                completed_at=datetime.now(timezone.utc),
                            )
                        )
                        await backfill_db.commit()
                        completed += 1

                        logger.info(
                            "Backfill complete: %s %s — %d bars", symbol, timeframe, count
                        )

                    except Exception as e:
                        await backfill_db.rollback()
                        # Use raw UPDATE to avoid greenlet_spawn on expired ORM object
                        try:
                            from sqlalchemy import update
                            await backfill_db.execute(
                                update(BackfillJob)
                                .where(BackfillJob.id == job_id)
                                .values(
                                    status="failed",
                                    error_message=str(e)[:1000],
                                    retry_count=BackfillJob.retry_count + 1,
                                )
                            )
                            await backfill_db.commit()
                        except Exception:
                            pass  # Job status update failed — not critical
                        failed += 1
                        logger.warning("Backfill failed for %s %s: %s", symbol, timeframe, e)

            except Exception as e:
                failed += 1
                logger.error("Backfill session error for %s %s: %s", symbol, timeframe, e)

    result = {
        "total_symbols": len(symbol_market_map),
        "total_bars": total_bars,
        "completed": completed,
        "failed": failed,
    }
    logger.info("Backfill run complete: %s", result)
    return result


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
    entry = await _watchlist_repo.get_by_symbol(db, symbol)
    if not entry:
        logger.warning("Gap backfill skipped: %s not on watchlist", symbol)
        return 0

    market = entry.market
    limiter = RateLimiter(max_requests_per_minute=180 if market == "equities" else 5000)
    adapter = _get_adapter(market, limiter)

    bars_data = await adapter.fetch_historical_bars(
        symbol=symbol, timeframe=timeframe, start=gap_start, end=gap_end
    )

    bar_models = [
        OHLCVBar(
            id=uuid4(),
            symbol=b["symbol"],
            market=market,
            timeframe=b["timeframe"],
            ts=b["ts"],
            open=b["open"],
            high=b["high"],
            low=b["low"],
            close=b["close"],
            volume=b["volume"],
            source="alpaca" if market == "equities" else "oanda",
            is_aggregated=False,
        )
        for b in bars_data
    ]

    count = await _bar_repo.upsert_bars(db, bar_models)
    logger.info("Gap backfill: %s %s [%s → %s] — %d bars", symbol, timeframe, gap_start, gap_end, count)
    return count
