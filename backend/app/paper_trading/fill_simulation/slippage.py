"""Slippage model for fill simulation."""

from decimal import Decimal


class SlippageModel:
    """Applies slippage to a reference price.

    Slippage always works against the trader:
    - Buys: price increases (pay more)
    - Sells: price decreases (receive less)
    """

    def apply(
        self, reference_price: Decimal, side: str, slippage_bps: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Apply slippage to a reference price.

        Returns: (execution_price, slippage_amount)
        """
        bps_factor = slippage_bps / Decimal("10000")

        if side == "buy":
            execution_price = reference_price * (Decimal("1") + bps_factor)
        else:
            execution_price = reference_price * (Decimal("1") - bps_factor)

        slippage_amount = abs(execution_price - reference_price)
        return execution_price, slippage_amount
