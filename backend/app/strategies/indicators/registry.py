"""Indicator registry — stores definitions and metadata for all indicators."""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class IndicatorParam:
    """Definition of a single parameter for an indicator."""

    name: str
    type: str  # "int" | "float" | "select"
    default: Any
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None  # for select type


@dataclass
class IndicatorDefinition:
    """Full definition of a registered indicator."""

    key: str  # e.g., "rsi", "ema", "bbands"
    name: str  # human-readable name
    category: str  # trend | momentum | volatility | volume | trend_strength | price_reference
    params: list[IndicatorParam]
    outputs: list[str]  # e.g., ["number"] or ["upper", "middle", "lower"]
    description: str
    compute_fn: Callable  # reference to the actual computation function


class IndicatorRegistry:
    """Registry of all available indicators."""

    def __init__(self):
        self._indicators: dict[str, IndicatorDefinition] = {}

    def register(self, definition: IndicatorDefinition) -> None:
        """Register an indicator."""
        self._indicators[definition.key] = definition

    def get(self, key: str) -> IndicatorDefinition | None:
        """Get indicator definition by key."""
        return self._indicators.get(key)

    def list_all(self) -> list[IndicatorDefinition]:
        """List all registered indicators."""
        return list(self._indicators.values())

    def list_by_category(self, category: str) -> list[IndicatorDefinition]:
        """List indicators in a category."""
        return [d for d in self._indicators.values() if d.category == category]

    def exists(self, key: str) -> bool:
        """Check if an indicator is registered."""
        return key in self._indicators
