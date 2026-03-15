"""Unit tests for risk check logic."""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest

from app.risk.checks.base import CheckOutcome, CheckResult, RiskContext
from app.risk.checks.kill_switch import KillSwitchCheck
from app.risk.checks.strategy_enable import StrategyEnableCheck
from app.risk.checks.position_limit import PositionLimitCheck
from app.risk.checks.position_sizing import PositionSizingCheck
from app.risk.checks.exposure import (
    SymbolExposureCheck,
    StrategyExposureCheck,
    PortfolioExposureCheck,
)
from app.risk.checks.drawdown import DrawdownCheck
from app.risk.checks.daily_loss import DailyLossCheck


# ---------------------------------------------------------------------------
# Helpers — mock signal and risk config
# ---------------------------------------------------------------------------

@dataclass
class MockSignal:
    signal_type: str = "entry"
    source: str = "strategy"
    symbol: str = "AAPL"
    market: str = "equities"
    strategy_id: object = None
    side: str = "buy"

    def __post_init__(self):
        if self.strategy_id is None:
            self.strategy_id = uuid4()


@dataclass
class MockStrategy:
    status: str = "enabled"


@dataclass
class MockRiskConfig:
    max_position_size_percent: Decimal = Decimal("10")
    min_position_value: Decimal = Decimal("100")
    max_symbol_exposure_percent: Decimal = Decimal("20")
    max_strategy_exposure_percent: Decimal = Decimal("30")
    max_total_exposure_percent: Decimal = Decimal("80")
    max_drawdown_percent: Decimal = Decimal("10")
    max_drawdown_catastrophic_percent: Decimal = Decimal("20")
    max_daily_loss_percent: Decimal = Decimal("3")
    max_daily_loss_amount: Decimal | None = None


def _ctx(**overrides) -> RiskContext:
    defaults = dict(
        risk_config=MockRiskConfig(),
        strategy=MockStrategy(),
        strategy_config={"position_sizing": {"method": "percent_equity", "percent": 5, "max_positions": 3}},
        portfolio_equity=Decimal("100000"),
        portfolio_cash=Decimal("50000"),
        peak_equity=Decimal("100000"),
        current_drawdown_percent=Decimal("0"),
        daily_realized_loss=Decimal("0"),
        symbol_exposure={},
        strategy_exposure={},
        total_exposure=Decimal("0"),
        open_positions_count=0,
        strategy_positions_count=0,
        current_price=Decimal("150"),
        proposed_position_value=Decimal("5000"),
        kill_switch_global=False,
        kill_switch_strategy=False,
    )
    defaults.update(overrides)
    return RiskContext(**defaults)


# ---------------------------------------------------------------------------
# 1. Kill Switch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    @pytest.mark.asyncio
    async def test_global_active_rejects_entry(self):
        check = KillSwitchCheck()
        result = await check.evaluate(MockSignal(signal_type="entry"), _ctx(kill_switch_global=True))
        assert result.outcome == CheckOutcome.REJECT
        assert "global" in result.reason_code

    @pytest.mark.asyncio
    async def test_strategy_active_rejects_entry(self):
        check = KillSwitchCheck()
        result = await check.evaluate(MockSignal(signal_type="entry"), _ctx(kill_switch_strategy=True))
        assert result.outcome == CheckOutcome.REJECT
        assert "strategy" in result.reason_code

    @pytest.mark.asyncio
    async def test_inactive_passes(self):
        check = KillSwitchCheck()
        result = await check.evaluate(MockSignal(), _ctx())
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_does_not_apply_to_exits(self):
        check = KillSwitchCheck()
        assert check.applies_to_exits is False

    @pytest.mark.asyncio
    async def test_exit_signal_passes_even_with_global_active(self):
        check = KillSwitchCheck()
        # Exit signals won't even reach this check (applies_to_exits=False)
        # But if they did, the check only rejects entry/scale_in
        result = await check.evaluate(MockSignal(signal_type="exit"), _ctx(kill_switch_global=True))
        assert result.outcome == CheckOutcome.PASS


# ---------------------------------------------------------------------------
# 2. Strategy Enable
# ---------------------------------------------------------------------------

class TestStrategyEnable:
    @pytest.mark.asyncio
    async def test_disabled_strategy_rejects(self):
        check = StrategyEnableCheck()
        ctx = _ctx(strategy=MockStrategy(status="disabled"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_paused_strategy_rejects(self):
        check = StrategyEnableCheck()
        ctx = _ctx(strategy=MockStrategy(status="paused"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_enabled_strategy_passes(self):
        check = StrategyEnableCheck()
        result = await check.evaluate(MockSignal(), _ctx())
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_manual_source_bypasses(self):
        check = StrategyEnableCheck()
        ctx = _ctx(strategy=MockStrategy(status="paused"))
        result = await check.evaluate(MockSignal(source="manual"), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_safety_source_bypasses(self):
        check = StrategyEnableCheck()
        ctx = _ctx(strategy=MockStrategy(status="disabled"))
        result = await check.evaluate(MockSignal(source="safety"), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_system_source_bypasses(self):
        check = StrategyEnableCheck()
        ctx = _ctx(strategy=MockStrategy(status="disabled"))
        result = await check.evaluate(MockSignal(source="system"), ctx)
        assert result.outcome == CheckOutcome.PASS


# ---------------------------------------------------------------------------
# 6. Position Limit
# ---------------------------------------------------------------------------

class TestPositionLimit:
    @pytest.mark.asyncio
    async def test_at_max_rejects(self):
        check = PositionLimitCheck()
        ctx = _ctx(strategy_positions_count=3)
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_under_limit_passes(self):
        check = PositionLimitCheck()
        ctx = _ctx(strategy_positions_count=1)
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exit_signal_passes(self):
        check = PositionLimitCheck()
        ctx = _ctx(strategy_positions_count=3)
        result = await check.evaluate(MockSignal(signal_type="exit"), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_no_max_configured_passes(self):
        check = PositionLimitCheck()
        ctx = _ctx(strategy_config={"position_sizing": {}})
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS


# ---------------------------------------------------------------------------
# 7. Position Sizing
# ---------------------------------------------------------------------------

class TestPositionSizing:
    @pytest.mark.asyncio
    async def test_valid_size_passes(self):
        check = PositionSizingCheck()
        result = await check.evaluate(MockSignal(), _ctx())
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exceeds_max_capped(self):
        check = PositionSizingCheck()
        # percent_equity 50% of 100k = 50000, max is 10% = 10000
        ctx = _ctx(strategy_config={"position_sizing": {"method": "percent_equity", "percent": 50}})
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.MODIFY
        assert result.modifications is not None

    @pytest.mark.asyncio
    async def test_too_small_rejects(self):
        check = PositionSizingCheck()
        ctx = _ctx(
            strategy_config={"position_sizing": {"method": "fixed_dollar", "amount": 50}},
            risk_config=MockRiskConfig(min_position_value=Decimal("100")),
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_exit_signal_passes(self):
        check = PositionSizingCheck()
        result = await check.evaluate(MockSignal(signal_type="exit"), _ctx())
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_fixed_qty_calculation(self):
        check = PositionSizingCheck()
        result = check._calculate_position_value(
            "fixed_qty", {"qty": 100}, Decimal("100000"), Decimal("50")
        )
        assert result == Decimal("5000")

    @pytest.mark.asyncio
    async def test_percent_equity_calculation(self):
        check = PositionSizingCheck()
        result = check._calculate_position_value(
            "percent_equity", {"percent": 5}, Decimal("100000"), Decimal("50")
        )
        assert result == Decimal("5000")


# ---------------------------------------------------------------------------
# 8. Symbol Exposure
# ---------------------------------------------------------------------------

class TestSymbolExposure:
    @pytest.mark.asyncio
    async def test_within_limit_passes(self):
        check = SymbolExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("5000"),
            symbol_exposure={"AAPL": Decimal("10000")},
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exceeds_limit_rejects(self):
        check = SymbolExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("15000"),
            symbol_exposure={"AAPL": Decimal("10000")},
            # 20% of 100k = 20k limit, 10k + 15k = 25k > 20k
        )
        result = await check.evaluate(MockSignal(), ctx)
        # May be MODIFY if remaining >= min, or REJECT
        assert result.outcome in (CheckOutcome.REJECT, CheckOutcome.MODIFY)

    @pytest.mark.asyncio
    async def test_caps_when_remaining_sufficient(self):
        check = SymbolExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("15000"),
            symbol_exposure={"AAPL": Decimal("10000")},
            # remaining = 20000 - 10000 = 10000, min = 100 → can cap
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.MODIFY


# ---------------------------------------------------------------------------
# 9. Strategy Exposure
# ---------------------------------------------------------------------------

class TestStrategyExposure:
    @pytest.mark.asyncio
    async def test_within_limit_passes(self):
        check = StrategyExposureCheck()
        sid = uuid4()
        ctx = _ctx(
            proposed_position_value=Decimal("5000"),
            strategy_exposure={str(sid): Decimal("10000")},
        )
        result = await check.evaluate(MockSignal(strategy_id=sid), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exceeds_limit_rejects(self):
        check = StrategyExposureCheck()
        sid = uuid4()
        ctx = _ctx(
            proposed_position_value=Decimal("25000"),
            strategy_exposure={str(sid): Decimal("10000")},
            # 30% of 100k = 30k, 10k + 25k = 35k > 30k
        )
        result = await check.evaluate(MockSignal(strategy_id=sid), ctx)
        assert result.outcome == CheckOutcome.REJECT


# ---------------------------------------------------------------------------
# 10. Portfolio Exposure
# ---------------------------------------------------------------------------

class TestPortfolioExposure:
    @pytest.mark.asyncio
    async def test_within_limit_passes(self):
        check = PortfolioExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("5000"),
            total_exposure=Decimal("50000"),
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exceeds_limit_rejects(self):
        check = PortfolioExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("30000"),
            total_exposure=Decimal("60000"),
            # 80% of 100k = 80k, 60k + 30k = 90k > 80k
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT


# ---------------------------------------------------------------------------
# 11. Drawdown
# ---------------------------------------------------------------------------

class TestDrawdown:
    @pytest.mark.asyncio
    async def test_within_limit_passes(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("5"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exceeds_limit_rejects(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("12"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_at_limit_rejects(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("10"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_exit_signal_passes(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("15"))
        result = await check.evaluate(MockSignal(signal_type="exit"), ctx)
        assert result.outcome == CheckOutcome.PASS


# ---------------------------------------------------------------------------
# 12. Daily Loss
# ---------------------------------------------------------------------------

class TestDailyLoss:
    @pytest.mark.asyncio
    async def test_within_limit_passes(self):
        check = DailyLossCheck()
        ctx = _ctx(daily_realized_loss=Decimal("1000"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_exceeds_limit_rejects(self):
        check = DailyLossCheck()
        # 3% of 100k = 3000
        ctx = _ctx(daily_realized_loss=Decimal("3500"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_at_limit_rejects(self):
        check = DailyLossCheck()
        ctx = _ctx(daily_realized_loss=Decimal("3000"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_exit_signal_passes(self):
        check = DailyLossCheck()
        ctx = _ctx(daily_realized_loss=Decimal("5000"))
        result = await check.evaluate(MockSignal(signal_type="exit"), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_absolute_limit(self):
        check = DailyLossCheck()
        ctx = _ctx(
            daily_realized_loss=Decimal("2500"),
            risk_config=MockRiskConfig(max_daily_loss_amount=Decimal("2000")),
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT


# ---------------------------------------------------------------------------
# Pipeline behavior
# ---------------------------------------------------------------------------

class TestRiskPipeline:
    @pytest.mark.asyncio
    async def test_all_pass_returns_pass(self):
        """Run all non-DB checks and verify all pass with valid context."""
        checks = [
            KillSwitchCheck(),
            StrategyEnableCheck(),
            PositionLimitCheck(),
            PositionSizingCheck(),
            SymbolExposureCheck(),
            StrategyExposureCheck(),
            PortfolioExposureCheck(),
            DrawdownCheck(),
            DailyLossCheck(),
        ]
        signal = MockSignal()
        ctx = _ctx()
        for check in checks:
            result = await check.evaluate(signal, ctx)
            assert result.outcome == CheckOutcome.PASS, f"{check.name} should pass"

    @pytest.mark.asyncio
    async def test_exit_signals_skip_entry_checks(self):
        """Exit checks: only checks with applies_to_exits=True should run."""
        entry_only = [
            KillSwitchCheck(),
            StrategyEnableCheck(),
            PositionLimitCheck(),
            PositionSizingCheck(),
            SymbolExposureCheck(),
            StrategyExposureCheck(),
            PortfolioExposureCheck(),
            DrawdownCheck(),
            DailyLossCheck(),
        ]
        for check in entry_only:
            assert check.applies_to_exits is False

    @pytest.mark.asyncio
    async def test_rejection_includes_reason(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("15"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT
        assert result.reason_code != ""
        assert result.reason_text != ""

    @pytest.mark.asyncio
    async def test_modification_includes_details(self):
        check = PositionSizingCheck()
        ctx = _ctx(strategy_config={"position_sizing": {"method": "percent_equity", "percent": 50}})
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.MODIFY
        assert result.modifications is not None
        assert "approved_value" in result.modifications
