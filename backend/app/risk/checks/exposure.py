"""Risk checks: Symbol, strategy, and portfolio exposure limits."""

from decimal import Decimal

from app.risk.checks.base import CheckOutcome, CheckResult, RiskCheck, RiskContext


class SymbolExposureCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "symbol_exposure_limit"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if context.portfolio_equity <= 0:
            return CheckResult(outcome=CheckOutcome.PASS)

        max_pct = context.risk_config.max_symbol_exposure_percent
        max_value = max_pct / 100 * context.portfolio_equity

        current = context.symbol_exposure.get(signal.symbol, Decimal("0"))

        proposed_value = context.proposed_position_value
        proposed_total = current + proposed_value

        if proposed_total > max_value:
            remaining = max_value - current
            if remaining >= context.risk_config.min_position_value:
                return CheckResult(
                    outcome=CheckOutcome.MODIFY,
                    reason_code="symbol_exposure_capped",
                    reason_text=f"Exposure to {signal.symbol} capped at {max_pct}%",
                    modifications={
                        "original_value": str(proposed_value),
                        "approved_value": str(remaining),
                        "modification_reason": "symbol_exposure_cap",
                    },
                )
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="symbol_exposure_limit",
                reason_text=f"Exposure to {signal.symbol} would exceed {max_pct}%",
            )
        return CheckResult(outcome=CheckOutcome.PASS)


class StrategyExposureCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "strategy_exposure_limit"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if context.portfolio_equity <= 0:
            return CheckResult(outcome=CheckOutcome.PASS)

        max_pct = context.risk_config.max_strategy_exposure_percent
        max_value = max_pct / 100 * context.portfolio_equity

        strategy_id_str = str(signal.strategy_id)
        current = context.strategy_exposure.get(strategy_id_str, Decimal("0"))

        proposed_value = context.proposed_position_value
        proposed_total = current + proposed_value

        if proposed_total > max_value:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="strategy_exposure_limit",
                reason_text=f"Strategy exposure would exceed {max_pct}%",
            )
        return CheckResult(outcome=CheckOutcome.PASS)


class PortfolioExposureCheck(RiskCheck):
    @property
    def name(self) -> str:
        return "portfolio_exposure_limit"

    @property
    def applies_to_exits(self) -> bool:
        return False

    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        if context.portfolio_equity <= 0:
            return CheckResult(outcome=CheckOutcome.PASS)

        max_pct = context.risk_config.max_total_exposure_percent
        max_value = max_pct / 100 * context.portfolio_equity

        proposed_value = context.proposed_position_value
        proposed_total = context.total_exposure + proposed_value

        if proposed_total > max_value:
            return CheckResult(
                outcome=CheckOutcome.REJECT,
                reason_code="portfolio_exposure_limit",
                reason_text=f"Total exposure would exceed {max_pct}%",
            )
        return CheckResult(outcome=CheckOutcome.PASS)
