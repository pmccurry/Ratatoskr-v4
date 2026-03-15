"""Fill simulation engine — orchestrates slippage and fee calculation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from app.paper_trading.executors.base import FillResult
from app.paper_trading.fill_simulation.fees import FeeModel
from app.paper_trading.fill_simulation.slippage import SlippageModel

if TYPE_CHECKING:
    from app.paper_trading.config import PaperTradingConfig
    from app.paper_trading.models import PaperOrder


class FillSimulationEngine:
    """Orchestrates fill simulation: reference price -> slippage -> fees -> result."""

    def __init__(
        self,
        slippage_model: SlippageModel,
        fee_model: FeeModel,
        config: PaperTradingConfig,
    ):
        self._slippage = slippage_model
        self._fee = fee_model
        self._config = config

    async def simulate(
        self, order: PaperOrder, reference_price: Decimal
    ) -> FillResult:
        """Simulate a fill for an order.

        Steps:
        1. Determine slippage BPS from config based on market
        2. Apply slippage to reference price
        3. Calculate gross value: qty * execution_price * contract_multiplier
        4. Calculate fee based on market
        5. Calculate net value:
           - Buys: gross_value + fee (total cost)
           - Sells: gross_value - fee (net proceeds)
        6. Return FillResult with all values
        """
        slippage_bps = self._get_slippage_bps(order)
        execution_price, slippage_per_unit = self._slippage.apply(
            reference_price, order.side, slippage_bps
        )

        multiplier = Decimal(str(order.contract_multiplier))
        gross_value = order.requested_qty * execution_price * multiplier

        fee = self._fee.calculate(gross_value, order.market, self._config)

        slippage_amount = slippage_per_unit * order.requested_qty * multiplier

        if order.side == "buy":
            net_value = gross_value + fee
        else:
            net_value = gross_value - fee

        now = datetime.now(timezone.utc)

        return FillResult(
            order_id=order.id,
            qty=order.requested_qty,
            reference_price=reference_price,
            price=execution_price,
            fee=fee,
            slippage_bps=slippage_bps,
            slippage_amount=slippage_amount,
            gross_value=gross_value,
            net_value=net_value,
            filled_at=now,
        )

    def _get_slippage_bps(self, order: PaperOrder) -> Decimal:
        """Get slippage BPS for this order's market."""
        if order.underlying_symbol is not None:
            return self._config.slippage_bps_options
        if order.market == "forex":
            return self._config.slippage_bps_forex
        return self._config.slippage_bps_equities
