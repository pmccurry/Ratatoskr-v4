"""Risk check: Global and strategy kill switch."""

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class KillSwitchCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "kill_switch"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if context.kill_switch_global or context.kill_switch_strategy:
            if signal.signal_type in ("entry", "scale_in"):
                return CheckResult(
                    outcome=CheckOutcome.REJECT,
                    reason_code="global_kill_switch" if context.kill_switch_global else "strategy_kill_switch",
                    reason_text="Trading is halted" if context.kill_switch_global else "Trading halted for strategy",
                )
        return CheckResult(outcome=CheckOutcome.PASS)
