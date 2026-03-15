"""Executor abstraction — abstract interface for order execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from abc import ABC, abstractmethod
from uuid import UUID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.paper_trading.models import PaperOrder


@dataclass
class OrderResult:
    success: bool
    order_id: UUID | None = None
    broker_order_id: str | None = None
    status: str = ""
    rejection_reason: str | None = None


@dataclass
class FillResult:
    order_id: UUID
    qty: Decimal
    reference_price: Decimal
    price: Decimal
    fee: Decimal
    slippage_bps: Decimal
    slippage_amount: Decimal
    gross_value: Decimal
    net_value: Decimal
    filled_at: datetime
    broker_fill_id: str | None = None


class Executor(ABC):
    """Abstract executor interface.

    Every execution mode (simulation, Alpaca paper, forex pool)
    implements this interface. The paper trading service routes
    to the correct executor based on market and config.
    """

    @property
    @abstractmethod
    def execution_mode(self) -> str:
        """Return the execution mode name (e.g., 'simulation', 'paper')."""

    @abstractmethod
    async def submit_order(
        self, order: PaperOrder, reference_price: Decimal
    ) -> OrderResult:
        """Submit an order for execution.

        Returns OrderResult with acceptance/rejection status.
        For simulation: processes immediately.
        For broker APIs: submits to broker, returns acceptance.
        """

    @abstractmethod
    async def simulate_fill(
        self, order: PaperOrder, reference_price: Decimal
    ) -> FillResult:
        """Simulate or record a fill for an accepted order.

        For simulation: calculates fill price with slippage and fees.
        For broker APIs: waits for broker fill notification.
        """

    @abstractmethod
    async def cancel_order(self, order: PaperOrder) -> bool:
        """Cancel a pending/accepted order. Returns True if successful."""
