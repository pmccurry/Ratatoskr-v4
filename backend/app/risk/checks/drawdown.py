"""Risk check: Drawdown threshold."""

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class DrawdownCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "drawdown_limit"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if signal.signal_type in ("exit", "scale_out"):
            return CheckResult(outcome=CheckOutcome.PASS)

        max_dd = context.risk_config.max_drawdown_percent
        if context.current_drawdown_percent >= max_dd:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="drawdown_limit",
                reason_text=f"Drawdown at {context.current_drawdown_percent:.1f}% exceeds {max_dd}% limit",
            )
        return CheckResult(outcome=CheckOutcome.PASS)
