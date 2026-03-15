"""Bar processing queue — async consumer that batches writes and triggers aggregation."""

import asyncio
import logging
import time
from uuid import uuid4

from app.common.database import get_session_factory
from app.market_data.aggregation.engine import AggregationEngine
from app.market_data.config import MarketDataConfig
from app.market_data.models import OHLCVBar
from app.market_data.repository import OHLCVBarRepository

logger = logging.getLogger(__name__)

_bar_repo = OHLCVBarRepository()
_aggregation = AggregationEngine()


class BarProcessor:
    """Processes incoming bars from the WebSocket queue.

    Reads bars from the async queue, batches them, and writes
    to the database using OHLCVBarRepository.upsert_bars().
    Also triggers aggregation for completed timeframe windows.
    """

    def __init__(self, bar_queue: asyncio.Queue, config: MarketDataConfig):
        self._queue = bar_queue
        self._config = config
        self._batch: list[dict] = []
        self._last_flush: float = time.monotonic()
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the processing loop as an asyncio task."""
        self._running = True
        self._last_flush = time.monotonic()
        self._task = asyncio.create_task(self._process_loop())
        logger.info(
            "Bar processor started (batch_size=%d, interval=%ds)",
            self._config.bar_batch_write_size,
            self._config.bar_batch_write_interval,
        )

    async def stop(self) -> None:
        """Flush remaining batch and stop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Final flush
        if self._batch:
            factory = get_session_factory()
            async with factory() as db:
                try:
                    await self._flush_batch(db)
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.error("Final flush failed: %s", e)

        logger.info("Bar processor stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Read from queue with timeout to allow periodic flush
                try:
                    bar = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                    self._batch.append(bar)
                except asyncio.TimeoutError:
                    pass

                # Check flush conditions
                elapsed = time.monotonic() - self._last_flush
                should_flush = (
                    len(self._batch) >= self._config.bar_batch_write_size
                    or (self._batch and elapsed >= self._config.bar_batch_write_interval)
                )

                if should_flush and self._batch:
                    factory = get_session_factory()
                    async with factory() as db:
                        try:
                            await self._flush_batch(db)
                            await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error("Batch flush failed: %s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Bar processor error: %s", e)

    async def _flush_batch(self, db) -> None:
        """Write current batch to database and trigger aggregation."""
        if not self._batch:
            return

        # Convert bar dicts to OHLCVBar models
        bar_models = [
            OHLCVBar(
                id=uuid4(),
                symbol=b["symbol"],
                market=b["market"],
                timeframe=b["timeframe"],
                ts=b["ts"],
                open=b["open"],
                high=b["high"],
                low=b["low"],
                close=b["close"],
                volume=b["volume"],
                source=b.get("market", "stream"),
                is_aggregated=False,
            )
            for b in self._batch
        ]

        count = await _bar_repo.upsert_bars(db, bar_models)
        logger.debug("Flushed %d bars to database", count)

        # Check aggregation for each 1m bar
        for bar_dict in self._batch:
            if bar_dict["timeframe"] == "1m":
                await self._check_aggregation(db, bar_dict)

        self._batch.clear()
        self._last_flush = time.monotonic()

    async def _check_aggregation(self, db, bar: dict) -> None:
        """Check if a completed higher-timeframe window exists.

        After writing a 1m bar, check if any higher timeframe windows
        just completed. If so, trigger aggregation for that window.
        """
        ts = bar["ts"]
        symbol = bar["symbol"]

        for timeframe in _aggregation.get_required_timeframes():
            if _aggregation.is_window_complete(ts, timeframe):
                window_start = _aggregation.get_window_start(ts, timeframe)
                try:
                    await _aggregation.aggregate_window(db, symbol, timeframe, window_start)
                except Exception as e:
                    logger.error(
                        "Aggregation failed for %s %s at %s: %s",
                        symbol, timeframe, window_start, e,
                    )
