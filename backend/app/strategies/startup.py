"""Strategy module startup — runner and safety monitor lifecycle."""

import logging

from app.strategies.conditions.engine import ConditionEngine
from app.strategies.config import get_strategy_config
from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators import get_registry
from app.strategies.runner import StrategyRunner
from app.strategies.safety_monitor import SafetyMonitor

logger = logging.getLogger(__name__)

_runner: StrategyRunner | None = None
_safety_monitor: SafetyMonitor | None = None


async def start_strategies() -> None:
    """Start the strategy runner and safety monitor."""
    global _runner, _safety_monitor

    config = get_strategy_config()
    registry = get_registry()
    parser = FormulaParser(registry)
    engine = ConditionEngine(registry, parser)

    _runner = StrategyRunner(config, engine)
    _safety_monitor = SafetyMonitor(config)

    await _runner.start()
    await _safety_monitor.start()

    logger.info("Strategy module started (runner + safety monitor)")


async def stop_strategies() -> None:
    """Stop the runner and safety monitor."""
    global _runner, _safety_monitor

    if _runner:
        await _runner.stop()
    if _safety_monitor:
        await _safety_monitor.stop()

    logger.info("Strategy module stopped")


def get_runner() -> StrategyRunner | None:
    return _runner


def get_safety_monitor() -> SafetyMonitor | None:
    return _safety_monitor
