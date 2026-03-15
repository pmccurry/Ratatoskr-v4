"""Cash manager — checks cash availability for orders."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.paper_trading.config import PaperTradingConfig
    from app.paper_trading.models import PaperOrder


class CashManager:
    """Checks cash availability for orders.

    Reads cash balance from portfolio module (stubbed until TASK-013).
    Does NOT own cash state — only queries and validates.
    """

    def __init__(self, config: PaperTradingConfig):
        self._config = config

    async def check_availability(
        self,
        db: AsyncSession,
        required_cash: Decimal,
        market: str,
        broker_account_id: str | None = None,
    ) -> tuple[bool, Decimal]:
        """Check if enough cash is available.

        Returns: (is_available: bool, available_cash: Decimal)

        NOTE: Until TASK-013, returns (True, initial_cash) as a stub.
        """
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                account_scope = "equities"
                if market == "forex" and broker_account_id:
                    account_scope = broker_account_id
                # Need user_id — get from any available context
                # For now, use total cash as a simpler check
                from app.portfolio.repository import CashBalanceRepository
                cash_repo = CashBalanceRepository()
                cash = await cash_repo.get_by_scope(db, account_scope, None)
                if cash is None:
                    # Try getting total across all scopes
                    from app.portfolio.models import CashBalance
                    from sqlalchemy import select, func
                    result = await db.execute(
                        select(func.coalesce(func.sum(CashBalance.balance), self._config.initial_cash))
                    )
                    available = result.scalar_one()
                else:
                    available = cash.balance
                return required_cash <= available, available
        except Exception:
            pass
        # Fallback if portfolio not initialized
        available = self._config.initial_cash
        return required_cash <= available, available

    def calculate_required_cash(
        self, order: PaperOrder, reference_price: Decimal
    ) -> Decimal:
        """Calculate cash required for an order.

        For buys: qty * reference_price * contract_multiplier + estimated_fee
        For sells: 0 (closing positions releases cash, doesn't consume it)
        """
        if order.side == "sell":
            return Decimal("0")

        multiplier = Decimal(str(order.contract_multiplier))
        gross = order.requested_qty * reference_price * multiplier
        estimated_fee = self._estimate_fee(gross, getattr(order, "market", "equities"))
        return gross + estimated_fee

    def _estimate_fee(self, gross_value: Decimal, market: str) -> Decimal:
        """Estimate trading fee for cash reservation purposes."""
        if market == "forex":
            return gross_value * self._config.fee_spread_bps_forex / Decimal("10000")
        if market == "options":
            return self._config.fee_per_trade_options
        # equities
        return self._config.fee_per_trade_equities
