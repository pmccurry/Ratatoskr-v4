"""Integration tests for position management and PnL."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.portfolio.models import Position, RealizedPnlEntry, CashBalance


class TestNewPosition:
    @pytest.mark.asyncio
    async def test_buy_creates_long_position(self, db, admin_user, sample_strategy):
        now = datetime.now(timezone.utc)
        position = Position(
            user_id=admin_user.id,
            strategy_id=sample_strategy.id,
            symbol="MSFT",
            market="equities",
            side="long",
            qty=Decimal("50"),
            avg_entry_price=Decimal("400.00000000"),
            cost_basis=Decimal("20000.00"),
            current_price=Decimal("400.00000000"),
            market_value=Decimal("20000.00"),
            status="open",
            opened_at=now,
            highest_price_since_entry=Decimal("400.00000000"),
            lowest_price_since_entry=Decimal("400.00000000"),
            contract_multiplier=1,
        )
        db.add(position)
        await db.flush()

        assert position.id is not None
        assert position.side == "long"
        assert position.qty == Decimal("50")
        assert position.status == "open"

    @pytest.mark.asyncio
    async def test_sell_creates_short_position(self, db, admin_user, sample_strategy):
        now = datetime.now(timezone.utc)
        position = Position(
            user_id=admin_user.id,
            strategy_id=sample_strategy.id,
            symbol="TSLA",
            market="equities",
            side="short",
            qty=Decimal("30"),
            avg_entry_price=Decimal("250.00000000"),
            cost_basis=Decimal("7500.00"),
            current_price=Decimal("250.00000000"),
            market_value=Decimal("7500.00"),
            status="open",
            opened_at=now,
            highest_price_since_entry=Decimal("250.00000000"),
            lowest_price_since_entry=Decimal("250.00000000"),
            contract_multiplier=1,
        )
        db.add(position)
        await db.flush()

        assert position.side == "short"
        assert position.qty == Decimal("30")


class TestScaleIn:
    @pytest.mark.asyncio
    async def test_scale_in_updates_weighted_average(self, db, sample_position):
        old_qty = sample_position.qty
        old_avg = sample_position.avg_entry_price
        add_qty = Decimal("50")
        add_price = Decimal("160.00000000")

        new_qty = old_qty + add_qty
        new_avg = (old_qty * old_avg + add_qty * add_price) / new_qty

        sample_position.qty = new_qty
        sample_position.avg_entry_price = new_avg
        sample_position.cost_basis = sample_position.cost_basis + add_qty * add_price
        await db.flush()

        assert sample_position.qty == Decimal("150")
        expected_avg = (Decimal("100") * Decimal("150") + Decimal("50") * Decimal("160")) / Decimal("150")
        assert abs(sample_position.avg_entry_price - expected_avg) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_scale_in_preserves_realized_pnl(self, db, sample_position):
        sample_position.realized_pnl = Decimal("500.00")
        await db.flush()

        # Scale in
        sample_position.qty = sample_position.qty + Decimal("25")
        await db.flush()

        assert sample_position.realized_pnl == Decimal("500.00")


class TestScaleOut:
    @pytest.mark.asyncio
    async def test_partial_close_updates_qty(self, db, sample_position):
        sample_position.qty = Decimal("50")  # Close half
        await db.flush()
        assert sample_position.qty == Decimal("50")

    @pytest.mark.asyncio
    async def test_realized_pnl_entry_created(self, db, admin_user, sample_position, sample_strategy):
        now = datetime.now(timezone.utc)
        entry = RealizedPnlEntry(
            position_id=sample_position.id,
            strategy_id=sample_strategy.id,
            user_id=admin_user.id,
            symbol="AAPL",
            market="equities",
            side="long",
            qty_closed=Decimal("50"),
            entry_price=Decimal("150.00000000"),
            exit_price=Decimal("170.00000000"),
            gross_pnl=Decimal("1000.00"),
            fees=Decimal("1.00"),
            net_pnl=Decimal("999.00"),
            pnl_percent=Decimal("6.6600"),
            holding_period_bars=24,
            closed_at=now,
        )
        db.add(entry)
        await db.flush()

        result = await db.execute(
            select(RealizedPnlEntry).where(
                RealizedPnlEntry.position_id == sample_position.id
            )
        )
        entries = result.scalars().all()
        assert len(entries) == 1
        assert entries[0].net_pnl == Decimal("999.00")

    @pytest.mark.asyncio
    async def test_avg_entry_unchanged_after_scale_out(self, db, sample_position):
        original_avg = sample_position.avg_entry_price
        sample_position.qty = Decimal("50")
        await db.flush()
        assert sample_position.avg_entry_price == original_avg


class TestFullClose:
    @pytest.mark.asyncio
    async def test_full_close_zeros_position(self, db, sample_position):
        sample_position.qty = Decimal("0")
        sample_position.status = "closed"
        sample_position.closed_at = datetime.now(timezone.utc)
        sample_position.market_value = Decimal("0.00")
        sample_position.unrealized_pnl = Decimal("0.00")
        await db.flush()

        assert sample_position.qty == Decimal("0")
        assert sample_position.status == "closed"
        assert sample_position.closed_at is not None

    @pytest.mark.asyncio
    async def test_full_close_records_pnl(self, db, sample_position):
        # Simulate full close at $170
        exit_price = Decimal("170")
        entry_price = sample_position.avg_entry_price
        qty = sample_position.qty
        gross_pnl = (exit_price - entry_price) * qty
        fee = Decimal("2.00")
        net_pnl = gross_pnl - fee

        sample_position.realized_pnl = net_pnl
        sample_position.qty = Decimal("0")
        sample_position.status = "closed"
        sample_position.closed_at = datetime.now(timezone.utc)
        await db.flush()

        assert sample_position.realized_pnl == Decimal("1998.00")


class TestUserIsolation:
    @pytest.mark.asyncio
    async def test_user_a_cannot_see_user_b_positions(self, db, admin_user, regular_user, sample_strategy):
        now = datetime.now(timezone.utc)
        # Position belongs to admin_user (via sample_strategy fixture)
        pos = Position(
            user_id=admin_user.id,
            strategy_id=sample_strategy.id,
            symbol="GOOGL",
            market="equities",
            side="long",
            qty=Decimal("10"),
            avg_entry_price=Decimal("170.00000000"),
            cost_basis=Decimal("1700.00"),
            current_price=Decimal("170.00000000"),
            market_value=Decimal("1700.00"),
            status="open",
            opened_at=now,
            highest_price_since_entry=Decimal("170.00000000"),
            lowest_price_since_entry=Decimal("170.00000000"),
            contract_multiplier=1,
        )
        db.add(pos)
        await db.flush()

        # Query as regular_user
        result = await db.execute(
            select(Position).where(
                Position.user_id == regular_user.id,
                Position.status == "open",
            )
        )
        user_positions = result.scalars().all()
        assert len(user_positions) == 0


class TestCashBalance:
    @pytest.mark.asyncio
    async def test_initial_cash_balance(self, db, admin_user):
        cash = CashBalance(
            account_scope="equities",
            balance=Decimal("100000.00"),
            user_id=admin_user.id,
        )
        db.add(cash)
        await db.flush()

        result = await db.execute(
            select(CashBalance).where(
                CashBalance.user_id == admin_user.id,
                CashBalance.account_scope == "equities",
            )
        )
        found = result.scalar_one()
        assert found.balance == Decimal("100000.00")

    @pytest.mark.asyncio
    async def test_cash_debit_on_buy(self, db, admin_user):
        cash = CashBalance(
            account_scope="equities",
            balance=Decimal("100000.00"),
            user_id=admin_user.id,
        )
        db.add(cash)
        await db.flush()

        cash.balance = cash.balance - Decimal("15000.00")
        await db.flush()
        assert cash.balance == Decimal("85000.00")
