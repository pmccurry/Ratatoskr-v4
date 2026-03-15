"""Unit tests for fill simulation — slippage, fees, and net value."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest

from app.paper_trading.fill_simulation.slippage import SlippageModel
from app.paper_trading.fill_simulation.fees import FeeModel


# ---------------------------------------------------------------------------
# Mock config for fee tests
# ---------------------------------------------------------------------------

@dataclass
class MockPaperTradingConfig:
    slippage_bps_equities: Decimal = Decimal("5")
    slippage_bps_forex: Decimal = Decimal("2")
    slippage_bps_options: Decimal = Decimal("10")
    fee_per_trade_equities: Decimal = Decimal("0")
    fee_spread_bps_forex: Decimal = Decimal("15")
    fee_per_trade_options: Decimal = Decimal("0")
    default_contract_multiplier: int = 100
    initial_cash: Decimal = Decimal("100000")


# ---------------------------------------------------------------------------
# Slippage
# ---------------------------------------------------------------------------

class TestSlippage:
    def test_buy_slippage_increases_price(self):
        model = SlippageModel()
        price, _ = model.apply(Decimal("100"), "buy", Decimal("5"))
        assert price > Decimal("100")
        assert price == Decimal("100.05")

    def test_sell_slippage_decreases_price(self):
        model = SlippageModel()
        price, _ = model.apply(Decimal("100"), "sell", Decimal("5"))
        assert price < Decimal("100")
        assert price == Decimal("99.95")

    def test_zero_slippage(self):
        model = SlippageModel()
        price, amount = model.apply(Decimal("100"), "buy", Decimal("0"))
        assert price == Decimal("100")
        assert amount == Decimal("0")

    def test_slippage_amount_calculation(self):
        model = SlippageModel()
        price, amount = model.apply(Decimal("100"), "buy", Decimal("5"))
        assert amount == abs(price - Decimal("100"))
        assert amount == Decimal("0.05")

    def test_slippage_amount_sell(self):
        model = SlippageModel()
        price, amount = model.apply(Decimal("100"), "sell", Decimal("5"))
        assert amount == Decimal("0.05")

    def test_slippage_per_market_equities(self):
        model = SlippageModel()
        price, _ = model.apply(Decimal("100"), "buy", Decimal("5"))
        # 5bps = 0.05%
        expected = Decimal("100") * (Decimal("1") + Decimal("5") / Decimal("10000"))
        assert price == expected

    def test_slippage_per_market_forex(self):
        model = SlippageModel()
        price, _ = model.apply(Decimal("1.25000"), "buy", Decimal("2"))
        expected = Decimal("1.25000") * (Decimal("1") + Decimal("2") / Decimal("10000"))
        assert price == expected

    def test_slippage_per_market_options(self):
        model = SlippageModel()
        price, _ = model.apply(Decimal("3.50"), "buy", Decimal("10"))
        expected = Decimal("3.50") * (Decimal("1") + Decimal("10") / Decimal("10000"))
        assert price == expected

    def test_returns_decimal(self):
        model = SlippageModel()
        price, amount = model.apply(Decimal("100"), "buy", Decimal("5"))
        assert isinstance(price, Decimal)
        assert isinstance(amount, Decimal)


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------

class TestFees:
    def test_flat_fee_equities(self):
        model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_equities=Decimal("0"))
        fee = model.calculate(Decimal("5000"), "equities", config)
        assert fee == Decimal("0")

    def test_flat_fee_equities_nonzero(self):
        model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_equities=Decimal("1.00"))
        fee = model.calculate(Decimal("5000"), "equities", config)
        assert fee == Decimal("1.00")

    def test_spread_bps_forex(self):
        model = FeeModel()
        config = MockPaperTradingConfig(fee_spread_bps_forex=Decimal("15"))
        fee = model.calculate(Decimal("10000"), "forex", config)
        # 15bps of 10000 = 10000 * 15 / 10000 = 15
        assert fee == Decimal("15")

    def test_flat_fee_options(self):
        model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_options=Decimal("0.65"))
        fee = model.calculate(Decimal("300"), "options", config)
        assert fee == Decimal("0.65")

    def test_zero_fee(self):
        model = FeeModel()
        config = MockPaperTradingConfig()
        fee = model.calculate(Decimal("5000"), "equities", config)
        assert fee == Decimal("0")

    def test_returns_decimal(self):
        model = FeeModel()
        config = MockPaperTradingConfig()
        fee = model.calculate(Decimal("5000"), "forex", config)
        assert isinstance(fee, Decimal)


# ---------------------------------------------------------------------------
# Net value calculation (slippage + fee combined)
# ---------------------------------------------------------------------------

class TestNetValue:
    def test_buy_net_value_greater_than_gross(self):
        slippage = SlippageModel()
        fee_model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_equities=Decimal("1.00"))

        ref_price = Decimal("50")
        qty = Decimal("100")
        exec_price, _ = slippage.apply(ref_price, "buy", Decimal("5"))
        gross_value = qty * exec_price
        fee = fee_model.calculate(gross_value, "equities", config)
        net_value = gross_value + fee  # Buy: pay more
        assert net_value > gross_value

    def test_sell_net_value_less_than_gross(self):
        slippage = SlippageModel()
        fee_model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_equities=Decimal("1.00"))

        ref_price = Decimal("50")
        qty = Decimal("100")
        exec_price, _ = slippage.apply(ref_price, "sell", Decimal("5"))
        gross_value = qty * exec_price
        fee = fee_model.calculate(gross_value, "equities", config)
        net_value = gross_value - fee  # Sell: receive less
        assert net_value < gross_value

    def test_full_buy_calculation(self):
        """Buy 100 shares at $50, 5bps slippage, $1 fee."""
        slippage = SlippageModel()
        fee_model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_equities=Decimal("1.00"))

        ref_price = Decimal("50")
        qty = Decimal("100")
        exec_price, _ = slippage.apply(ref_price, "buy", Decimal("5"))
        # exec_price = 50 * 1.0005 = 50.025
        assert exec_price == Decimal("50.0250")
        gross_value = qty * exec_price
        assert gross_value == Decimal("5002.50")
        fee = fee_model.calculate(gross_value, "equities", config)
        assert fee == Decimal("1.00")
        net_value = gross_value + fee
        assert net_value == Decimal("5003.50")

    def test_zero_fee_net_equals_gross(self):
        slippage = SlippageModel()
        fee_model = FeeModel()
        config = MockPaperTradingConfig()

        exec_price, _ = slippage.apply(Decimal("100"), "buy", Decimal("0"))
        gross_value = Decimal("100") * exec_price
        fee = fee_model.calculate(gross_value, "equities", config)
        net_value = gross_value + fee
        assert net_value == gross_value  # $0 fee


# ---------------------------------------------------------------------------
# Options fill
# ---------------------------------------------------------------------------

class TestOptionsFill:
    def test_options_contract_multiplier(self):
        """Options qty=1 at $3.00 → gross_value = 1 * 3.00 * 100 = 300."""
        slippage = SlippageModel()
        exec_price, _ = slippage.apply(Decimal("3.00"), "buy", Decimal("0"))
        multiplier = Decimal("100")
        qty = Decimal("1")
        gross_value = qty * exec_price * multiplier
        assert gross_value == Decimal("300")

    def test_options_slippage(self):
        """10bps slippage on options premium."""
        slippage = SlippageModel()
        exec_price, amount = slippage.apply(Decimal("3.00"), "buy", Decimal("10"))
        # 10bps of 3.00 = 0.003
        assert exec_price > Decimal("3.00")
        expected = Decimal("3.00") * (Decimal("1") + Decimal("10") / Decimal("10000"))
        assert exec_price == expected

    def test_options_full_calculation(self):
        """Buy 5 calls at $3.00, 10bps slippage, $0.65 fee, multiplier=100."""
        slippage = SlippageModel()
        fee_model = FeeModel()
        config = MockPaperTradingConfig(fee_per_trade_options=Decimal("0.65"))

        exec_price, _ = slippage.apply(Decimal("3.00"), "buy", Decimal("10"))
        qty = Decimal("5")
        multiplier = Decimal("100")
        gross_value = qty * exec_price * multiplier
        fee = fee_model.calculate(gross_value, "options", config)
        net_value = gross_value + fee

        assert fee == Decimal("0.65")
        assert net_value == gross_value + Decimal("0.65")
        assert isinstance(net_value, Decimal)
