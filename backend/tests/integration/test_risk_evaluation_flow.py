"""Integration tests for risk evaluation flow."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.risk.models import KillSwitch
from app.risk.checks.base import CheckOutcome, RiskContext
from app.risk.checks.kill_switch import KillSwitchCheck
from app.risk.checks.drawdown import DrawdownCheck
from app.risk.checks.daily_loss import DailyLossCheck
from app.risk.checks.exposure import SymbolExposureCheck, PortfolioExposureCheck
from app.risk.checks.position_sizing import PositionSizingCheck

from tests.unit.test_risk_checks import MockSignal, MockStrategy, MockRiskConfig, _ctx


class TestRiskApproval:
    @pytest.mark.asyncio
    async def test_clean_signal_approved(self):
        """All checks pass with no risk violations."""
        checks = [
            KillSwitchCheck(),
            PositionSizingCheck(),
            SymbolExposureCheck(),
            PortfolioExposureCheck(),
            DrawdownCheck(),
            DailyLossCheck(),
        ]
        signal = MockSignal()
        ctx = _ctx()
        for check in checks:
            result = await check.evaluate(signal, ctx)
            assert result.outcome == CheckOutcome.PASS, f"{check.name} failed"

    @pytest.mark.asyncio
    async def test_kill_switch_blocks_entry(self):
        check = KillSwitchCheck()
        signal = MockSignal(signal_type="entry")
        ctx = _ctx(kill_switch_global=True)
        result = await check.evaluate(signal, ctx)
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_kill_switch_allows_exit(self):
        check = KillSwitchCheck()
        signal = MockSignal(signal_type="exit")
        ctx = _ctx(kill_switch_global=True)
        result = await check.evaluate(signal, ctx)
        assert result.outcome == CheckOutcome.PASS


class TestExposureLimits:
    @pytest.mark.asyncio
    async def test_symbol_exposure_rejection(self):
        check = SymbolExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("25000"),
            symbol_exposure={"AAPL": Decimal("18000")},
            risk_config=MockRiskConfig(
                max_symbol_exposure_percent=Decimal("20"),
                min_position_value=Decimal("5000"),
            ),
        )
        result = await check.evaluate(MockSignal(), ctx)
        # 20% of 100k = 20k, 18k + 25k = 43k > 20k
        # remaining = 20k - 18k = 2k < min 5k → reject
        assert result.outcome == CheckOutcome.REJECT

    @pytest.mark.asyncio
    async def test_portfolio_exposure_rejection(self):
        check = PortfolioExposureCheck()
        ctx = _ctx(
            proposed_position_value=Decimal("25000"),
            total_exposure=Decimal("60000"),
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT


class TestDrawdownCheck:
    @pytest.mark.asyncio
    async def test_drawdown_within_limit_passes(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("5"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.PASS

    @pytest.mark.asyncio
    async def test_drawdown_exceeds_limit_rejects(self):
        check = DrawdownCheck()
        ctx = _ctx(current_drawdown_percent=Decimal("12"))
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.REJECT


class TestRiskModification:
    @pytest.mark.asyncio
    async def test_position_size_reduced_to_fit(self):
        check = PositionSizingCheck()
        ctx = _ctx(
            strategy_config={
                "position_sizing": {"method": "percent_equity", "percent": 50}
            },
        )
        result = await check.evaluate(MockSignal(), ctx)
        assert result.outcome == CheckOutcome.MODIFY
        assert result.modifications is not None
        assert "approved_value" in result.modifications


class TestKillSwitchPersistence:
    @pytest.mark.asyncio
    async def test_kill_switch_record_creation(self, db):
        ks = KillSwitch(
            scope="global",
            is_active=True,
            activated_by="admin",
            activated_at=datetime.now(timezone.utc),
            reason="Emergency stop",
        )
        db.add(ks)
        await db.flush()

        result = await db.execute(
            select(KillSwitch).where(KillSwitch.scope == "global", KillSwitch.is_active == True)
        )
        found = result.scalar_one()
        assert found.scope == "global"
        assert found.is_active is True

    @pytest.mark.asyncio
    async def test_kill_switch_deactivation(self, db):
        ks = KillSwitch(
            scope="global",
            is_active=True,
            activated_by="admin",
            activated_at=datetime.now(timezone.utc),
            reason="Test",
        )
        db.add(ks)
        await db.flush()

        ks.is_active = False
        ks.deactivated_at = datetime.now(timezone.utc)
        await db.flush()

        assert ks.is_active is False
        assert ks.deactivated_at is not None
