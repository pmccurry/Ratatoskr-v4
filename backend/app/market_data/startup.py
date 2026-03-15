"""Market data module startup and shutdown sequence."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.config import get_market_data_config, MarketDataConfig
from app.market_data.repository import WatchlistRepository
from app.market_data.streams.health import HealthMonitor
from app.market_data.streams.manager import WebSocketManager
from app.market_data.streams.processor import BarProcessor

logger = logging.getLogger(__name__)

# Module-level references for shutdown access
_ws_manager: WebSocketManager | None = None
_bar_processor: BarProcessor | None = None
_health_monitor: HealthMonitor | None = None
_bar_queue: asyncio.Queue | None = None

_watchlist_repo = WatchlistRepository()


def get_ws_manager() -> WebSocketManager | None:
    """Return the active WebSocketManager instance (for adapter delegation)."""
    return _ws_manager


def get_health_monitor() -> HealthMonitor | None:
    """Return the active HealthMonitor instance (for health endpoint)."""
    return _health_monitor


async def start_market_data(db: AsyncSession) -> None:
    """Market data module startup sequence.

    Called from FastAPI lifespan on application start.

    Steps:
    1. Load market data config
    2. Run universe filter (update watchlist)
    3. Get active watchlist symbols (grouped by broker)
    4. Check for backfill needs (new symbols, gaps)
    5. Run initial backfill if needed
    6. Create the bar processing queue
    7. Start the bar processor
    8. Start the WebSocket manager (connect to brokers, subscribe to symbols)
    9. Start the health monitor
    10. Log startup complete with symbol counts
    """
    global _ws_manager, _bar_processor, _health_monitor, _bar_queue

    config = get_market_data_config()

    # Step 1-2: Run universe filter
    try:
        from app.market_data.universe.filter import run_universe_filter
        filter_result = await run_universe_filter(db)
        logger.info("Universe filter complete: %s", filter_result)
    except Exception as e:
        logger.warning("Universe filter failed during startup: %s", e)

    # Step 3: Get active watchlist grouped by broker
    watchlist = await _watchlist_repo.get_active(db)
    broker_symbols: dict[str, list[str]] = {}
    for entry in watchlist:
        broker = "alpaca" if entry.market == "equities" else "oanda"
        broker_symbols.setdefault(broker, []).append(entry.symbol)

    total_symbols = sum(len(s) for s in broker_symbols.values())
    logger.info(
        "Watchlist loaded: %d total symbols (%s)",
        total_symbols,
        {b: len(s) for b, s in broker_symbols.items()},
    )

    # Step 4-5: Run initial backfill if needed
    try:
        from app.market_data.backfill.runner import run_backfill
        backfill_result = await run_backfill(db)
        logger.info("Initial backfill complete: %s", backfill_result)
    except Exception as e:
        logger.warning("Initial backfill failed during startup: %s", e)

    # Step 6: Create bar processing queue
    _bar_queue = asyncio.Queue(maxsize=config.ws_bar_queue_max_size)

    # Step 7: Start bar processor
    _bar_processor = BarProcessor(_bar_queue, config)
    await _bar_processor.start()

    # Step 8: Start WebSocket manager
    _ws_manager = WebSocketManager(_bar_queue, config)
    for broker, symbols in broker_symbols.items():
        try:
            await _ws_manager.start(broker, symbols)
        except Exception as e:
            logger.warning("WebSocket start failed for %s: %s", broker, e)

    # Step 9: Start health monitor
    _health_monitor = HealthMonitor(_ws_manager, _bar_queue, config)
    await _health_monitor.start()

    # Step 10: Done
    logger.info(
        "Market data module started: %d symbols, %d brokers",
        total_symbols,
        len(broker_symbols),
    )


async def stop_market_data() -> None:
    """Graceful shutdown of market data module.

    Steps:
    1. Stop health monitor
    2. Stop WebSocket manager (close all connections)
    3. Stop bar processor (flush remaining batch)
    4. Log shutdown complete
    """
    global _ws_manager, _bar_processor, _health_monitor, _bar_queue

    if _health_monitor:
        await _health_monitor.stop()
        _health_monitor = None

    if _ws_manager:
        await _ws_manager.stop()
        _ws_manager = None

    if _bar_processor:
        await _bar_processor.stop()
        _bar_processor = None

    _bar_queue = None

    logger.info("Market data module stopped")
