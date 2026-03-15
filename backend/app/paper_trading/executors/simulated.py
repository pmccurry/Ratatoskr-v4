"""Simulated executor — internal fill simulation."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from app.paper_trading.executors.base import Executor, FillResult, OrderResult

if TYPE_CHECKING:
    from app.paper_trading.fill_simulation.engine import FillSimulationEngine
    from app.paper_trading.models import PaperOrder


class SimulatedExecutor(Executor):
    """Internal fill simulation executor.

    Used for: forex paper trading, backtesting, offline testing,
    and as fallback when broker APIs are unavailable.

    Processing is synchronous (within an async call) — fills happen
    immediately since there's no broker to wait for.
    """

    @property
    def execution_mode(self) -> str:
        return "simulation"

    def __init__(self, fill_engine: FillSimulationEngine):
        self._fill_engine = fill_engine

    async def submit_order(
        self, order: PaperOrder, reference_price: Decimal
    ) -> OrderResult:
        """Accept the order immediately (simulation has no queue)."""
        return OrderResult(success=True, status="accepted")

    async def simulate_fill(
        self, order: PaperOrder, reference_price: Decimal
    ) -> FillResult:
        """Calculate fill using the fill simulation engine."""
        return await self._fill_engine.simulate(order, reference_price)

    async def cancel_order(self, order: PaperOrder) -> bool:
        """Cancel is always successful in simulation (no broker state)."""
        return True
