"""Risk check: Duplicate order guard."""

import logging

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext

logger = logging.getLogger(__name__)


class DuplicateOrderCheck(RiskCheck):
    """Check for duplicate pending/open orders.

    Queries the paper_orders table for any pending/accepted order
    with the same strategy + symbol + side.
    """

    @property
    def name(self) -> str:
        return "duplicate_order"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        try:
            from app.common.database import get_session_factory
            from app.paper_trading.repository import PaperOrderRepository

            repo = PaperOrderRepository()
            factory = get_session_factory()
            async with factory() as db:
                existing = await repo.get_pending_for_symbol(
                    db, signal.strategy_id, signal.symbol, signal.side
                )
                if existing:
                    return CheckResult(
                        outcome=CheckOutcome.REJECT,
                        reason_code="duplicate_order",
                        reason_text=(
                            f"Duplicate order: pending {signal.side} order for "
                            f"{signal.symbol} already exists (order={existing.id})"
                        ),
                    )
        except Exception as e:
            logger.warning("Duplicate order check failed, allowing signal: %s", e)

        return CheckResult(outcome=CheckOutcome.PASS)
