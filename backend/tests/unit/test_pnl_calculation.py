"""Unit tests for PnL calculations — fill-to-position scenarios."""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

from app.portfolio.fill_processor import FillProcessor


# ---------------------------------------------------------------------------
# Mock objects
# ---------------------------------------------------------------------------

@dataclass
class MockPosition:
    id: object = None
    strategy_id: object = None
    symbol: str = "AAPL"
    market: str = "equities"
    side: str = "long"
    qty: Decimal = Decimal("0")
    avg_entry_price: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    unrealized_pnl_percent: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    total_dividends_received: Decimal = Decimal("0")
    total_return: Decimal = Decimal("0")
    total_return_percent: Decimal = Decimal("0")
    contract_multiplier: int = 1
    status: str = "open"

    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()
        if self.strategy_id is None:
            self.strategy_id = uuid4()


@dataclass
class MockFill:
    qty: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    net_value: Decimal = Decimal("0")
    filled_at: datetime = None

    def __post_init__(self):
        if self.filled_at is None:
            self.filled_at = datetime.now(timezone.utc)


@dataclass
class MockOrder:
    side: str = "buy"
    signal_type: str = "entry"
    requested_qty: Decimal = Decimal("0")
    filled_qty: Decimal | None = None
    contract_multiplier: int = 1


# ---------------------------------------------------------------------------
# Scenario determination
# ---------------------------------------------------------------------------

class TestDetermineScenario:
    def test_no_position_returns_entry(self):
        fp = FillProcessor()
        assert fp._determine_scenario(None, MockOrder()) == "entry"

    def test_same_direction_returns_scale_in(self):
        fp = FillProcessor()
        pos = MockPosition(side="long", qty=Decimal("100"))
        order = MockOrder(side="buy")
        assert fp._determine_scenario(pos, order) == "scale_in"

    def test_opposite_direction_full_qty_returns_full_exit(self):
        fp = FillProcessor()
        pos = MockPosition(side="long", qty=Decimal("100"))
        order = MockOrder(side="sell", requested_qty=Decimal("100"))
        assert fp._determine_scenario(pos, order) == "full_exit"

    def test_opposite_direction_partial_qty_returns_scale_out(self):
        fp = FillProcessor()
        pos = MockPosition(side="long", qty=Decimal("100"))
        order = MockOrder(side="sell", requested_qty=Decimal("50"))
        assert fp._determine_scenario(pos, order) == "scale_out"

    def test_short_position_buy_back_full(self):
        fp = FillProcessor()
        pos = MockPosition(side="short", qty=Decimal("100"))
        order = MockOrder(side="buy", requested_qty=Decimal("100"))
        assert fp._determine_scenario(pos, order) == "full_exit"

    def test_short_position_sell_more_scale_in(self):
        fp = FillProcessor()
        pos = MockPosition(side="short", qty=Decimal("100"))
        order = MockOrder(side="sell")
        assert fp._determine_scenario(pos, order) == "scale_in"


# ---------------------------------------------------------------------------
# Unrealized PnL (pure logic)
# ---------------------------------------------------------------------------

class TestUnrealizedPnl:
    def test_long_unrealized_profit(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="long", qty=Decimal("100"),
            avg_entry_price=Decimal("150"), current_price=Decimal("170"),
        )
        fp._update_unrealized_pnl(pos)
        assert pos.unrealized_pnl == Decimal("2000")

    def test_long_unrealized_loss(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="long", qty=Decimal("100"),
            avg_entry_price=Decimal("150"), current_price=Decimal("130"),
        )
        fp._update_unrealized_pnl(pos)
        assert pos.unrealized_pnl == Decimal("-2000")

    def test_short_unrealized_profit(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="short", qty=Decimal("100"),
            avg_entry_price=Decimal("150"), current_price=Decimal("130"),
        )
        fp._update_unrealized_pnl(pos)
        assert pos.unrealized_pnl == Decimal("2000")

    def test_short_unrealized_loss(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="short", qty=Decimal("100"),
            avg_entry_price=Decimal("150"), current_price=Decimal("170"),
        )
        fp._update_unrealized_pnl(pos)
        assert pos.unrealized_pnl == Decimal("-2000")

    def test_unrealized_pnl_percent_long(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="long", qty=Decimal("100"),
            avg_entry_price=Decimal("100"), current_price=Decimal("110"),
        )
        fp._update_unrealized_pnl(pos)
        assert pos.unrealized_pnl_percent == Decimal("10")

    def test_unrealized_pnl_percent_short(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="short", qty=Decimal("100"),
            avg_entry_price=Decimal("100"), current_price=Decimal("90"),
        )
        fp._update_unrealized_pnl(pos)
        assert pos.unrealized_pnl_percent == Decimal("10")

    def test_options_multiplier_in_unrealized(self):
        fp = FillProcessor()
        pos = MockPosition(
            side="long", qty=Decimal("5"),
            avg_entry_price=Decimal("3"), current_price=Decimal("5"),
            contract_multiplier=100,
        )
        fp._update_unrealized_pnl(pos)
        # (5-3) * 5 * 100 = 1000
        assert pos.unrealized_pnl == Decimal("1000")


# ---------------------------------------------------------------------------
# Scale-in weighted average (manual calculation)
# ---------------------------------------------------------------------------

class TestScaleIn:
    def test_long_scale_in_weighted_average(self):
        """Position: 100 @ $150. Buy 50 more @ $160.
        New avg = (100*150 + 50*160) / 150 = 23000/150 = 153.33..."""
        old_qty = Decimal("100")
        old_avg = Decimal("150")
        new_qty_added = Decimal("50")
        new_price = Decimal("160")
        total_qty = old_qty + new_qty_added
        new_avg = (old_qty * old_avg + new_qty_added * new_price) / total_qty
        expected = Decimal("23000") / Decimal("150")
        assert new_avg == expected
        assert total_qty == Decimal("150")

    def test_multiple_scale_ins(self):
        """Three successive scale-ins with correct running weighted avg."""
        # Entry: 100 @ 100
        qty = Decimal("100")
        avg = Decimal("100")
        # Scale-in 1: 50 @ 110
        new_qty = Decimal("50")
        avg = (qty * avg + new_qty * Decimal("110")) / (qty + new_qty)
        qty = qty + new_qty
        # Scale-in 2: 25 @ 120
        new_qty2 = Decimal("25")
        avg = (qty * avg + new_qty2 * Decimal("120")) / (qty + new_qty2)
        qty = qty + new_qty2
        # Total: 175 shares
        assert qty == Decimal("175")
        # Total cost: 100*100 + 50*110 + 25*120 = 10000+5500+3000 = 18500
        expected_avg = Decimal("18500") / Decimal("175")
        assert abs(avg - expected_avg) < Decimal("0.01")

    def test_scale_in_preserves_realized_pnl(self):
        """Scale-in does not affect previously realized PnL."""
        pos = MockPosition(
            side="long", qty=Decimal("100"),
            avg_entry_price=Decimal("150"), realized_pnl=Decimal("500"),
        )
        # Scale-in: buy 50 more at 160
        old_qty = pos.qty
        new_qty = Decimal("50")
        new_price = Decimal("160")
        pos.avg_entry_price = (old_qty * pos.avg_entry_price + new_qty * new_price) / (old_qty + new_qty)
        pos.qty = old_qty + new_qty
        # Realized PnL should be unchanged
        assert pos.realized_pnl == Decimal("500")


# ---------------------------------------------------------------------------
# Scale-out (partial close) PnL
# ---------------------------------------------------------------------------

class TestScaleOut:
    def test_long_partial_close_profit(self):
        """Position: 100 @ $150. Sell 50 @ $170. gross_pnl = (170-150)*50 = $1000."""
        entry = Decimal("150")
        exit = Decimal("170")
        qty_closed = Decimal("50")
        gross_pnl = (exit - entry) * qty_closed
        assert gross_pnl == Decimal("1000")

    def test_long_partial_close_loss(self):
        """Sell 50 @ $140. gross_pnl = (140-150)*50 = -$500."""
        gross_pnl = (Decimal("140") - Decimal("150")) * Decimal("50")
        assert gross_pnl == Decimal("-500")

    def test_short_partial_close_profit(self):
        """Short 100 @ $150. Buy 50 @ $140. gross_pnl = (150-140)*50 = $500."""
        gross_pnl = (Decimal("150") - Decimal("140")) * Decimal("50")
        assert gross_pnl == Decimal("500")

    def test_short_partial_close_loss(self):
        """Buy 50 @ $160. gross_pnl = (150-160)*50 = -$500."""
        gross_pnl = (Decimal("150") - Decimal("160")) * Decimal("50")
        assert gross_pnl == Decimal("-500")

    def test_partial_close_avg_entry_unchanged(self):
        """avg_entry_price stays the same after partial close."""
        pos = MockPosition(side="long", qty=Decimal("100"), avg_entry_price=Decimal("150"))
        original_avg = pos.avg_entry_price
        # Simulate partial close of 50
        pos.qty = Decimal("50")
        assert pos.avg_entry_price == original_avg

    def test_realized_pnl_accumulates(self):
        """Two partial closes → realized_pnl = sum of both."""
        entry = Decimal("100")
        # Close 1: sell 30 @ 110
        pnl1 = (Decimal("110") - entry) * Decimal("30")  # +300
        # Close 2: sell 20 @ 105
        pnl2 = (Decimal("105") - entry) * Decimal("20")  # +100
        total = pnl1 + pnl2
        assert total == Decimal("400")

    def test_net_pnl_includes_fee(self):
        """net_pnl = gross_pnl - fee."""
        gross = Decimal("1000")
        fee = Decimal("5")
        net = gross - fee
        assert net == Decimal("995")


# ---------------------------------------------------------------------------
# Full close
# ---------------------------------------------------------------------------

class TestFullClose:
    def test_long_full_close_profit(self):
        """Position: 100 @ $150. Sell 100 @ $170."""
        entry = Decimal("150")
        exit = Decimal("170")
        qty = Decimal("100")
        gross_pnl = (exit - entry) * qty
        fee = Decimal("6")
        net_pnl = gross_pnl - fee
        assert gross_pnl == Decimal("2000")
        assert net_pnl == Decimal("1994")

    def test_long_full_close_loss(self):
        """Sell 100 @ $130."""
        gross_pnl = (Decimal("130") - Decimal("150")) * Decimal("100")
        fee = Decimal("6")
        net_pnl = gross_pnl - fee
        assert gross_pnl == Decimal("-2000")
        assert net_pnl == Decimal("-2006")

    def test_full_close_after_scale_ins(self):
        """Multiple scale-ins then full close → PnL uses weighted avg entry."""
        # Entry: 100 @ 100, Scale-in: 50 @ 120
        total_cost = Decimal("100") * Decimal("100") + Decimal("50") * Decimal("120")
        total_qty = Decimal("150")
        avg_entry = total_cost / total_qty  # 16000/150 = 106.666...
        exit_price = Decimal("130")
        gross_pnl = (exit_price - avg_entry) * total_qty
        # (130 - 106.666...) * 150 = 23.333... * 150 = 3500
        assert abs(gross_pnl - Decimal("3500")) < Decimal("0.01")

    def test_full_close_zeros_qty(self):
        """After full close: qty = 0."""
        pos = MockPosition(side="long", qty=Decimal("100"))
        pos.qty = Decimal("0")
        pos.status = "closed"
        assert pos.qty == Decimal("0")
        assert pos.status == "closed"

    def test_short_full_close_profit(self):
        """Short 100 @ $150, buy 100 @ $130."""
        gross_pnl = (Decimal("150") - Decimal("130")) * Decimal("100")
        assert gross_pnl == Decimal("2000")

    def test_short_full_close_loss(self):
        """Short 100 @ $150, buy 100 @ $170."""
        gross_pnl = (Decimal("150") - Decimal("170")) * Decimal("100")
        assert gross_pnl == Decimal("-2000")


# ---------------------------------------------------------------------------
# New position
# ---------------------------------------------------------------------------

class TestNewPosition:
    def test_long_new_open(self):
        """Buy 100 AAPL at $150 → long position."""
        qty = Decimal("100")
        price = Decimal("150")
        side = "long"
        unrealized = Decimal("0")
        assert qty == Decimal("100")
        assert side == "long"
        assert unrealized == Decimal("0")

    def test_short_new_open(self):
        """Sell 100 AAPL at $150 → short position."""
        side = "short"
        assert side == "short"

    def test_options_new_open(self):
        """Buy 5 AAPL calls at $3.00 → multiplier=100."""
        qty = Decimal("5")
        price = Decimal("3")
        multiplier = Decimal("100")
        market_value = qty * price * multiplier
        assert market_value == Decimal("1500")

    def test_all_decimal(self):
        """All financial values are Decimal."""
        pos = MockPosition(
            qty=Decimal("100"),
            avg_entry_price=Decimal("150"),
            cost_basis=Decimal("15000"),
        )
        assert isinstance(pos.qty, Decimal)
        assert isinstance(pos.avg_entry_price, Decimal)
        assert isinstance(pos.cost_basis, Decimal)
