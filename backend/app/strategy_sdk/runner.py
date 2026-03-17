"""Python strategy runner — executes strategies against live bar data."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pandas as pd

from .base import Strategy
from .signal import StrategySignal
from .registry import get_strategy_instance, list_strategies

logger = logging.getLogger(__name__)


class PythonStrategyRunner:
    """
    Runs Python-based strategies against live bar data.

    Integrates with the existing signal pipeline:
    Python Strategy -> StrategySignal -> signal_service.create_signal() -> risk -> orders
    """

    def __init__(self):
        self._running_strategies: dict[str, bool] = {}  # name -> running


    async def start_strategy(self, name: str, db_session_factory=None):
        """Start a Python strategy for live paper trading."""
        instance = get_strategy_instance(name)
        if instance is None:
            raise ValueError(f"Strategy not found: {name}")

        if self._running_strategies.get(name):
            logger.warning("Strategy %s is already running", name)
            return

        self._running_strategies[name] = True
        instance.on_start()

        logger.info("Started Python strategy: %s", name)

        # The actual bar-by-bar execution is driven by the market data
        # stream. When a new bar arrives for a symbol this strategy
        # watches, the on_new_bar() method is called.

    async def stop_strategy(self, name: str):
        """Stop a running Python strategy."""
        instance = get_strategy_instance(name)
        if instance:
            instance.on_stop()
        self._running_strategies[name] = False
        logger.info("Stopped Python strategy: %s", name)

    async def on_new_bar(self, symbol: str, bar: dict, history_df: pd.DataFrame):
        """
        Called by the market data stream when a new bar is available.

        Iterates through all running Python strategies that watch this symbol
        and calls their on_bar() method.
        """
        for name, running in self._running_strategies.items():
            if not running:
                continue

            instance = get_strategy_instance(name)
            if instance is None or symbol not in instance.symbols:
                continue

            try:
                # Update runtime state
                instance.positions = await self._get_positions(instance, symbol)
                instance.equity = await self._get_equity()
                instance.cash = await self._get_cash()

                # Execute strategy
                signals = instance.on_bar(symbol, bar, history_df)

                if not signals:
                    continue

                # Process each signal through the existing pipeline
                for signal in signals:
                    await self._process_signal(signal, instance)

            except Exception as e:
                logger.error("Strategy %s error on %s: %s", name, symbol, e, exc_info=True)

    async def _process_signal(self, signal: StrategySignal, strategy: Strategy):
        """
        Convert a StrategySignal to the platform's internal format
        and submit it to the signal service.

        Uses the session factory pattern to obtain a db session,
        similar to how the alert engine gets sessions.
        """
        from app.common.database import get_session_factory
        from app.signals.startup import get_signal_service

        # Map direction to side: "long" -> "buy", "short" -> "sell"
        side = "buy" if signal.direction == "long" else "sell"

        # Map action to signal_type: entry signals for new positions
        signal_type = "entry"

        ts = signal.timestamp or datetime.now(timezone.utc)

        # Build the internal signal dict matching what the signal service expects.
        # See SignalService.create_signal() — it expects a dict with these keys:
        # strategy_id, strategy_version, symbol, market, timeframe, side,
        # signal_type, source, confidence, payload_json, position_id, exit_reason, ts
        signal_data = {
            "strategy_id": None,       # Python strategies don't have a DB strategy record yet
            "strategy_version": 1,
            "symbol": signal.symbol,
            "market": strategy.market,
            "timeframe": strategy.timeframe,
            "side": side,
            "signal_type": signal_type,
            "source": "strategy",
            "confidence": Decimal(str(signal.confidence)) if signal.confidence else None,
            "ts": ts,
            "payload_json": {
                "strategy_name": signal.strategy_name,
                "strategy_type": "python",
                "entry_price": str(signal.entry_price),
                "stop_loss": str(signal.stop_loss) if signal.stop_loss else None,
                "take_profit": str(signal.take_profit) if signal.take_profit else None,
                "quantity": str(signal.quantity) if signal.quantity else None,
                "score": signal.score,
                "metadata": signal.metadata,
            },
        }

        try:
            signal_service = get_signal_service()
            factory = get_session_factory()
            async with factory() as db:
                result = await signal_service.create_signal(db, signal_data)
                await db.commit()
                if result:
                    logger.info(
                        "Signal submitted: %s %s @ %s (from %s)",
                        signal.direction, signal.symbol,
                        signal.entry_price, signal.strategy_name,
                    )
                else:
                    logger.debug(
                        "Signal not created (validation/dedup): %s %s (from %s)",
                        signal.direction, signal.symbol, signal.strategy_name,
                    )
        except Exception as e:
            logger.error("Failed to submit signal from %s: %s", signal.strategy_name, e)

    async def _get_positions(self, strategy: Strategy, symbol: str) -> dict:
        """Get current positions for the strategy's symbols."""
        # TODO: Wire up to portfolio service when market data integration is done.
        # For now, return empty positions dict.
        return {}

    async def _get_equity(self) -> Decimal:
        """Get current account equity."""
        # TODO: Wire up to portfolio service when market data integration is done.
        return Decimal("0")

    async def _get_cash(self) -> Decimal:
        """Get current available cash."""
        # TODO: Wire up to portfolio service when market data integration is done.
        return Decimal("0")

    def get_status(self) -> list[dict]:
        """Get status of all Python strategies."""
        result = []
        for name, running in self._running_strategies.items():
            instance = get_strategy_instance(name)
            result.append({
                "name": name,
                "running": running,
                "symbols": instance.symbols if instance else [],
                "timeframe": instance.timeframe if instance else "",
                "positions": instance.position_count() if instance else 0,
            })
        return result


# Singleton
_runner: Optional[PythonStrategyRunner] = None


def get_python_runner() -> PythonStrategyRunner:
    """Get the singleton PythonStrategyRunner instance."""
    global _runner
    if _runner is None:
        _runner = PythonStrategyRunner()
    return _runner
