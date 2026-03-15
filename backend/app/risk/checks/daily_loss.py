"""Risk check: Daily loss limit."""

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class DailyLossCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "daily_loss_limit"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if signal.signal_type in ("exit", "scale_out"):
            return CheckResult(outcome=CheckOutcome.PASS)

        # Determine limit
        if context.risk_config.max_daily_loss_amount is not None:
            limit = context.risk_config.max_daily_loss_amount
        elif context.portfolio_equity > 0:
            limit = context.risk_config.max_daily_loss_percent / 100 * context.portfolio_equity
        else:
            return CheckResult(outcome=CheckOutcome.PASS)

        if limit <= 0:
            return CheckResult(outcome=CheckOutcome.PASS)

        # daily_realized_loss is a positive number representing losses
        if context.daily_realized_loss >= limit:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="daily_loss_limit",
                reason_text=f"Daily loss ${context.daily_realized_loss:.2f} exceeds limit ${limit:.2f}",
            )
        return CheckResult(outcome=CheckOutcome.PASS)
