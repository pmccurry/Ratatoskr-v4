"""Condition engine — evaluates condition groups against bar data."""

import logging
from decimal import Decimal
from typing import Any

from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators.registry import IndicatorRegistry

logger = logging.getLogger(__name__)


class ConditionEngine:
    """Evaluates condition groups against bar data.

    Usage:
        engine = ConditionEngine(registry, formula_parser)
        result = engine.evaluate(condition_group, bars)
    """

    def __init__(self, registry: IndicatorRegistry, formula_parser: FormulaParser):
        self._registry = registry
        self._parser = formula_parser
        self._cache: dict[str, Any] = {}

    def evaluate(self, condition_group: dict, bars: list) -> bool:
        """Evaluate a condition group against bar data.

        Clears the computation cache per evaluation cycle.
        """
        self._cache.clear()
        try:
            return self._evaluate_group(condition_group, bars)
        except Exception as e:
            logger.error("Condition evaluation error: %s", e)
            return False

    def _evaluate_group(self, group: dict, bars: list) -> bool:
        """Evaluate a condition group with AND/OR logic.

        Items in conditions list can be:
        - A condition dict (has "left", "operator", "right")
        - A nested group dict (has "logic", "conditions")
        """
        logic = group.get("logic", "and")
        conditions = group.get("conditions", [])

        if not conditions:
            return True

        results = []
        for item in conditions:
            if "logic" in item and "conditions" in item:
                results.append(self._evaluate_group(item, bars))
            else:
                results.append(self._evaluate_condition(item, bars))

        if logic == "and":
            return all(results)
        if logic == "or":
            return any(results)
        return False

    def _evaluate_condition(self, condition: dict, bars: list) -> bool:
        """Evaluate a single condition."""
        try:
            operator = condition.get("operator", "")
            left_def = condition.get("left", {})
            right_def = condition.get("right", {})

            # Crossover operators need series (current + previous)
            if operator in ("crosses_above", "crosses_below"):
                left_current, left_prev = self._resolve_series(left_def, bars)
                right_current, right_prev = self._resolve_series(right_def, bars)
                return self._apply_operator(
                    operator,
                    (left_current, left_prev),
                    (right_current, right_prev),
                )

            # Range operators
            if operator in ("between", "outside"):
                left_val = self._resolve_operand(left_def, bars)
                return self._apply_operator(operator, left_val, right_def)

            # Standard comparison
            left_val = self._resolve_operand(left_def, bars)
            right_val = self._resolve_operand(right_def, bars)
            return self._apply_operator(operator, left_val, right_val)
        except Exception as e:
            logger.debug("Condition evaluation failed: %s", e)
            return False

    def _resolve_operand(self, operand: dict, bars: list) -> Decimal | None:
        """Resolve an operand to a numeric value."""
        op_type = operand.get("type", "")

        if op_type == "value":
            val = operand.get("value")
            if val is None:
                return None
            return Decimal(str(val))

        if op_type == "indicator":
            return self._compute_indicator(
                operand.get("indicator", ""),
                operand.get("params") or {},
                operand.get("output"),
                bars,
            )

        if op_type == "formula":
            expr = operand.get("expression", "")
            return self._parser.evaluate(expr, bars)

        return None

    def _resolve_series(
        self, operand: dict, bars: list
    ) -> tuple[Decimal | None, Decimal | None]:
        """Resolve an operand to (current_value, previous_value) for crossover."""
        if len(bars) < 2:
            return (None, None)

        current = self._resolve_operand(operand, bars)

        # Compute on bars[:-1] for previous value
        # Temporarily clear cache entries that depend on bar length
        saved_cache = dict(self._cache)
        self._cache.clear()
        previous = self._resolve_operand(operand, bars[:-1])
        self._cache = saved_cache

        return (current, previous)

    def _compute_indicator(
        self,
        key: str,
        params: dict,
        output: str | None,
        bars: list,
    ) -> Decimal | None:
        """Compute an indicator with caching."""
        cache_key = f"{key}:{sorted(params.items())}:{output}:{len(bars)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        defn = self._registry.get(key)
        if defn is None:
            return None

        # Build kwargs from params, using defaults for missing
        kwargs = {}
        for pdef in defn.params:
            val = params.get(pdef.name, pdef.default)
            if pdef.type == "int":
                kwargs[pdef.name] = int(val)
            elif pdef.type == "float":
                kwargs[pdef.name] = float(val)
            else:
                kwargs[pdef.name] = val

        result = defn.compute_fn(bars, **kwargs)

        # Extract named output from multi-output indicators
        if isinstance(result, dict):
            if output and output in result:
                result = result[output]
            elif defn.outputs and defn.outputs[0] != "number":
                result = result.get(defn.outputs[0])
            else:
                result = next(iter(result.values()), None)

        self._cache[cache_key] = result
        return result

    def _apply_operator(self, operator: str, left: Any, right: Any) -> bool:
        """Apply a comparison operator. Returns False if data is None."""
        # Crossover operators
        if operator == "crosses_above":
            if not isinstance(left, tuple) or not isinstance(right, tuple):
                return False
            curr_l, prev_l = left
            curr_r, prev_r = right
            if None in (curr_l, prev_l, curr_r, prev_r):
                return False
            return prev_l <= prev_r and curr_l > curr_r

        if operator == "crosses_below":
            if not isinstance(left, tuple) or not isinstance(right, tuple):
                return False
            curr_l, prev_l = left
            curr_r, prev_r = right
            if None in (curr_l, prev_l, curr_r, prev_r):
                return False
            return prev_l >= prev_r and curr_l < curr_r

        # Range operators
        if operator == "between":
            if left is None or not isinstance(right, dict):
                return False
            r_min = right.get("min")
            r_max = right.get("max")
            if r_min is None or r_max is None:
                return False
            r_min = Decimal(str(r_min))
            r_max = Decimal(str(r_max))
            return r_min <= left <= r_max

        if operator == "outside":
            if left is None or not isinstance(right, dict):
                return False
            r_min = right.get("min")
            r_max = right.get("max")
            if r_min is None or r_max is None:
                return False
            r_min = Decimal(str(r_min))
            r_max = Decimal(str(r_max))
            return left < r_min or left > r_max

        # Standard comparison
        if left is None or right is None:
            return False

        if operator == "greater_than":
            return left > right
        if operator == "less_than":
            return left < right
        if operator == "greater_than_or_equal":
            return left >= right
        if operator == "less_than_or_equal":
            return left <= right
        if operator == "equal":
            return left == right

        return False
