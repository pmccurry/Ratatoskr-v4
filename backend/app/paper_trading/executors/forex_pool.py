"""Forex pool executor — routes forex orders through the account pool."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from app.paper_trading.executors.base import Executor, FillResult, OrderResult

if TYPE_CHECKING:
    from app.paper_trading.fill_simulation.engine import FillSimulationEngine
    from app.paper_trading.forex_pool.pool_manager import ForexPoolManager
    from app.paper_trading.models import PaperOrder
    from sqlalchemy.ext.asyncio import AsyncSession


class ForexPoolExecutor(Executor):
    """Executor for forex orders that routes through the account pool.

    Wraps the SimulatedExecutor (same fill simulation) but adds
    pool allocation before execution and pool release on position close.
    """

    @property
    def execution_mode(self) -> str:
        return "simulation"

    def __init__(
        self,
        fill_engine: FillSimulationEngine,
        pool_manager: ForexPoolManager,
    ):
        self._fill_engine = fill_engine
        self._pool = pool_manager

    async def submit_order(
        self, order: PaperOrder, reference_price: Decimal, db: AsyncSession | None = None
    ) -> OrderResult:
        """Submit a forex order with pool allocation.

        1. Find available account for this pair
        2. If none available: reject with "no_available_account"
        3. If available: allocate and accept
        """
        if db is None:
            # No db session, can't check pool — reject
            return OrderResult(
                success=False,
                rejection_reason="no_db_session_for_pool",
            )

        # For exit orders, skip pool allocation (account already allocated)
        if order.signal_type in ("exit", "scale_out"):
            return OrderResult(success=True, status="accepted")

        account = await self._pool.find_available_account(db, order.symbol)
        if account is None:
            return OrderResult(
                success=False,
                rejection_reason="no_available_account",
            )

        # Allocate the account
        await self._pool.allocate(
            db,
            account_id=account.id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=order.side,
        )

        # Set broker_account_id on the order
        order.broker_account_id = account.account_id

        return OrderResult(success=True, status="accepted")

    async def simulate_fill(
        self, order: PaperOrder, reference_price: Decimal
    ) -> FillResult:
        """Calculate fill using same engine as simulated executor."""
        return await self._fill_engine.simulate(order, reference_price)

    async def cancel_order(self, order: PaperOrder) -> bool:
        """Cancel is always successful (simulation)."""
        return True
