"""Paper trading module startup and shutdown."""

import logging
from decimal import Decimal

from app.paper_trading.cash_manager import CashManager
from app.paper_trading.config import PaperTradingConfig
from app.paper_trading.consumer import OrderConsumer
from app.paper_trading.executors.simulated import SimulatedExecutor
from app.paper_trading.fill_simulation.engine import FillSimulationEngine
from app.paper_trading.fill_simulation.fees import FeeModel
from app.paper_trading.fill_simulation.slippage import SlippageModel
from app.paper_trading.service import PaperTradingService

logger = logging.getLogger(__name__)

_service: PaperTradingService | None = None
_consumer: OrderConsumer | None = None
_pool_manager = None


async def start_paper_trading() -> None:
    """Initialize paper trading module."""
    global _service, _consumer, _pool_manager

    config = PaperTradingConfig()

    # Create fill simulation components
    slippage_model = SlippageModel()
    fee_model = FeeModel()
    fill_engine = FillSimulationEngine(slippage_model, fee_model, config)

    # Create simulated executor (base for all modes)
    simulated_executor = SimulatedExecutor(fill_engine)

    # Create forex pool executor
    forex_pool_executor = None
    try:
        from app.paper_trading.forex_pool.pool_manager import ForexPoolManager
        from app.paper_trading.executors.forex_pool import ForexPoolExecutor

        _pool_manager = ForexPoolManager(
            pool_size=config.forex_account_pool_size,
            capital_per_account=config.forex_capital_per_account,
        )

        # Seed accounts if they don't exist
        from app.common.database import get_session_factory
        factory = get_session_factory()
        async with factory() as db:
            created = await _pool_manager.seed_accounts(db)
            await db.commit()
            if created > 0:
                logger.info("Seeded %d forex pool accounts", created)

        forex_pool_executor = ForexPoolExecutor(fill_engine, _pool_manager)
        logger.info("Forex pool executor initialized")
    except Exception as e:
        logger.warning("Forex pool executor not available: %s", e)

    # Create Alpaca paper executor
    alpaca_executor = None
    try:
        from app.common.config import get_settings
        settings = get_settings()
        if settings.alpaca_api_key and config.execution_mode_equities == "paper":
            from app.paper_trading.executors.alpaca_paper import AlpacaPaperExecutor
            alpaca_executor = AlpacaPaperExecutor(config, simulated_executor)
            logger.info("Alpaca paper executor initialized")
    except Exception as e:
        logger.warning("Alpaca paper executor not available: %s", e)

    # Create shadow tracker
    shadow_tracker = None
    try:
        from app.common.config import get_settings
        settings = get_settings()
        if settings.shadow_tracking_enabled:
            from app.paper_trading.shadow.tracker import ShadowTracker
            shadow_tracker = ShadowTracker(fill_engine, config)
            logger.info("Shadow tracker initialized")
    except Exception as e:
        logger.warning("Shadow tracker not available: %s", e)

    # Create cash manager
    cash_manager = CashManager(config)

    # Create service with all executors
    _service = PaperTradingService(
        config,
        simulated_executor,
        cash_manager,
        forex_pool_executor=forex_pool_executor,
        alpaca_executor=alpaca_executor,
        shadow_tracker=shadow_tracker,
        forex_pool_manager=_pool_manager,
    )

    # Create and start consumer
    _consumer = OrderConsumer(_service)
    await _consumer.start()

    logger.info("Paper trading module started")


async def stop_paper_trading() -> None:
    """Stop the order consumer."""
    global _consumer

    if _consumer:
        await _consumer.stop()
        _consumer = None

    logger.info("Paper trading module stopped")


def get_paper_trading_service() -> PaperTradingService:
    """Get the service singleton for inter-module use."""
    if _service is None:
        raise RuntimeError("Paper trading service not initialized. Call start_paper_trading() first.")
    return _service


def get_pool_manager():
    """Get the forex pool manager singleton."""
    return _pool_manager
