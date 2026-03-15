"""Strategy config validation — comprehensive checks at save time."""

import logging
import re

from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators.registry import IndicatorRegistry
from app.strategies.schemas import StrategyValidationResponse

logger = logging.getLogger(__name__)

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h"}
_VALID_OPERATORS = {
    "greater_than", "less_than", "greater_than_or_equal",
    "less_than_or_equal", "equal", "crosses_above", "crosses_below",
    "between", "outside",
}
_VALID_OPERAND_TYPES = {"indicator", "formula", "value"}
_VALID_SL_TP_TYPES = {"percent", "atr_multiple", "fixed", "risk_multiple"}
_VALID_SIZING_METHODS = {"fixed_qty", "fixed_dollar", "percent_equity", "risk_based"}
_VALID_SYMBOL_MODES = {"explicit", "watchlist", "filtered"}

_CAMEL_TO_SNAKE_RE = re.compile(r"(?<!^)(?=[A-Z])")


def normalize_config_keys(config: dict) -> dict:
    """Recursively convert camelCase config keys to snake_case.

    The frontend sends camelCase (entryConditions, positionSizing) but the
    backend validators and runner expect snake_case (entry_conditions,
    position_sizing).  Normalising once at the boundary lets all downstream
    code use a single convention.
    """

    def _to_snake(name: str) -> str:
        return _CAMEL_TO_SNAKE_RE.sub("_", name).lower()

    def _walk(obj):  # noqa: ANN202
        if isinstance(obj, dict):
            return {_to_snake(k): _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(item) for item in obj]
        return obj

    return _walk(config)


class StrategyValidator:
    """Validates strategy configuration at save time."""

    def __init__(self, registry: IndicatorRegistry, formula_parser: FormulaParser):
        self._registry = registry
        self._parser = formula_parser

    def validate(self, config: dict) -> StrategyValidationResponse:
        config = normalize_config_keys(config)
        errors: list[dict] = []
        warnings: list[dict] = []

        self._validate_completeness(config, errors, warnings)
        self._validate_indicators(config, errors, warnings)
        self._validate_formulas(config, errors, warnings)
        self._validate_symbols(config, errors, warnings)
        self._validate_risk_sanity(config, errors, warnings)

        entry_conditions = config.get("entry_conditions")
        if entry_conditions:
            self._validate_conditions(entry_conditions, "entry_conditions", errors, warnings)

        exit_conditions = config.get("exit_conditions")
        if exit_conditions:
            self._validate_conditions(exit_conditions, "exit_conditions", errors, warnings)

        return StrategyValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_completeness(self, config: dict, errors: list, warnings: list) -> None:
        entry = config.get("entry_conditions")
        if not entry or not entry.get("conditions"):
            errors.append({
                "field": "entry_conditions",
                "message": "At least one entry condition is required",
                "severity": "error",
            })

        exit_cond = config.get("exit_conditions")
        stop_loss = config.get("stop_loss")
        take_profit = config.get("take_profit")
        has_exit = bool(
            (exit_cond and exit_cond.get("conditions"))
            or (stop_loss and stop_loss.get("value"))
            or (take_profit and take_profit.get("value"))
        )
        if not has_exit:
            errors.append({
                "field": "exit",
                "message": "At least one exit mechanism required (exit conditions, stop loss, or take profit)",
                "severity": "error",
            })

        sizing = config.get("position_sizing")
        if not sizing:
            errors.append({
                "field": "position_sizing",
                "message": "Position sizing must be defined",
                "severity": "error",
            })
        elif sizing.get("method") not in _VALID_SIZING_METHODS:
            errors.append({
                "field": "position_sizing.method",
                "message": f"Invalid sizing method. Must be one of: {', '.join(sorted(_VALID_SIZING_METHODS))}",
                "severity": "error",
            })

        symbols = config.get("symbols")
        if not symbols:
            errors.append({
                "field": "symbols",
                "message": "Symbol selection must be defined",
                "severity": "error",
            })
        else:
            if isinstance(symbols, list):
                symbol_list = symbols
                mode = "specific"
            else:
                mode = symbols.get("mode", "specific")
                symbol_list = symbols.get("list") or symbols.get("symbols", [])
            if mode in ("explicit", "specific") and not symbol_list:
                errors.append({
                    "field": "symbols.list",
                    "message": "At least one symbol required when mode is 'explicit'",
                    "severity": "error",
                })

        timeframe = config.get("timeframe")
        if not timeframe:
            errors.append({
                "field": "timeframe",
                "message": "Timeframe must be set",
                "severity": "error",
            })
        elif timeframe not in _VALID_TIMEFRAMES:
            errors.append({
                "field": "timeframe",
                "message": f"Invalid timeframe. Must be one of: {', '.join(sorted(_VALID_TIMEFRAMES))}",
                "severity": "error",
            })

        lookback = config.get("lookback_bars", 0)
        max_period = self._get_max_indicator_period(config)
        if max_period > 0 and lookback < max_period:
            warnings.append({
                "field": "lookback_bars",
                "message": f"lookback_bars ({lookback}) is less than the maximum indicator period ({max_period}). Indicators may not have enough data.",
                "severity": "warning",
            })

    def _get_max_indicator_period(self, config: dict) -> int:
        max_p = 0
        for group_key in ("entry_conditions", "exit_conditions"):
            group = config.get(group_key)
            if group:
                max_p = max(max_p, self._extract_max_period(group))
        return max_p

    def _extract_max_period(self, group: dict) -> int:
        max_p = 0
        for item in group.get("conditions", []):
            if "logic" in item and "conditions" in item:
                max_p = max(max_p, self._extract_max_period(item))
            else:
                for side in ("left", "right"):
                    operand = item.get(side, {})
                    if isinstance(operand, dict) and operand.get("type") == "indicator":
                        params = operand.get("params", {})
                        for pname in ("period", "slow", "k_period"):
                            val = params.get(pname)
                            if val is not None:
                                max_p = max(max_p, int(val))
        return max_p

    def _validate_indicators(self, config: dict, errors: list, warnings: list) -> None:
        for group_key in ("entry_conditions", "exit_conditions"):
            group = config.get(group_key)
            if group:
                self._validate_indicators_in_group(group, group_key, errors, warnings)

    def _validate_indicators_in_group(
        self, group: dict, path: str, errors: list, warnings: list
    ) -> None:
        for i, item in enumerate(group.get("conditions", [])):
            item_path = f"{path}[{i}]"
            if "logic" in item and "conditions" in item:
                self._validate_indicators_in_group(item, item_path, errors, warnings)
            else:
                for side in ("left", "right"):
                    operand = item.get(side, {})
                    if isinstance(operand, dict) and operand.get("type") == "indicator":
                        self._validate_single_indicator(
                            operand, f"{item_path}.{side}", errors, warnings
                        )

    def _validate_single_indicator(
        self, operand: dict, path: str, errors: list, warnings: list
    ) -> None:
        key = operand.get("indicator", "")
        defn = self._registry.get(key)
        if defn is None:
            errors.append({
                "field": f"{path}.indicator",
                "message": f"Unknown indicator: '{key}'",
                "severity": "error",
            })
            return

        params = operand.get("params", {})
        for pdef in defn.params:
            val = params.get(pdef.name)
            if val is None:
                continue
            if pdef.type == "int":
                try:
                    int_val = int(val)
                except (TypeError, ValueError):
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{pdef.name} must be an integer, got {val}",
                        "severity": "error",
                    })
                    continue
                if pdef.min is not None and int_val < pdef.min:
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{key} {pdef.name} must be >= {pdef.min}, got {int_val}",
                        "severity": "error",
                    })
                if pdef.max is not None and int_val > pdef.max:
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{key} {pdef.name} must be <= {pdef.max}, got {int_val}",
                        "severity": "error",
                    })
            elif pdef.type == "float":
                try:
                    float_val = float(val)
                except (TypeError, ValueError):
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{pdef.name} must be a number, got {val}",
                        "severity": "error",
                    })
                    continue
                if pdef.min is not None and float_val < pdef.min:
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{key} {pdef.name} must be >= {pdef.min}, got {float_val}",
                        "severity": "error",
                    })
                if pdef.max is not None and float_val > pdef.max:
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{key} {pdef.name} must be <= {pdef.max}, got {float_val}",
                        "severity": "error",
                    })
            elif pdef.type == "select" and pdef.options:
                if val not in pdef.options:
                    errors.append({
                        "field": f"{path}.params.{pdef.name}",
                        "message": f"{pdef.name} must be one of: {', '.join(pdef.options)}, got '{val}'",
                        "severity": "error",
                    })

        if len(defn.outputs) > 1:
            output = operand.get("output")
            if not output:
                errors.append({
                    "field": f"{path}.output",
                    "message": f"Multi-output indicator '{key}' requires an output field. Options: {', '.join(defn.outputs)}",
                    "severity": "error",
                })
            elif output not in defn.outputs:
                errors.append({
                    "field": f"{path}.output",
                    "message": f"Invalid output '{output}' for indicator '{key}'. Options: {', '.join(defn.outputs)}",
                    "severity": "error",
                })

    def _validate_formulas(self, config: dict, errors: list, warnings: list) -> None:
        for group_key in ("entry_conditions", "exit_conditions"):
            group = config.get(group_key)
            if group:
                self._validate_formulas_in_group(group, group_key, errors, warnings)

    def _validate_formulas_in_group(
        self, group: dict, path: str, errors: list, warnings: list
    ) -> None:
        for i, item in enumerate(group.get("conditions", [])):
            item_path = f"{path}[{i}]"
            if "logic" in item and "conditions" in item:
                self._validate_formulas_in_group(item, item_path, errors, warnings)
            else:
                for side in ("left", "right"):
                    operand = item.get(side, {})
                    if isinstance(operand, dict) and operand.get("type") == "formula":
                        expr = operand.get("expression", "")
                        parse_errors = self._parser.validate(expr)
                        for err in parse_errors:
                            errors.append({
                                "field": f"{item_path}.{side}.expression",
                                "message": err,
                                "severity": "error",
                            })

    def _validate_symbols(self, config: dict, errors: list, warnings: list) -> None:
        symbols = config.get("symbols")
        if not symbols:
            return

        # Handle list format (frontend sends plain list)
        if isinstance(symbols, list):
            return  # list format is valid, no mode/filter validation needed

        mode = symbols.get("mode")
        if mode not in _VALID_SYMBOL_MODES:
            errors.append({
                "field": "symbols.mode",
                "message": f"Invalid symbol mode. Must be one of: {', '.join(sorted(_VALID_SYMBOL_MODES))}",
                "severity": "error",
            })
            return

        if mode == "watchlist" and not config.get("market"):
            warnings.append({
                "field": "symbols.market",
                "message": "Watchlist mode should specify a market",
                "severity": "warning",
            })

        if mode == "filtered":
            filters = symbols.get("filters")
            if not filters:
                errors.append({
                    "field": "symbols.filters",
                    "message": "Filter criteria required when mode is 'filtered'",
                    "severity": "error",
                })

    def _validate_risk_sanity(self, config: dict, errors: list, warnings: list) -> None:
        stop_loss = config.get("stop_loss")
        if stop_loss and stop_loss.get("type") == "percent":
            val = stop_loss.get("value")
            if val is not None:
                val = float(val)
                if val < 0.1:
                    errors.append({
                        "field": "stop_loss.value",
                        "message": f"Stop loss of {val}% is too small (minimum 0.1%)",
                        "severity": "error",
                    })
                elif val > 50:
                    errors.append({
                        "field": "stop_loss.value",
                        "message": f"Stop loss of {val}% is too large (maximum 50%)",
                        "severity": "error",
                    })
                elif val > 10:
                    warnings.append({
                        "field": "stop_loss.value",
                        "message": f"Stop loss of {val}% is high. Consider reducing.",
                        "severity": "warning",
                    })

        sizing = config.get("position_sizing")
        if sizing:
            if sizing.get("method") == "percent_equity":
                val = sizing.get("value")
                if val is not None:
                    val = float(val)
                    if val > 100:
                        errors.append({
                            "field": "position_sizing.value",
                            "message": "Position size cannot exceed 100% of equity",
                            "severity": "error",
                        })
                    elif val > 25:
                        warnings.append({
                            "field": "position_sizing.value",
                            "message": f"Position size of {val}% is high. Consider reducing.",
                            "severity": "warning",
                        })

            max_pos = sizing.get("max_positions")
            if max_pos is not None and int(max_pos) < 1:
                errors.append({
                    "field": "position_sizing.max_positions",
                    "message": "max_positions must be >= 1",
                    "severity": "error",
                })

    def _validate_conditions(
        self, group: dict, path: str, errors: list, warnings: list
    ) -> None:
        logic = group.get("logic", "and")
        if logic not in ("and", "or"):
            errors.append({
                "field": f"{path}.logic",
                "message": f"Invalid logic: '{logic}'. Must be 'and' or 'or'",
                "severity": "error",
            })

        conditions = group.get("conditions", [])
        for i, item in enumerate(conditions):
            item_path = f"{path}[{i}]"
            if "logic" in item and "conditions" in item:
                self._validate_conditions(item, item_path, errors, warnings)
            else:
                operator = item.get("operator", "")
                if operator not in _VALID_OPERATORS:
                    errors.append({
                        "field": f"{item_path}.operator",
                        "message": f"Invalid operator: '{operator}'",
                        "severity": "error",
                    })

                for side in ("left", "right"):
                    operand = item.get(side, {})
                    if isinstance(operand, dict):
                        op_type = operand.get("type")
                        if op_type and op_type not in _VALID_OPERAND_TYPES:
                            if not (operator in ("between", "outside") and side == "right"):
                                errors.append({
                                    "field": f"{item_path}.{side}.type",
                                    "message": f"Invalid operand type: '{op_type}'",
                                    "severity": "error",
                                })
