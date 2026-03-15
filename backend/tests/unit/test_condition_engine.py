"""Unit tests for the condition engine."""

from decimal import Decimal

from tests.conftest import make_bars, make_trending_bars

from app.strategies.conditions.engine import ConditionEngine
from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators import get_registry


def _engine() -> ConditionEngine:
    registry = get_registry()
    parser = FormulaParser(registry)
    return ConditionEngine(registry, parser)


def _value_operand(val: float | int) -> dict:
    return {"type": "value", "value": val}


def _indicator_operand(key: str, params: dict | None = None, output: str | None = None) -> dict:
    op: dict = {"type": "indicator", "indicator": key, "params": params or {}}
    if output:
        op["output"] = output
    return op


def _condition(left: dict, operator: str, right: dict) -> dict:
    return {"left": left, "operator": operator, "right": right}


def _group(logic: str, conditions: list[dict]) -> dict:
    return {"logic": logic, "conditions": conditions}


# ---------------------------------------------------------------------------
# Standard comparison operators
# ---------------------------------------------------------------------------

class TestGreaterThan:
    def test_true(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(10), "greater_than", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_false(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "greater_than", _value_operand(10))
        assert _engine().evaluate(_group("and", [cond]), bars) is False

    def test_equal_false(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "greater_than", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is False


class TestLessThan:
    def test_true(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "less_than", _value_operand(10))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_false(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(10), "less_than", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is False

    def test_equal_false(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "less_than", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is False


class TestGreaterThanOrEqual:
    def test_greater(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(10), "greater_than_or_equal", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_equal(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "greater_than_or_equal", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_less(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(4), "greater_than_or_equal", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is False


class TestLessThanOrEqual:
    def test_less(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "less_than_or_equal", _value_operand(10))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_equal(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "less_than_or_equal", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_greater(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(6), "less_than_or_equal", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is False


class TestEqual:
    def test_true(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "equal", _value_operand(5))
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_false(self):
        bars = make_bars([100])
        cond = _condition(_value_operand(5), "equal", _value_operand(6))
        assert _engine().evaluate(_group("and", [cond]), bars) is False


# ---------------------------------------------------------------------------
# Range operators
# ---------------------------------------------------------------------------

class TestBetween:
    def test_in_range(self):
        bars = make_bars([100])
        cond = _condition(
            _value_operand(5),
            "between",
            {"min": 3, "max": 7},
        )
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_out_of_range(self):
        bars = make_bars([100])
        cond = _condition(
            _value_operand(2),
            "between",
            {"min": 3, "max": 7},
        )
        assert _engine().evaluate(_group("and", [cond]), bars) is False

    def test_boundary_inclusive(self):
        bars = make_bars([100])
        cond = _condition(
            _value_operand(3),
            "between",
            {"min": 3, "max": 7},
        )
        assert _engine().evaluate(_group("and", [cond]), bars) is True


class TestOutside:
    def test_outside_below(self):
        bars = make_bars([100])
        cond = _condition(
            _value_operand(2),
            "outside",
            {"min": 3, "max": 7},
        )
        assert _engine().evaluate(_group("and", [cond]), bars) is True

    def test_inside(self):
        bars = make_bars([100])
        cond = _condition(
            _value_operand(5),
            "outside",
            {"min": 3, "max": 7},
        )
        assert _engine().evaluate(_group("and", [cond]), bars) is False


# ---------------------------------------------------------------------------
# Crossover operators
# ---------------------------------------------------------------------------

class TestCrossovers:
    def test_crosses_above_simple(self):
        engine = _engine()
        # Bar 0: left=5, right=10 (below); Bar 1: left=15, right=10 (above)
        bars = make_bars([100, 200])
        cond = _condition(
            _value_operand(15),  # current
            "crosses_above",
            _value_operand(10),
        )
        # crosses_above checks prev_l <= prev_r AND curr_l > curr_r
        # With value operands, prev and current resolve to same values
        # so this is 15 <= 10 (false) → no cross
        # For a real crossover we need indicator-based operands that change with bars
        # Use indicators instead
        bars = make_bars([5, 10, 15, 20, 25])
        cond = _condition(
            _indicator_operand("sma", {"period": 2}),
            "crosses_above",
            _value_operand(17),
        )
        # SMA(2) on bars[-1:] = avg of [20,25] = 22.5
        # SMA(2) on bars[:-1] = avg of [15,20] = 17.5, comparing against 17
        # prev: 17.5 <= 17 → False; so no cross
        # Let's use clearer data
        bars = make_bars([10, 14, 18, 22])
        cond = _condition(
            _indicator_operand("sma", {"period": 2}),
            "crosses_above",
            _value_operand(16),
        )
        # SMA(2) current (18,22) = 20 > 16
        # SMA(2) previous (14,18) = 16 <= 16
        result = engine.evaluate(_group("and", [cond]), bars)
        assert result is True

    def test_crosses_above_already_above(self):
        engine = _engine()
        bars = make_bars([20, 22, 24, 26])
        cond = _condition(
            _indicator_operand("sma", {"period": 2}),
            "crosses_above",
            _value_operand(10),
        )
        # Both prev and current SMA > 10 → prev_l > prev_r → not a crossover
        result = engine.evaluate(_group("and", [cond]), bars)
        assert result is False

    def test_crosses_below_simple(self):
        engine = _engine()
        bars = make_bars([22, 18, 14, 10])
        cond = _condition(
            _indicator_operand("sma", {"period": 2}),
            "crosses_below",
            _value_operand(16),
        )
        # SMA(2) current (14,10) = 12 < 16
        # SMA(2) previous (18,14) = 16 >= 16
        result = engine.evaluate(_group("and", [cond]), bars)
        assert result is True

    def test_no_crossover_single_bar(self):
        engine = _engine()
        bars = make_bars([100])
        cond = _condition(
            _indicator_operand("close"),
            "crosses_above",
            _value_operand(50),
        )
        result = engine.evaluate(_group("and", [cond]), bars)
        assert result is False


# ---------------------------------------------------------------------------
# Condition group logic
# ---------------------------------------------------------------------------

class TestConditionGroups:
    def test_and_group_all_true(self):
        bars = make_bars([100])
        group = _group("and", [
            _condition(_value_operand(10), "greater_than", _value_operand(5)),
            _condition(_value_operand(1), "less_than", _value_operand(2)),
        ])
        assert _engine().evaluate(group, bars) is True

    def test_and_group_one_false(self):
        bars = make_bars([100])
        group = _group("and", [
            _condition(_value_operand(10), "greater_than", _value_operand(5)),
            _condition(_value_operand(3), "less_than", _value_operand(2)),
        ])
        assert _engine().evaluate(group, bars) is False

    def test_or_group_one_true(self):
        bars = make_bars([100])
        group = _group("or", [
            _condition(_value_operand(1), "greater_than", _value_operand(5)),
            _condition(_value_operand(1), "less_than", _value_operand(2)),
        ])
        assert _engine().evaluate(group, bars) is True

    def test_or_group_all_false(self):
        bars = make_bars([100])
        group = _group("or", [
            _condition(_value_operand(1), "greater_than", _value_operand(5)),
            _condition(_value_operand(3), "less_than", _value_operand(2)),
        ])
        assert _engine().evaluate(group, bars) is False

    def test_empty_conditions(self):
        bars = make_bars([100])
        group = _group("and", [])
        assert _engine().evaluate(group, bars) is True

    def test_nested_groups(self):
        bars = make_bars([100])
        inner = _group("or", [
            _condition(_value_operand(1), "greater_than", _value_operand(5)),
            _condition(_value_operand(10), "greater_than", _value_operand(5)),
        ])
        outer = _group("and", [
            _condition(_value_operand(1), "less_than", _value_operand(2)),
            inner,
        ])
        assert _engine().evaluate(outer, bars) is True


# ---------------------------------------------------------------------------
# Multi-output indicator conditions
# ---------------------------------------------------------------------------

class TestMultiOutputConditions:
    def test_bbands_close_below_upper(self):
        engine = _engine()
        bars = make_bars([50, 51, 49, 52, 48, 53, 47, 54, 46, 55,
                          50, 51, 49, 52, 48, 53, 47, 54, 46, 50])
        cond = _condition(
            _indicator_operand("close"),
            "less_than",
            _indicator_operand("bbands", {"period": 20}, output="upper"),
        )
        result = engine.evaluate(_group("and", [cond]), bars)
        assert isinstance(result, bool)

    def test_indicator_with_default_output(self):
        engine = _engine()
        bars = make_trending_bars(50, 100, 40)
        cond = _condition(
            _indicator_operand("macd", output="macd_line"),
            "greater_than",
            _value_operand(0),
        )
        result = engine.evaluate(_group("and", [cond]), bars)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Null handling
# ---------------------------------------------------------------------------

class TestNullHandling:
    def test_null_operand_returns_false(self):
        engine = _engine()
        bars = make_bars([100])
        # SMA(20) on 1 bar → None
        cond = _condition(
            _indicator_operand("sma", {"period": 20}),
            "greater_than",
            _value_operand(50),
        )
        assert engine.evaluate(_group("and", [cond]), bars) is False

    def test_unknown_indicator_returns_false(self):
        engine = _engine()
        bars = make_bars([100])
        cond = _condition(
            _indicator_operand("nonexistent"),
            "greater_than",
            _value_operand(50),
        )
        assert engine.evaluate(_group("and", [cond]), bars) is False
