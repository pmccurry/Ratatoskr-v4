# TASK-026 — Test Infrastructure + Strategy Module Unit Tests

## Goal

Set up the pytest infrastructure (conftest, fixtures, config) and write unit tests for the strategy module's core logic: indicator library, condition engine, formula parser, and strategy validation. These are pure-logic tests with no database dependency.

## Depends On

TASK-025

## Scope

**In scope:**
- pytest configuration (`pyproject.toml` [tool.pytest] section or `pytest.ini`)
- Root `conftest.py` with shared fixtures and test utilities
- `tests/unit/conftest.py` with unit-test-specific setup
- `tests/unit/test_indicator_library.py`
- `tests/unit/test_condition_engine.py`
- `tests/unit/test_formula_parser.py`
- `tests/unit/test_strategy_validation.py`

**Out of scope:**
- Integration tests (TASK-028)
- Frontend tests
- Tests requiring a database
- Application code changes

---

## Deliverables

### D1 — pytest configuration

Add to `backend/pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

Ensure these test dependencies are in the dev dependencies (add if missing):
- pytest
- pytest-asyncio
- pytest-cov

### D2 — Root conftest (`backend/tests/conftest.py`)

```python
"""
Root conftest — shared fixtures available to all test layers.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Helper to build OHLCV bar data for indicator tests
def make_bars(closes: list[float], *, 
              opens: list[float] | None = None,
              highs: list[float] | None = None,
              lows: list[float] | None = None,
              volumes: list[float] | None = None) -> list[dict]:
    """Build bar dicts from close prices. Other fields derived if not provided."""
    bars = []
    for i, close in enumerate(closes):
        bars.append({
            "open": Decimal(str(opens[i] if opens else close)),
            "high": Decimal(str(highs[i] if highs else close * 1.01)),
            "low": Decimal(str(lows[i] if lows else close * 0.99)),
            "close": Decimal(str(close)),
            "volume": Decimal(str(volumes[i] if volumes else 1000000)),
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i),
        })
    return bars
```

Also create `backend/tests/__init__.py` and `backend/tests/unit/__init__.py` (empty).

### D3 — `tests/unit/test_indicator_library.py`

Test every MVP indicator. Each test verifies computation against known values.

**Indicators to test (from strategy_module_spec.md):**

| Indicator | Key test cases |
|-----------|---------------|
| SMA | Basic average of N closes; verify SMA(3) on [10, 20, 30] = 20; insufficient data returns None |
| EMA | Verify EMA converges; first value equals SMA seed; EMA(10) on known series matches expected |
| RSI | RSI(14) on all-up data → near 100; all-down → near 0; flat → 50; insufficient data → None |
| MACD | Verify 3 outputs (macd_line, signal_line, histogram); histogram = macd - signal; sign changes |
| Stochastic | K and D values; K=100 when close=high of range; K=0 when close=low of range |
| ADX | Trending market → high ADX; choppy → low ADX; returns value in 0-100 range |
| Bollinger Bands | Middle = SMA; upper = middle + std_dev*σ; lower = middle - std_dev*σ; close between bands normally |
| ATR | Known range → known ATR; single bar ATR = high-low |
| VWAP | VWAP of single bar = typical price; cumulative VWAP weighted by volume |
| OBV | Up close → add volume; down close → subtract volume; flat → no change |
| Volume SMA | Same as SMA but on volume field |

**Test structure per indicator:**

```python
class TestSMA:
    def test_basic_computation(self):
        """SMA(3) on [10, 20, 30, 40] → [None, None, 20, 30]"""
        
    def test_insufficient_data(self):
        """SMA(20) on 5 bars → None"""
        
    def test_single_value(self):
        """SMA(1) on [50] → 50"""
        
    def test_decimal_precision(self):
        """Results are Decimal, not float"""
```

**Import the actual indicator functions** from `backend/app/strategies/indicators/` (wherever they live). If indicators are registered in a catalog, import from there.

### D4 — `tests/unit/test_condition_engine.py`

Test every operator and edge case in the condition engine.

**Operators to test (from strategy_module_spec.md §Supported Operators):**

| Operator | Test cases |
|----------|-----------|
| `greater_than` | 10 > 5 → True; 5 > 10 → False; 5 > 5 → False |
| `less_than` | 5 < 10 → True; 10 < 5 → False; 5 < 5 → False |
| `greater_than_or_equal` | 10 >= 5 → True; 5 >= 5 → True; 4 >= 5 → False |
| `less_than_or_equal` | 5 <= 10 → True; 5 <= 5 → True; 6 <= 5 → False |
| `equal` | 5 == 5 → True; 5 == 6 → False |
| `crosses_above` | Previous: left < right, current: left > right → True; both above → False; need 2+ bars |
| `crosses_below` | Previous: left > right, current: left < right → True |
| `between` | 5 between [3, 7] → True; 2 between [3, 7] → False; boundary → True (inclusive) |
| `outside` | 2 outside [3, 7] → True; 5 outside [3, 7] → False |

**Condition group logic:**

```python
class TestConditionGroups:
    def test_and_group_all_true(self):
        """AND group: all conditions true → group is true"""

    def test_and_group_one_false(self):
        """AND group: one false → group is false"""

    def test_or_group_one_true(self):
        """OR group: one true → group is true"""

    def test_or_group_all_false(self):
        """OR group: all false → group is false"""

    def test_nested_groups(self):
        """Entry conditions AND exit conditions evaluated independently"""

    def test_empty_conditions(self):
        """Empty condition group → no signal"""
```

**Crossover tests (need bar history):**

```python
class TestCrossovers:
    def test_crosses_above_simple(self):
        """SMA(5) crosses above SMA(20) — was below, now above"""

    def test_crosses_above_already_above(self):
        """Already above → not a crossover"""

    def test_crosses_below_simple(self):
        """Price crosses below EMA — was above, now below"""

    def test_no_crossover_on_first_bar(self):
        """First bar cannot be a crossover (no previous)"""
```

**Multi-output indicator conditions:**

```python
class TestMultiOutputConditions:
    def test_macd_line_crosses_signal(self):
        """MACD.macd_line crosses_above MACD.signal_line"""

    def test_stochastic_k_greater_than_d(self):
        """Stochastic.k > Stochastic.d"""

    def test_bbands_close_below_lower(self):
        """close < BBands.lower"""
```

### D5 — `tests/unit/test_formula_parser.py`

Test the formula expression parser (Tier 2 strategy definitions).

**Valid expression tests:**

```python
class TestValidFormulas:
    def test_simple_arithmetic(self):
        """sma(close, 20) + atr(14)"""

    def test_nested_functions(self):
        """ema(rsi(14), 5)"""

    def test_comparison(self):
        """close > sma(close, 200)"""

    def test_crossover_function(self):
        """crosses_above(sma(close, 5), sma(close, 20))"""

    def test_price_fields(self):
        """open, high, low, close, volume all valid"""

    def test_numeric_literals(self):
        """rsi(14) > 70"""

    def test_complex_expression(self):
        """(sma(close, 50) - sma(close, 200)) / atr(14) > 2.0"""
```

**Invalid expression tests:**

```python
class TestInvalidFormulas:
    def test_unknown_function(self):
        """nonexistent_func(close, 14) → validation error"""

    def test_wrong_arg_count(self):
        """sma(close) → missing period arg"""

    def test_param_out_of_range(self):
        """rsi(500) → period exceeds max (200)"""

    def test_empty_expression(self):
        """'' → validation error"""

    def test_unbalanced_parens(self):
        """sma(close, 20 → parse error"""

    def test_division_by_zero_literal(self):
        """close / 0 → validation error or handled"""

    def test_injection_attempt(self):
        """__import__('os').system('rm -rf /') → rejected"""
```

### D6 — `tests/unit/test_strategy_validation.py`

Test the strategy config validation logic.

**Valid strategy configs:**

```python
class TestValidConfigs:
    def test_minimal_valid_strategy(self):
        """Name, market, timeframe, one symbol, one entry condition → valid"""

    def test_all_fields_populated(self):
        """Full config with entry, exit, SL, TP, position sizing → valid"""

    def test_explicit_symbols_mode(self):
        """Symbols mode = explicit with list of symbols → valid"""

    def test_filter_symbols_mode(self):
        """Symbols mode = filter with criteria → valid"""

    def test_all_position_sizing_methods(self):
        """fixed_qty, fixed_dollar, percent_equity, risk_based → all valid"""
```

**Invalid strategy configs:**

```python
class TestInvalidConfigs:
    def test_missing_name(self):
        """No name → validation error"""

    def test_missing_market(self):
        """No market → validation error"""

    def test_invalid_timeframe(self):
        """timeframe = '3h' (not supported) → validation error"""

    def test_no_symbols(self):
        """explicit mode with empty symbol list → validation error"""

    def test_no_entry_conditions(self):
        """No entry condition groups → validation error"""

    def test_indicator_param_out_of_range(self):
        """RSI period = 500 → validation error"""

    def test_unknown_indicator(self):
        """indicator = 'made_up' → validation error"""

    def test_invalid_operator(self):
        """operator = 'kinda_greater' → validation error"""

    def test_stop_loss_negative(self):
        """stop_loss_percent = -5 → validation error"""

    def test_position_sizing_zero(self):
        """fixed_qty = 0 → validation error"""
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | pytest config exists in `pyproject.toml` with correct settings |
| AC2 | Root `conftest.py` exists with `make_bars` helper and shared utilities |
| AC3 | `tests/__init__.py` and `tests/unit/__init__.py` exist |
| AC4 | All 11 MVP indicators have at least 3 test cases each (basic, edge case, insufficient data) |
| AC5 | All 9 condition operators have at least 2 test cases each (true case, false case) |
| AC6 | Crossover operators test both "is a crossover" and "not a crossover" scenarios |
| AC7 | Condition group AND/OR logic tested (all-true, one-false, all-false) |
| AC8 | Formula parser tests cover at least 5 valid and 5 invalid expressions |
| AC9 | Strategy validation tests cover at least 5 valid and 8 invalid configs |
| AC10 | All tests are pure unit tests — no database, no network, no file I/O |
| AC11 | All tests use `Decimal` for financial values (not float) |
| AC12 | `pytest tests/unit/ -v` runs without import errors (tests may fail if implementations have bugs — that's acceptable, the test code itself must be correct) |
| AC13 | No application code modified |
| AC14 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/tests/__init__.py` | Package marker |
| `backend/tests/conftest.py` | Root fixtures and helpers |
| `backend/tests/unit/__init__.py` | Package marker |
| `backend/tests/unit/test_indicator_library.py` | Indicator computation tests |
| `backend/tests/unit/test_condition_engine.py` | Condition evaluation tests |
| `backend/tests/unit/test_formula_parser.py` | Formula parsing tests |
| `backend/tests/unit/test_strategy_validation.py` | Config validation tests |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/pyproject.toml` | Add `[tool.pytest.ini_options]` and test dependencies if missing |

## References

- cross_cutting_specs.md §6 — Testing Strategy
- strategy_module_spec.md §Indicator Catalog (all indicators with params)
- strategy_module_spec.md §Supported Operators (all 9 operators)
- strategy_module_spec.md §Formula Expression Language
- strategy_module_spec.md §Strategy Validation
