"""Risk check: Position sizing validation and capping."""

from decimal import Decimal

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class PositionSizingCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "position_sizing"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if signal.signal_type not in ("entry", "scale_in"):
            return CheckResult(outcome=CheckOutcome.PASS)

        if context.portfolio_equity <= 0 or context.current_price is None or context.current_price <= 0:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="invalid_size",
                reason_text="Cannot calculate position size: missing equity or price data",
            )

        sizing_config = context.strategy_config.get("position_sizing", {})
        method = sizing_config.get("method", "fixed_qty")

        requested_value = self._calculate_position_value(
            method, sizing_config, context.portfolio_equity, context.current_price,
        )

        if requested_value is None or requested_value <= 0:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="invalid_size",
                reason_text="Calculated position size is zero or negative",
            )

        max_value = context.risk_config.max_position_size_percent / 100 * context.portfolio_equity

        if requested_value > max_value:
            if max_value >= context.risk_config.min_position_value:
                return CheckResult(
                    outcome=CheckOutcome.MODIFY,
                    reason_code="position_size_capped",
                    reason_text=f"Position size capped from ${requested_value:.2f} to ${max_value:.2f}",
                    modifications={
                        "original_value": str(requested_value),
                        "approved_value": str(max_value),
                        "modification_reason": "max_position_size_cap",
                    },
                )
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="position_too_large",
                reason_text=f"Position value ${requested_value:.2f} exceeds max {context.risk_config.max_position_size_percent}%",
            )

        if requested_value < context.risk_config.min_position_value:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="position_too_small",
                reason_text=f"Position value ${requested_value:.2f} below minimum ${context.risk_config.min_position_value}",
            )

        return CheckResult(outcome=CheckOutcome.PASS)

    def _calculate_position_value(
        self, method: str, config: dict, equity: Decimal, price: Decimal,
    ) -> Decimal | None:
        if method == "fixed_qty":
            qty = Decimal(str(config.get("qty", 0)))
            return qty * price

        if method == "fixed_dollar":
            return Decimal(str(config.get("amount", 0)))

        if method == "percent_equity":
            pct = Decimal(str(config.get("percent", 0)))
            return equity * pct / 100

        if method == "risk_based":
            risk_pct = Decimal(str(config.get("risk_percent", 1)))
            risk_amount = equity * risk_pct / 100
            stop_distance = Decimal(str(config.get("stop_distance", 0)))
            if stop_distance <= 0:
                return None
            qty = risk_amount / stop_distance
            return qty * price

        return None
