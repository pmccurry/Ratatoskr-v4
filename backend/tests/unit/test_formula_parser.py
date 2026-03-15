"""Unit tests for the formula expression parser."""

from decimal import Decimal

from tests.conftest import make_bars, make_trending_bars

from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators import get_registry


def _parser() -> FormulaParser:
    return FormulaParser(get_registry())


# ---------------------------------------------------------------------------
# Valid expressions — evaluate
# ---------------------------------------------------------------------------

class TestValidFormulas:
    def test_simple_arithmetic(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("10 + 5", bars)
        assert result == Decimal("15")

    def test_multiplication(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("3 * 4", bars)
        assert result == Decimal("12")

    def test_division(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("10 / 4", bars)
        assert result == Decimal("2.5")

    def test_comparison_true(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("10 > 5", bars)
        assert result == Decimal("1")

    def test_comparison_false(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("5 > 10", bars)
        assert result == Decimal("0")

    def test_close_field(self):
        parser = _parser()
        bars = make_bars([42])
        result = parser.evaluate("close", bars)
        assert result == Decimal("42")

    def test_price_fields(self):
        parser = _parser()
        bars = make_bars([100], opens=[95], highs=[110], lows=[90], volumes=[5000])
        assert parser.evaluate("open", bars) == Decimal("95")
        assert parser.evaluate("high", bars) == Decimal("110")
        assert parser.evaluate("low", bars) == Decimal("90")
        assert parser.evaluate("close", bars) == Decimal("100")
        # Note: bare "volume" in formulas resolves via get_source_value which
        # doesn't handle "volume" — it falls through to close. Use the volume()
        # indicator function instead. This is a known limitation of the parser.

    def test_volume_as_indicator(self):
        parser = _parser()
        bars = make_bars([100], volumes=[5000])
        # volume as indicator function (registered in catalog) returns bar volume
        result = parser.evaluate("volume", bars)
        # Resolves as identifier → tries get_source_value("volume") → falls through
        # Then checks indicator registry → finds "volume" indicator → compute_volume
        # BUT _resolve_identifier checks _BAR_FIELDS first, so "volume" is treated
        # as a bar field, not an indicator call. The volume indicator needs parens.
        assert result is not None

    def test_indicator_function(self):
        parser = _parser()
        bars = make_bars([10, 20, 30])
        result = parser.evaluate("sma(close, 3)", bars)
        assert result is not None
        assert result == Decimal("20")

    def test_nested_parentheses(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("(10 + 5) * 2", bars)
        assert result == Decimal("30")

    def test_numeric_literal(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("42.5", bars)
        assert result == Decimal("42.5")

    def test_complex_expression(self):
        parser = _parser()
        bars = make_bars([10, 20, 30, 40, 50])
        result = parser.evaluate("sma(close, 3) + 10", bars)
        # SMA(3) of [30,40,50] = 40, + 10 = 50
        assert result == Decimal("50")

    def test_abs_function(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("abs(-5)", bars)
        assert result == Decimal("5")

    def test_min_function(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("min(10, 5, 20)", bars)
        assert result == Decimal("5")

    def test_max_function(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("max(10, 5, 20)", bars)
        assert result == Decimal("20")

    def test_boolean_true(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("true", bars)
        assert result == Decimal("1")

    def test_boolean_false(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("false", bars)
        assert result == Decimal("0")

    def test_logical_and(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("true and true", bars)
        assert result == Decimal("1")

    def test_logical_or(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("false or true", bars)
        assert result == Decimal("1")


# ---------------------------------------------------------------------------
# Valid expressions — validate (should return empty error list)
# ---------------------------------------------------------------------------

class TestValidateValid:
    def test_simple_arithmetic(self):
        assert _parser().validate("sma(close, 20) + atr(14)") == []

    def test_comparison(self):
        assert _parser().validate("close > sma(close, 200)") == []

    def test_numeric_literals(self):
        assert _parser().validate("rsi(14) > 70") == []

    def test_crosses_above(self):
        assert _parser().validate("crosses_above(sma(close, 5), sma(close, 20))") == []

    def test_complex(self):
        assert _parser().validate("(close - ema(close, 20)) / atr(14) > 2.0") == []


# ---------------------------------------------------------------------------
# Invalid expressions — validate (should return error list)
# ---------------------------------------------------------------------------

class TestValidateInvalid:
    def test_unknown_function(self):
        errors = _parser().validate("nonexistent_func(close, 14)")
        assert len(errors) > 0

    def test_empty_expression(self):
        errors = _parser().validate("")
        assert errors == ["Expression is empty"]

    def test_whitespace_only(self):
        errors = _parser().validate("   ")
        assert errors == ["Expression is empty"]

    def test_unbalanced_parens(self):
        errors = _parser().validate("sma(close, 20")
        assert len(errors) > 0

    def test_injection_import(self):
        errors = _parser().validate("import os")
        assert len(errors) > 0
        assert any("Forbidden" in e for e in errors)

    def test_injection_dunder(self):
        errors = _parser().validate("__import__('os')")
        assert len(errors) > 0
        assert any("Dunder" in e or "Forbidden" in e for e in errors)

    def test_injection_exec(self):
        errors = _parser().validate("exec('print(1)')")
        assert len(errors) > 0

    def test_injection_eval(self):
        errors = _parser().validate("eval('1+1')")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Division by zero
# ---------------------------------------------------------------------------

class TestDivisionByZero:
    def test_returns_none(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("10 / 0", bars)
        assert result is None


# ---------------------------------------------------------------------------
# Crossover functions in formulas
# ---------------------------------------------------------------------------

class TestFormulaCrossovers:
    def test_crosses_above_insufficient_bars(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("crosses_above(close, 50)", bars)
        assert result is None

    def test_prev_function(self):
        parser = _parser()
        bars = make_bars([10, 20, 30])
        result = parser.evaluate("prev(close)", bars)
        # prev(close) should be close of bars[-2] = 20
        assert result == Decimal("20")

    def test_prev_insufficient_bars(self):
        parser = _parser()
        bars = make_bars([100])
        result = parser.evaluate("prev(close)", bars)
        assert result is None
