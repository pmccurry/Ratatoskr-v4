"""Risk check: Strategy-level enable status."""

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class StrategyEnableCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "strategy_enable"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        # Manual, safety, and system signals bypass this check
        if signal.source in ("manual", "safety", "system"):
            return CheckResult(outcome=CheckOutcome.PASS)
        if context.strategy.status != "enabled":
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="strategy_not_enabled",
                reason_text=f"Strategy is {context.strategy.status}, not enabled",
            )
        return CheckResult(outcome=CheckOutcome.PASS)
