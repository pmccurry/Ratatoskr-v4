"""Risk check: Position limit per strategy."""

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class PositionLimitCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "position_limit"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if signal.signal_type != "entry":
            return CheckResult(outcome=CheckOutcome.PASS)

        max_positions = context.strategy_config.get("position_sizing", {}).get("max_positions")
        if max_positions is None:
            return CheckResult(outcome=CheckOutcome.PASS)

        # TODO (TASK-013): strategy_positions_count is stubbed to 0
        if context.strategy_positions_count >= max_positions:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="max_positions_reached",
                reason_text=f"Strategy has {context.strategy_positions_count}/{max_positions} positions",
            )
        return CheckResult(outcome=CheckOutcome.PASS)
