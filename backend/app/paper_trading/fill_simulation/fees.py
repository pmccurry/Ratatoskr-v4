"""Fee model for fill simulation."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.paper_trading.config import PaperTradingConfig


class FeeModel:
    """Calculates trading fees based on market configuration.

    Fee types:
    - per_trade: flat amount per order (equities, options)
    - spread_bps: basis points of gross value (forex spread cost)
    """

    def calculate(
        self, gross_value: Decimal, market: str, config: PaperTradingConfig
    ) -> Decimal:
        """Calculate the fee for a fill."""
        if market == "forex":
            return gross_value * config.fee_spread_bps_forex / Decimal("10000")
        elif market == "options":
            return config.fee_per_trade_options
        else:
            # equities
            return config.fee_per_trade_equities
