"""Risk checks: Symbol tradability and market hours."""

from datetime import datetime, timezone

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class SymbolTradabilityCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "symbol_tradability"

    @property
    def applies_to_exits(self) -> bool:
        return True

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        from app.market_data.service import MarketDataService

        # For exits, log but don't reject
        from app.common.database import get_session_factory
        factory = get_session_factory()
        async with factory() as db:
            on_watchlist = await MarketDataService().is_symbol_on_watchlist(db, signal.symbol)

        if not on_watchlist:
            if signal.signal_type in ("exit", "scale_out"):
                # Don't block exits, just note it
                return CheckResult(outcome=CheckOutcome.PASS)
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="symbol_not_tradable",
                reason_text=f"Symbol {signal.symbol} is not on active watchlist",
            )
        return CheckResult(outcome=CheckOutcome.PASS)


class MarketHoursCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "market_hours"

    @property
    def applies_to_exits(self) -> bool:
        return True

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        now = datetime.now(timezone.utc)
        market = signal.market

        if self._is_market_open(market, now):
            return CheckResult(outcome=CheckOutcome.PASS)

        # Market closed
        if signal.signal_type in ("exit", "scale_out"):
            # Queue exit for execution at market open
            return CheckResult(
                outcome=CheckOutcome.MODIFY,
                reason_code="market_closed_exit_queued",
                reason_text="Market closed — exit signal queued for market open",
                modifications={"queue_until_market_open": True},
            )

        return CheckResult(
            outcome=CheckOutcome.REJECT,
            reason_code="market_closed",
            reason_text="Market is currently closed",
        )

    def _is_market_open(self, market: str, now: datetime) -> bool:
        weekday = now.weekday()

        if market == "forex":
            if weekday == 5:  # Saturday
                return False
            if weekday == 6:  # Sunday
                return now.hour >= 22
            if weekday == 4:  # Friday
                return now.hour < 22
            return True

        # Equities
        if weekday >= 5:
            return False
        return 13 <= now.hour < 21  # 9:30 AM - 4 PM ET in UTC (approximate)
