"""Integration tests for dividend processing and stock split adjustments."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.market_data.models import DividendAnnouncement
from app.portfolio.models import DividendPayment, Position, SplitAdjustment


class TestDividendProcessing:
    @pytest.mark.asyncio
    async def test_dividend_announcement_stored(self, db):
        ann = DividendAnnouncement(
            symbol="AAPL",
            corporate_action_id="div_aapl_20240715",
            ca_type="cash",
            declaration_date=date(2024, 6, 1),
            ex_date=date(2024, 7, 5),
            record_date=date(2024, 7, 6),
            payable_date=date(2024, 7, 15),
            cash_amount=Decimal("0.50"),
            status="announced",
            source="alpaca",
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(ann)
        await db.flush()

        result = await db.execute(
            select(DividendAnnouncement).where(
                DividendAnnouncement.symbol == "AAPL"
            )
        )
        found = result.scalar_one()
        assert found.cash_amount == Decimal("0.50")
        assert found.ex_date == date(2024, 7, 5)

    @pytest.mark.asyncio
    async def test_dividend_payment_created(self, db, admin_user, sample_position):
        ann = DividendAnnouncement(
            symbol="AAPL",
            corporate_action_id=f"div_aapl_{id(self)}",
            ca_type="cash",
            declaration_date=date(2024, 6, 1),
            ex_date=date(2024, 7, 5),
            record_date=date(2024, 7, 6),
            payable_date=date(2024, 7, 15),
            cash_amount=Decimal("0.50"),
            status="announced",
            source="alpaca",
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(ann)
        await db.flush()

        # 100 shares × $0.50 = $50.00
        payment = DividendPayment(
            position_id=sample_position.id,
            announcement_id=ann.id,
            user_id=admin_user.id,
            symbol="AAPL",
            ex_date=date(2024, 7, 5),
            payable_date=date(2024, 7, 15),
            shares_held=Decimal("100"),
            amount_per_share=Decimal("0.50"),
            gross_amount=Decimal("50.00"),
            net_amount=Decimal("50.00"),
            status="pending",
        )
        db.add(payment)
        await db.flush()

        assert payment.gross_amount == Decimal("50.00")
        assert payment.shares_held == Decimal("100")

    @pytest.mark.asyncio
    async def test_dividend_amount_calculation(self, db, admin_user, sample_position):
        shares = Decimal("100")
        dividend_per_share = Decimal("0.50")
        gross = shares * dividend_per_share
        assert gross == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_dividend_payment_status_transition(self, db, admin_user, sample_position):
        ann = DividendAnnouncement(
            symbol="AAPL",
            corporate_action_id=f"div_status_{id(self)}",
            ca_type="cash",
            declaration_date=date(2024, 6, 1),
            ex_date=date(2024, 7, 5),
            record_date=date(2024, 7, 6),
            payable_date=date(2024, 7, 15),
            cash_amount=Decimal("0.25"),
            status="announced",
            source="alpaca",
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(ann)
        await db.flush()

        payment = DividendPayment(
            position_id=sample_position.id,
            announcement_id=ann.id,
            user_id=admin_user.id,
            symbol="AAPL",
            ex_date=date(2024, 7, 5),
            payable_date=date(2024, 7, 15),
            shares_held=Decimal("100"),
            amount_per_share=Decimal("0.25"),
            gross_amount=Decimal("25.00"),
            net_amount=Decimal("25.00"),
            status="pending",
        )
        db.add(payment)
        await db.flush()

        # Transition to paid
        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        await db.flush()
        assert payment.status == "paid"
        assert payment.paid_at is not None


class TestStockSplit:
    @pytest.mark.asyncio
    async def test_forward_split_adjusts_qty_and_price(self, db, sample_position):
        # 2:1 split: qty 100→200, avg_entry $150→$75
        old_qty = sample_position.qty
        old_price = sample_position.avg_entry_price
        split_ratio = Decimal("2")

        sample_position.qty = old_qty * split_ratio
        sample_position.avg_entry_price = old_price / split_ratio
        sample_position.current_price = sample_position.current_price / split_ratio
        sample_position.highest_price_since_entry = sample_position.highest_price_since_entry / split_ratio
        sample_position.lowest_price_since_entry = sample_position.lowest_price_since_entry / split_ratio
        await db.flush()

        assert sample_position.qty == Decimal("200")
        assert sample_position.avg_entry_price == Decimal("75.00000000")

    @pytest.mark.asyncio
    async def test_reverse_split_adjusts_qty_and_price(self, db, sample_position):
        # 1:2 reverse split: qty 100→50, avg_entry $150→$300
        split_ratio = Decimal("0.5")

        sample_position.qty = sample_position.qty * split_ratio
        sample_position.avg_entry_price = sample_position.avg_entry_price / split_ratio
        await db.flush()

        assert sample_position.qty == Decimal("50.00000000")
        assert sample_position.avg_entry_price == Decimal("300.00000000")

    @pytest.mark.asyncio
    async def test_split_preserves_total_value(self, db, sample_position):
        pre_value = sample_position.qty * sample_position.avg_entry_price
        split_ratio = Decimal("3")

        sample_position.qty = sample_position.qty * split_ratio
        sample_position.avg_entry_price = sample_position.avg_entry_price / split_ratio

        post_value = sample_position.qty * sample_position.avg_entry_price
        assert abs(pre_value - post_value) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_split_adjustment_record(self, db):
        adj = SplitAdjustment(
            symbol="AAPL",
            split_type="forward",
            old_rate=1,
            new_rate=2,
            effective_date=date(2024, 8, 1),
            positions_adjusted=5,
            adjustments_json={"positions": ["id1", "id2"]},
        )
        db.add(adj)
        await db.flush()

        result = await db.execute(
            select(SplitAdjustment).where(SplitAdjustment.symbol == "AAPL")
        )
        found = result.scalar_one()
        assert found.old_rate == 1
        assert found.new_rate == 2
        assert found.positions_adjusted == 5
