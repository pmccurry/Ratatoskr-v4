"""Unit tests for strategy config validation."""

from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators import get_registry
from app.strategies.validation import StrategyValidator


def _validator() -> StrategyValidator:
    registry = get_registry()
    parser = FormulaParser(registry)
    return StrategyValidator(registry, parser)


def _minimal_valid_config() -> dict:
    """Return a minimal valid strategy config."""
    return {
        "timeframe": "1h",
        "symbols": {"mode": "explicit", "list": ["AAPL"]},
        "entry_conditions": {
            "logic": "and",
            "conditions": [
                {
                    "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
                    "operator": "less_than",
                    "right": {"type": "value", "value": 30},
                }
            ],
        },
        "stop_loss": {"type": "percent", "value": 2.0},
        "position_sizing": {"method": "percent_equity", "value": 5, "max_positions": 3},
    }


def _full_config() -> dict:
    """Return a fully populated config."""
    return {
        "timeframe": "1h",
        "lookback_bars": 200,
        "symbols": {"mode": "explicit", "list": ["AAPL", "MSFT"]},
        "entry_conditions": {
            "logic": "and",
            "conditions": [
                {
                    "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
                    "operator": "less_than",
                    "right": {"type": "value", "value": 30},
                },
                {
                    "left": {"type": "indicator", "indicator": "sma", "params": {"period": 50}},
                    "operator": "greater_than",
                    "right": {"type": "indicator", "indicator": "sma", "params": {"period": 200}},
                },
            ],
        },
        "exit_conditions": {
            "logic": "or",
            "conditions": [
                {
                    "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
                    "operator": "greater_than",
                    "right": {"type": "value", "value": 70},
                },
            ],
        },
        "stop_loss": {"type": "percent", "value": 2.0},
        "take_profit": {"type": "percent", "value": 6.0},
        "position_sizing": {"method": "percent_equity", "value": 5, "max_positions": 3},
    }


# ---------------------------------------------------------------------------
# Valid configs
# ---------------------------------------------------------------------------

class TestValidConfigs:
    def test_minimal_valid(self):
        result = _validator().validate(_minimal_valid_config())
        assert result.valid is True
        assert len(result.errors) == 0

    def test_full_config(self):
        result = _validator().validate(_full_config())
        assert result.valid is True
        assert len(result.errors) == 0

    def test_explicit_symbols_mode(self):
        config = _minimal_valid_config()
        config["symbols"] = {"mode": "explicit", "list": ["AAPL", "MSFT", "GOOGL"]}
        result = _validator().validate(config)
        assert result.valid is True

    def test_watchlist_symbols_mode(self):
        config = _minimal_valid_config()
        config["symbols"] = {"mode": "watchlist"}
        result = _validator().validate(config)
        assert result.valid is True

    def test_all_timeframes(self):
        for tf in ("1m", "5m", "15m", "1h", "4h"):
            config = _minimal_valid_config()
            config["timeframe"] = tf
            result = _validator().validate(config)
            assert result.valid is True, f"Timeframe {tf} should be valid"

    def test_all_position_sizing_methods(self):
        for method in ("fixed_qty", "fixed_dollar", "percent_equity", "risk_based"):
            config = _minimal_valid_config()
            config["position_sizing"]["method"] = method
            result = _validator().validate(config)
            assert result.valid is True, f"Sizing method {method} should be valid"

    def test_with_exit_conditions_only(self):
        config = _minimal_valid_config()
        del config["stop_loss"]
        config["exit_conditions"] = {
            "logic": "and",
            "conditions": [
                {
                    "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
                    "operator": "greater_than",
                    "right": {"type": "value", "value": 70},
                },
            ],
        }
        result = _validator().validate(config)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Invalid configs
# ---------------------------------------------------------------------------

class TestInvalidConfigs:
    def test_missing_timeframe(self):
        config = _minimal_valid_config()
        del config["timeframe"]
        result = _validator().validate(config)
        assert result.valid is False
        assert any("timeframe" in e.get("field", "").lower() or "timeframe" in e.get("message", "").lower()
                    for e in result.errors)

    def test_invalid_timeframe(self):
        config = _minimal_valid_config()
        config["timeframe"] = "3h"
        result = _validator().validate(config)
        assert result.valid is False

    def test_no_symbols(self):
        config = _minimal_valid_config()
        del config["symbols"]
        result = _validator().validate(config)
        assert result.valid is False

    def test_explicit_mode_empty_list(self):
        config = _minimal_valid_config()
        config["symbols"] = {"mode": "explicit", "list": []}
        result = _validator().validate(config)
        assert result.valid is False

    def test_no_entry_conditions(self):
        config = _minimal_valid_config()
        del config["entry_conditions"]
        result = _validator().validate(config)
        assert result.valid is False

    def test_empty_entry_conditions(self):
        config = _minimal_valid_config()
        config["entry_conditions"] = {"logic": "and", "conditions": []}
        result = _validator().validate(config)
        assert result.valid is False

    def test_no_exit_mechanism(self):
        config = _minimal_valid_config()
        del config["stop_loss"]
        # No exit_conditions, no stop_loss, no take_profit
        result = _validator().validate(config)
        assert result.valid is False

    def test_unknown_indicator(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"]["indicator"] = "made_up_indicator"
        result = _validator().validate(config)
        assert result.valid is False
        assert any("Unknown indicator" in e.get("message", "") for e in result.errors)

    def test_invalid_operator(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["operator"] = "kinda_greater"
        result = _validator().validate(config)
        assert result.valid is False

    def test_indicator_param_out_of_range_high(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"]["params"]["period"] = 500
        result = _validator().validate(config)
        assert result.valid is False
        assert any("must be <=" in e.get("message", "") for e in result.errors)

    def test_indicator_param_out_of_range_low(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"]["params"]["period"] = 1
        result = _validator().validate(config)
        assert result.valid is False
        assert any("must be >=" in e.get("message", "") for e in result.errors)

    def test_no_position_sizing(self):
        config = _minimal_valid_config()
        del config["position_sizing"]
        result = _validator().validate(config)
        assert result.valid is False

    def test_invalid_sizing_method(self):
        config = _minimal_valid_config()
        config["position_sizing"]["method"] = "yolo"
        result = _validator().validate(config)
        assert result.valid is False

    def test_max_positions_zero(self):
        config = _minimal_valid_config()
        config["position_sizing"]["max_positions"] = 0
        result = _validator().validate(config)
        assert result.valid is False


# ---------------------------------------------------------------------------
# Risk sanity checks
# ---------------------------------------------------------------------------

class TestRiskSanity:
    def test_stop_loss_too_small(self):
        config = _minimal_valid_config()
        config["stop_loss"] = {"type": "percent", "value": 0.05}
        result = _validator().validate(config)
        assert result.valid is False

    def test_stop_loss_too_large(self):
        config = _minimal_valid_config()
        config["stop_loss"] = {"type": "percent", "value": 60}
        result = _validator().validate(config)
        assert result.valid is False

    def test_stop_loss_warning_high(self):
        config = _minimal_valid_config()
        config["stop_loss"] = {"type": "percent", "value": 15}
        result = _validator().validate(config)
        assert result.valid is True
        assert any("high" in w.get("message", "").lower() for w in result.warnings)

    def test_position_size_over_100_percent(self):
        config = _minimal_valid_config()
        config["position_sizing"] = {"method": "percent_equity", "value": 150, "max_positions": 1}
        result = _validator().validate(config)
        assert result.valid is False

    def test_position_size_warning_high(self):
        config = _minimal_valid_config()
        config["position_sizing"] = {"method": "percent_equity", "value": 30, "max_positions": 1}
        result = _validator().validate(config)
        assert result.valid is True
        assert any("high" in w.get("message", "").lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Multi-output indicator validation
# ---------------------------------------------------------------------------

class TestMultiOutputValidation:
    def test_missing_output_for_macd(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"] = {
            "type": "indicator",
            "indicator": "macd",
            "params": {"fast": 12, "slow": 26, "signal": 9},
            # Missing "output" field
        }
        result = _validator().validate(config)
        assert result.valid is False
        assert any("output" in e.get("message", "").lower() for e in result.errors)

    def test_invalid_output_for_bbands(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"] = {
            "type": "indicator",
            "indicator": "bbands",
            "params": {"period": 20},
            "output": "nonexistent",
        }
        result = _validator().validate(config)
        assert result.valid is False

    def test_valid_output_for_stochastic(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"] = {
            "type": "indicator",
            "indicator": "stochastic",
            "params": {"k_period": 14, "d_period": 3, "slowing": 3},
            "output": "k",
        }
        result = _validator().validate(config)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Formula in conditions
# ---------------------------------------------------------------------------

class TestFormulaValidation:
    def test_valid_formula_operand(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"] = {
            "type": "formula",
            "expression": "close > sma(close, 20)",
        }
        result = _validator().validate(config)
        assert result.valid is True

    def test_invalid_formula_operand(self):
        config = _minimal_valid_config()
        config["entry_conditions"]["conditions"][0]["left"] = {
            "type": "formula",
            "expression": "",
        }
        result = _validator().validate(config)
        assert result.valid is False


# ---------------------------------------------------------------------------
# Filtered symbol mode
# ---------------------------------------------------------------------------

class TestFilteredSymbolMode:
    def test_filtered_without_filters(self):
        config = _minimal_valid_config()
        config["symbols"] = {"mode": "filtered"}
        result = _validator().validate(config)
        assert result.valid is False
        assert any("filter" in e.get("message", "").lower() for e in result.errors)

    def test_filtered_with_filters(self):
        config = _minimal_valid_config()
        config["symbols"] = {"mode": "filtered", "filters": {"min_volume": 1000000}}
        result = _validator().validate(config)
        assert result.valid is True
