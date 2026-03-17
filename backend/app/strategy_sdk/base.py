"""Strategy base class for the Strategy SDK."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

import pandas as pd

from .signal import StrategySignal
from .indicators import Indicators
from .utils import TimeUtils, PipUtils


class Strategy(ABC):
    """
    Base class for all Python-based trading strategies.

    Subclass this and implement on_bar() to create a strategy.
    Place your file in the strategies/ folder and it will be
    auto-discovered on startup.

    Example:
        class MyStrategy(Strategy):
            name = "My Strategy"
            symbols = ["EUR_USD"]
            timeframe = "1h"
            market = "forex"

            def on_bar(self, symbol, bar, history):
                sma_fast = self.indicators.sma(history, 20)
                sma_slow = self.indicators.sma(history, 50)
                if sma_fast > sma_slow:
                    return [self.signal(symbol, "long", bar["close"],
                                        stop_loss=bar["close"] - 0.005,
                                        take_profit=bar["close"] + 0.0075)]
                return []
    """

    # === Required metadata (subclass MUST set these) ===
    name: str = ""
    description: str = ""
    symbols: list[str] = []
    timeframe: str = "1h"          # "1m", "5m", "15m", "1h", "4h", "1d"
    market: str = "forex"           # "forex", "equity"

    # === Optional configuration ===
    max_positions_per_symbol: int = 1
    max_total_positions: int = 5

    # === Runtime state (set by runner, available to strategy) ===
    positions: dict = {}            # symbol -> list of open positions
    equity: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")

    # === Helpers (set by runner at initialization) ===
    indicators: Indicators = None  # type: ignore[assignment]
    time: TimeUtils = None  # type: ignore[assignment]
    pips: PipUtils = None  # type: ignore[assignment]

    # === Internal state ===
    _state: dict = {}               # Strategy's private state (persists across bars)

    def __init__(self):
        self._state = {}
        self.positions = {}
        self.indicators = Indicators()
        self.time = TimeUtils()
        self.pips = PipUtils()

    # === Lifecycle hooks ===

    def on_start(self):
        """Called once when the strategy starts. Initialize state here."""
        pass

    @abstractmethod
    def on_bar(self, symbol: str, bar: dict, history: pd.DataFrame) -> list[StrategySignal]:
        """
        Called on every new bar for each symbol.

        Args:
            symbol: The instrument (e.g., "EUR_USD")
            bar: Current bar dict with keys: open, high, low, close, volume, timestamp
            history: DataFrame of historical bars (most recent last),
                     including the current bar as the last row.
                     Columns: open, high, low, close, volume, timestamp

        Returns:
            List of StrategySignal objects (empty list = no action)
        """
        raise NotImplementedError

    def on_fill(self, symbol: str, fill: dict):
        """Called when an order is filled. Override to track fills."""
        pass

    def on_stop(self):
        """Called when the strategy is stopped. Cleanup here."""
        pass

    # === Signal builder ===

    def signal(
        self,
        symbol: str,
        direction: str,           # "long" or "short"
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        quantity: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> StrategySignal:
        """Convenience method to create a signal."""
        return StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            direction=direction,
            entry_price=Decimal(str(entry_price)),
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            take_profit=Decimal(str(take_profit)) if take_profit else None,
            quantity=Decimal(str(quantity)) if quantity else None,
            metadata=metadata or {},
        )

    # === State helpers ===

    def get_state(self, key: str, default=None):
        """Get a value from strategy's private state."""
        return self._state.get(key, default)

    def set_state(self, key: str, value):
        """Set a value in strategy's private state."""
        self._state[key] = value

    def has_position(self, symbol: str, direction: Optional[str] = None) -> bool:
        """Check if strategy has an open position for symbol."""
        positions = self.positions.get(symbol, [])
        if direction:
            return any(p.get("side") == direction for p in positions)
        return len(positions) > 0

    def position_count(self) -> int:
        """Total number of open positions across all symbols."""
        return sum(len(v) for v in self.positions.values())

    # === Parameter declaration (for UI display and backtest config) ===

    @classmethod
    def get_parameters(cls) -> dict:
        """
        Return configurable parameters for this strategy.

        Override to declare parameters that can be tuned:

            @classmethod
            def get_parameters(cls):
                return {
                    "risk_reward": {"type": "float", "default": 1.5, "min": 0.5, "max": 5.0, "label": "Risk:Reward Ratio"},
                    "min_range_pips": {"type": "float", "default": 15, "min": 5, "max": 100, "label": "Min Range (pips)"},
                }
        """
        return {}
