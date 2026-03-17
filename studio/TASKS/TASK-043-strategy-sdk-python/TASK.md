# TASK-043 — Strategy SDK + Python Strategy Runner

## Goal

Build a Strategy base class (SDK) and a runner that loads Python strategy files, executes them against live bar data, and feeds signals into the existing risk → orders → portfolio pipeline. After this task, Python-based strategies can run in paper trading mode alongside the existing condition-based strategies.

## Depends On

TASK-042 (backtest/strategy fixes)

## Architecture

```
strategies/                    ← User's strategy files (git-tracked)
  london_breakout.py
  rsi_mean_reversion.py
  ...

backend/app/
  strategy_sdk/                ← SDK module (new)
    __init__.py
    base.py                    ← Strategy base class
    signal.py                  ← Signal dataclass
    runner.py                  ← Loads + executes Python strategies
    registry.py                ← Discovers + registers strategy files
    indicators.py              ← Helper indicators (wraps existing library)
    utils.py                   ← Time helpers, pip calculations
  
  strategies/                  ← Existing condition engine (unchanged)
    runner.py                  ← Existing condition-based runner (unchanged)
```

The SDK lives in the backend as a proper module. User strategy files live in a top-level `strategies/` folder at the repo root. The runner scans that folder, imports each file, and registers any class that inherits from `Strategy`.

## Scope

**In scope:**
- Strategy base class with lifecycle hooks (on_start, on_bar, on_fill, on_stop)
- Built-in indicator helpers (SMA, EMA, RSI, ATR, MACD, Bollinger, highest, lowest)
- Built-in utility helpers (hour_et, candle_body_pct, pips, pip_value)
- Signal dataclass matching the existing signal pipeline format
- Strategy runner that executes Python strategies on each new bar
- Registry that discovers strategies from the `strategies/` folder
- Integration with existing signal service (signals flow to risk → orders → portfolio)
- API endpoint to list registered Python strategies and their parameters
- API endpoint to start/stop a Python strategy for paper trading
- Startup registration (scan and load strategies on backend boot)

**Out of scope:**
- Backtest integration (TASK-044)
- London Breakout strategy (TASK-045)
- Dashboard UI changes (TASK-046)
- Hot-reload of strategy files (future enhancement)
- Code editor in the UI (not needed — edit files directly)
- Condition-based strategy changes (existing system stays unchanged)

---

## Deliverables

### D1 — Strategy Base Class (`strategy_sdk/base.py`)

```python
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
    positions: dict = {}            # symbol → list of open positions
    equity: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")
    
    # === Helpers (set by runner at initialization) ===
    indicators: Indicators = None
    time: TimeUtils = None
    pips: PipUtils = None
    
    # === Internal state ===
    _state: dict = {}               # Strategy's private state (persists across bars)
    
    def __init__(self):
        self._state = {}
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
```

### D2 — Signal Dataclass (`strategy_sdk/signal.py`)

```python
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from datetime import datetime


@dataclass
class StrategySignal:
    """
    Signal generated by a Python strategy.
    
    This is converted to the platform's internal signal format
    by the runner before passing to the risk engine.
    """
    strategy_name: str
    symbol: str
    direction: str                          # "long" or "short"
    entry_price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    quantity: Optional[Decimal] = None      # None = use default sizing
    metadata: dict = field(default_factory=dict)
    timestamp: Optional[datetime] = None    # Set by runner if not provided
    
    # Quality/scoring (optional)
    score: Optional[float] = None           # 0-100
    confidence: Optional[float] = None      # 0.0-1.0
```

### D3 — Indicator Helpers (`strategy_sdk/indicators.py`)

Wraps the existing indicator library functions for convenient access:

```python
import pandas as pd
import numpy as np
from decimal import Decimal


class Indicators:
    """
    Indicator calculation helpers.
    
    All methods accept a pandas DataFrame (history) and return
    the most recent value (or a Series if requested).
    """
    
    def sma(self, history: pd.DataFrame, period: int, source: str = "close") -> float:
        """Simple Moving Average. Returns most recent value."""
        if len(history) < period:
            return float("nan")
        return float(history[source].tail(period).mean())
    
    def sma_series(self, history: pd.DataFrame, period: int, source: str = "close") -> pd.Series:
        """Simple Moving Average as a full series."""
        return history[source].rolling(window=period).mean()
    
    def ema(self, history: pd.DataFrame, period: int, source: str = "close") -> float:
        """Exponential Moving Average. Returns most recent value."""
        if len(history) < period:
            return float("nan")
        return float(history[source].ewm(span=period, adjust=False).mean().iloc[-1])
    
    def rsi(self, history: pd.DataFrame, period: int = 14, source: str = "close") -> float:
        """Relative Strength Index. Returns most recent value (0-100)."""
        if len(history) < period + 1:
            return float("nan")
        delta = history[source].diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def atr(self, history: pd.DataFrame, period: int = 14) -> float:
        """Average True Range. Returns most recent value."""
        if len(history) < period + 1:
            return float("nan")
        high = history["high"]
        low = history["low"]
        close = history["close"].shift(1)
        tr = pd.concat([
            high - low,
            (high - close).abs(),
            (low - close).abs()
        ], axis=1).max(axis=1)
        return float(tr.rolling(window=period).mean().iloc[-1])
    
    def bollinger(self, history: pd.DataFrame, period: int = 20, std_dev: float = 2.0, source: str = "close") -> tuple:
        """Bollinger Bands. Returns (upper, middle, lower)."""
        sma = history[source].rolling(window=period).mean()
        std = history[source].rolling(window=period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        return (float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1]))
    
    def macd(self, history: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, source: str = "close") -> tuple:
        """MACD. Returns (macd_line, signal_line, histogram)."""
        fast_ema = history[source].ewm(span=fast, adjust=False).mean()
        slow_ema = history[source].ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return (float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1]))
    
    def highest(self, history: pd.DataFrame, period: int, source: str = "high") -> float:
        """Highest value over last N bars."""
        return float(history[source].tail(period).max())
    
    def lowest(self, history: pd.DataFrame, period: int, source: str = "low") -> float:
        """Lowest value over last N bars."""
        return float(history[source].tail(period).min())
    
    def crosses_above(self, series_a: pd.Series, series_b) -> bool:
        """Check if series_a just crossed above series_b (or a value)."""
        if len(series_a) < 2:
            return False
        if isinstance(series_b, (int, float)):
            return series_a.iloc[-2] <= series_b and series_a.iloc[-1] > series_b
        return series_a.iloc[-2] <= series_b.iloc[-2] and series_a.iloc[-1] > series_b.iloc[-1]
    
    def crosses_below(self, series_a: pd.Series, series_b) -> bool:
        """Check if series_a just crossed below series_b (or a value)."""
        if len(series_a) < 2:
            return False
        if isinstance(series_b, (int, float)):
            return series_a.iloc[-2] >= series_b and series_a.iloc[-1] < series_b
        return series_a.iloc[-2] >= series_b.iloc[-2] and series_a.iloc[-1] < series_b.iloc[-1]
```

### D4 — Utility Helpers (`strategy_sdk/utils.py`)

```python
from datetime import datetime, timezone
import pytz


ET = pytz.timezone("US/Eastern")
UTC = pytz.UTC


class TimeUtils:
    """Time-related helpers for strategies."""
    
    def hour_et(self, bar: dict) -> int:
        """Get the hour (0-23) in US/Eastern time for a bar."""
        ts = bar.get("timestamp")
        if ts is None:
            return -1
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.astimezone(ET).hour
    
    def minute_et(self, bar: dict) -> int:
        """Get the minute (0-59) in US/Eastern time for a bar."""
        ts = bar.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.astimezone(ET).minute
    
    def date_et(self, bar: dict):
        """Get the date in US/Eastern time for a bar."""
        ts = bar.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.astimezone(ET).date()
    
    def weekday(self, bar: dict) -> int:
        """Get weekday (0=Monday, 6=Sunday) in ET."""
        return self.date_et(bar).weekday()
    
    def is_between_hours(self, bar: dict, start_hour: int, end_hour: int) -> bool:
        """Check if bar falls within a time window (ET hours)."""
        hour = self.hour_et(bar)
        return start_hour <= hour < end_hour


class PipUtils:
    """Pip calculation helpers for forex."""
    
    JPY_PAIRS = {"USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "CAD_JPY", "CHF_JPY"}
    
    def pip_value(self, symbol: str) -> float:
        """Get the pip value for a symbol (0.0001 for most, 0.01 for JPY)."""
        if symbol in self.JPY_PAIRS or symbol.endswith("_JPY"):
            return 0.01
        return 0.0001
    
    def to_pips(self, price_diff: float, symbol: str) -> float:
        """Convert a price difference to pips."""
        return abs(price_diff) / self.pip_value(symbol)
    
    def from_pips(self, pip_count: float, symbol: str) -> float:
        """Convert pips to a price difference."""
        return pip_count * self.pip_value(symbol)
    
    def candle_body_pct(self, bar: dict) -> float:
        """Calculate candle body as percentage of total range."""
        high = bar["high"]
        low = bar["low"]
        if high == low:
            return 0.0
        body = abs(bar["close"] - bar["open"])
        return body / (high - low)
    
    def candle_direction(self, bar: dict) -> str:
        """Return 'bullish', 'bearish', or 'neutral'."""
        if bar["close"] > bar["open"]:
            return "bullish"
        elif bar["close"] < bar["open"]:
            return "bearish"
        return "neutral"
```

### D5 — Strategy Registry (`strategy_sdk/registry.py`)

```python
import importlib
import importlib.util
import os
import logging
from pathlib import Path
from typing import Dict, Type

from .base import Strategy

logger = logging.getLogger(__name__)

# Global registry
_strategies: Dict[str, Type[Strategy]] = {}
_instances: Dict[str, Strategy] = {}


def discover_strategies(strategies_dir: str = None) -> Dict[str, Type[Strategy]]:
    """
    Scan the strategies/ directory and register all Strategy subclasses.
    
    Args:
        strategies_dir: Path to strategies folder. 
                       Defaults to {repo_root}/strategies/
    
    Returns:
        Dict mapping strategy name → strategy class
    """
    if strategies_dir is None:
        # Default: repo_root/strategies/
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        strategies_dir = repo_root / "strategies"
    else:
        strategies_dir = Path(strategies_dir)
    
    if not strategies_dir.exists():
        logger.warning(f"Strategies directory not found: {strategies_dir}")
        strategies_dir.mkdir(parents=True, exist_ok=True)
        return {}
    
    discovered = {}
    
    for py_file in sorted(strategies_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        
        try:
            # Import the module
            module_name = f"strategies.{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Strategy subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) 
                    and issubclass(attr, Strategy) 
                    and attr is not Strategy
                    and attr.name):  # Must have a name set
                    
                    discovered[attr.name] = attr
                    logger.info(f"Discovered strategy: {attr.name} ({py_file.name})")
        
        except Exception as e:
            logger.error(f"Failed to load strategy from {py_file.name}: {e}")
    
    _strategies.update(discovered)
    return discovered


def get_strategy_class(name: str) -> Type[Strategy] | None:
    """Get a registered strategy class by name."""
    return _strategies.get(name)


def get_strategy_instance(name: str) -> Strategy | None:
    """Get or create a strategy instance by name."""
    if name not in _instances:
        cls = _strategies.get(name)
        if cls is None:
            return None
        _instances[name] = cls()
    return _instances[name]


def list_strategies() -> list[dict]:
    """List all registered strategies with metadata."""
    result = []
    for name, cls in _strategies.items():
        result.append({
            "name": cls.name,
            "description": cls.description,
            "symbols": cls.symbols,
            "timeframe": cls.timeframe,
            "market": cls.market,
            "parameters": cls.get_parameters(),
            "type": "python",
        })
    return result


def reset():
    """Clear all registrations (for testing)."""
    _strategies.clear()
    _instances.clear()
```

### D6 — Strategy Runner (`strategy_sdk/runner.py`)

The runner executes Python strategies against live bar data and feeds signals into the existing pipeline:

```python
import asyncio
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from .base import Strategy
from .signal import StrategySignal
from .registry import get_strategy_instance, list_strategies

logger = logging.getLogger(__name__)


class PythonStrategyRunner:
    """
    Runs Python-based strategies against live bar data.
    
    Integrates with the existing signal pipeline:
    Python Strategy → StrategySignal → signal_service.create() → risk → orders
    """
    
    def __init__(self):
        self._running_strategies: dict[str, bool] = {}  # name → running
        self._tasks: dict[str, asyncio.Task] = {}
    
    async def start_strategy(self, name: str, db_session_factory):
        """Start a Python strategy for live paper trading."""
        instance = get_strategy_instance(name)
        if instance is None:
            raise ValueError(f"Strategy not found: {name}")
        
        if self._running_strategies.get(name):
            logger.warning(f"Strategy {name} is already running")
            return
        
        self._running_strategies[name] = True
        instance.on_start()
        
        logger.info(f"Started Python strategy: {name}")
        
        # The actual bar-by-bar execution is driven by the market data
        # stream. When a new bar arrives for a symbol this strategy
        # watches, the on_new_bar() method is called.
    
    async def stop_strategy(self, name: str):
        """Stop a running Python strategy."""
        instance = get_strategy_instance(name)
        if instance:
            instance.on_stop()
        self._running_strategies[name] = False
        logger.info(f"Stopped Python strategy: {name}")
    
    async def on_new_bar(self, symbol: str, bar: dict, history_df: pd.DataFrame):
        """
        Called by the market data stream when a new bar is available.
        
        Iterates through all running Python strategies that watch this symbol
        and calls their on_bar() method.
        """
        for name, running in self._running_strategies.items():
            if not running:
                continue
            
            instance = get_strategy_instance(name)
            if instance is None or symbol not in instance.symbols:
                continue
            
            # Check timeframe match
            # (The bar's timeframe should match the strategy's timeframe)
            
            try:
                # Update runtime state
                instance.positions = await self._get_positions(instance, symbol)
                instance.equity = await self._get_equity()
                instance.cash = await self._get_cash()
                
                # Execute strategy
                signals = instance.on_bar(symbol, bar, history_df)
                
                if not signals:
                    continue
                
                # Process each signal through the existing pipeline
                for signal in signals:
                    await self._process_signal(signal, instance)
                    
            except Exception as e:
                logger.error(f"Strategy {name} error on {symbol}: {e}", exc_info=True)
    
    async def _process_signal(self, signal: StrategySignal, strategy: Strategy):
        """
        Convert a StrategySignal to the platform's internal format
        and submit it to the signal service.
        """
        from app.signals.service import create_signal
        
        # Build the internal signal dict matching what the condition
        # engine produces — same format that flows to risk → orders
        internal_signal = {
            "strategy_name": signal.strategy_name,
            "strategy_type": "python",
            "symbol": signal.symbol,
            "side": signal.direction,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "quantity": signal.quantity,
            "score": signal.score,
            "confidence": signal.confidence,
            "metadata": signal.metadata,
            "timestamp": signal.timestamp or datetime.utcnow(),
        }
        
        try:
            await create_signal(internal_signal)
            logger.info(f"Signal submitted: {signal.direction} {signal.symbol} "
                       f"@ {signal.entry_price} (from {signal.strategy_name})")
        except Exception as e:
            logger.error(f"Failed to submit signal from {signal.strategy_name}: {e}")
    
    async def _get_positions(self, strategy: Strategy, symbol: str) -> dict:
        """Get current positions for the strategy's symbols."""
        # Import here to avoid circular imports
        from app.portfolio.service import get_open_positions
        positions = {}
        for sym in strategy.symbols:
            pos = await get_open_positions(sym)
            if pos:
                positions[sym] = pos
        return positions
    
    async def _get_equity(self) -> float:
        """Get current account equity."""
        from app.portfolio.service import get_portfolio_summary
        summary = await get_portfolio_summary()
        return summary.get("equity", 0)
    
    async def _get_cash(self) -> float:
        """Get current available cash."""
        from app.portfolio.service import get_portfolio_summary
        summary = await get_portfolio_summary()
        return summary.get("cash", 0)
    
    def get_status(self) -> list[dict]:
        """Get status of all Python strategies."""
        result = []
        for name, running in self._running_strategies.items():
            instance = get_strategy_instance(name)
            result.append({
                "name": name,
                "running": running,
                "symbols": instance.symbols if instance else [],
                "timeframe": instance.timeframe if instance else "",
                "positions": instance.position_count() if instance else 0,
            })
        return result


# Singleton
_runner: Optional[PythonStrategyRunner] = None

def get_python_runner() -> PythonStrategyRunner:
    global _runner
    if _runner is None:
        _runner = PythonStrategyRunner()
    return _runner
```

### D7 — API Endpoints (`strategy_sdk/router.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user

from .registry import list_strategies, get_strategy_class
from .runner import get_python_runner

router = APIRouter(prefix="/api/v1/python-strategies", tags=["python-strategies"])


@router.get("")
async def list_python_strategies(user=Depends(get_current_user)):
    """List all discovered Python strategies."""
    return {"data": list_strategies()}


@router.get("/{name}")
async def get_python_strategy(name: str, user=Depends(get_current_user)):
    """Get details for a specific Python strategy."""
    cls = get_strategy_class(name)
    if not cls:
        raise HTTPException(404, f"Strategy '{name}' not found")
    return {"data": {
        "name": cls.name,
        "description": cls.description,
        "symbols": cls.symbols,
        "timeframe": cls.timeframe,
        "market": cls.market,
        "parameters": cls.get_parameters(),
        "type": "python",
    }}


@router.post("/{name}/start")
async def start_strategy(name: str, user=Depends(get_current_user)):
    """Start a Python strategy for paper trading."""
    cls = get_strategy_class(name)
    if not cls:
        raise HTTPException(404, f"Strategy '{name}' not found")
    
    runner = get_python_runner()
    await runner.start_strategy(name, None)  # TODO: pass session factory
    return {"data": {"name": name, "status": "running"}}


@router.post("/{name}/stop")
async def stop_strategy(name: str, user=Depends(get_current_user)):
    """Stop a running Python strategy."""
    runner = get_python_runner()
    await runner.stop_strategy(name)
    return {"data": {"name": name, "status": "stopped"}}


@router.get("/status/all")
async def get_runner_status(user=Depends(get_current_user)):
    """Get status of all Python strategies."""
    runner = get_python_runner()
    return {"data": runner.get_status()}
```

### D8 — Startup Integration

In `backend/app/main.py`, add strategy discovery on startup:

```python
# In the lifespan function, after other modules start:
from app.strategy_sdk.registry import discover_strategies

logger.info("Discovering Python strategies...")
strategies = discover_strategies()
logger.info(f"Found {len(strategies)} Python strategies")
```

Register the router:
```python
from app.strategy_sdk.router import router as python_strategy_router
app.include_router(python_strategy_router)
```

### D9 — Example Strategy

Create `strategies/example_sma_cross.py` as a working example:

```python
"""
Example: SMA Crossover Strategy
================================
Simple moving average crossover on forex pairs.
This is an example showing how to write a Python strategy.
"""
from app.strategy_sdk.base import Strategy


class SMACrossover(Strategy):
    name = "SMA Crossover Example"
    description = "Enters on SMA(20) crossing above/below SMA(50)"
    symbols = ["EUR_USD"]
    timeframe = "1h"
    market = "forex"
    
    # Configurable parameters
    fast_period = 20
    slow_period = 50
    
    @classmethod
    def get_parameters(cls):
        return {
            "fast_period": {"type": "int", "default": 20, "min": 5, "max": 100, "label": "Fast SMA Period"},
            "slow_period": {"type": "int", "default": 50, "min": 10, "max": 500, "label": "Slow SMA Period"},
        }
    
    def on_start(self):
        self.set_state("last_signal", None)
    
    def on_bar(self, symbol, bar, history):
        if len(history) < self.slow_period + 1:
            return []
        
        sma_fast = self.indicators.sma_series(history, self.fast_period)
        sma_slow = self.indicators.sma_series(history, self.slow_period)
        
        signals = []
        
        # Long signal: fast crosses above slow
        if self.indicators.crosses_above(sma_fast, sma_slow):
            if not self.has_position(symbol, "long"):
                # Close any short position first
                # (handled by signal_exit logic in the pipeline)
                entry = bar["close"]
                sl = entry - self.pips.from_pips(50, symbol)
                tp = entry + self.pips.from_pips(75, symbol)
                signals.append(self.signal(symbol, "long", entry, 
                                          stop_loss=sl, take_profit=tp))
                self.set_state("last_signal", "long")
        
        # Short signal: fast crosses below slow
        elif self.indicators.crosses_below(sma_fast, sma_slow):
            if not self.has_position(symbol, "short"):
                entry = bar["close"]
                sl = entry + self.pips.from_pips(50, symbol)
                tp = entry - self.pips.from_pips(75, symbol)
                signals.append(self.signal(symbol, "short", entry,
                                          stop_loss=sl, take_profit=tp))
                self.set_state("last_signal", "short")
        
        return signals
```

### D10 — Strategies Directory

Create `strategies/__init__.py` (empty) and `strategies/README.md`:

```markdown
# Ratatoskr Python Strategies

Place your strategy files here. Any Python file with a class that
inherits from `Strategy` will be auto-discovered on startup.

## Quick Start

```python
from app.strategy_sdk.base import Strategy

class MyStrategy(Strategy):
    name = "My Strategy"
    symbols = ["EUR_USD"]
    timeframe = "1h"
    market = "forex"
    
    def on_bar(self, symbol, bar, history):
        # Your logic here
        return []  # Return list of signals
```

## Available Helpers

### Indicators
- `self.indicators.sma(history, period)` — Simple Moving Average
- `self.indicators.ema(history, period)` — Exponential Moving Average
- `self.indicators.rsi(history, period)` — Relative Strength Index
- `self.indicators.atr(history, period)` — Average True Range
- `self.indicators.bollinger(history, period, std_dev)` — Bollinger Bands
- `self.indicators.macd(history, fast, slow, signal)` — MACD
- `self.indicators.highest(history, period)` — Highest High
- `self.indicators.lowest(history, period)` — Lowest Low
- `self.indicators.crosses_above(series_a, series_b)` — Crossover detection
- `self.indicators.crosses_below(series_a, series_b)` — Crossunder detection

### Time
- `self.time.hour_et(bar)` — Hour in US/Eastern (0-23)
- `self.time.is_between_hours(bar, start, end)` — Time window check
- `self.time.date_et(bar)` — Date in US/Eastern
- `self.time.weekday(bar)` — Day of week (0=Mon)

### Pips
- `self.pips.to_pips(price_diff, symbol)` — Convert price to pips
- `self.pips.from_pips(count, symbol)` — Convert pips to price
- `self.pips.candle_body_pct(bar)` — Candle body percentage
- `self.pips.candle_direction(bar)` — "bullish"/"bearish"/"neutral"

### State
- `self.set_state(key, value)` — Store strategy state
- `self.get_state(key, default)` — Retrieve state
- `self.has_position(symbol, direction)` — Check open positions
- `self.position_count()` — Total open positions
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `Strategy` base class exists with on_bar(), on_start(), on_stop(), on_fill() lifecycle hooks |
| AC2 | `StrategySignal` dataclass has all fields needed by the signal pipeline |
| AC3 | `Indicators` class provides SMA, EMA, RSI, ATR, Bollinger, MACD, highest, lowest, crosses_above/below |
| AC4 | `TimeUtils` provides hour_et, is_between_hours, date_et, weekday |
| AC5 | `PipUtils` provides to_pips, from_pips, pip_value (with JPY handling), candle_body_pct |
| AC6 | Registry discovers Python strategy files from `strategies/` folder on startup |
| AC7 | Strategy classes with `name` set are auto-registered; files without valid strategies are skipped with warning |
| AC8 | `GET /api/v1/python-strategies` returns list of discovered strategies with metadata |
| AC9 | `POST /api/v1/python-strategies/{name}/start` starts a strategy (sets running flag) |
| AC10 | `POST /api/v1/python-strategies/{name}/stop` stops a strategy |
| AC11 | Runner's `on_new_bar()` calls `strategy.on_bar()` for matching symbol/timeframe |
| AC12 | Signals from Python strategies are submitted to the existing signal service |
| AC13 | Example SMA Crossover strategy exists in `strategies/` and is discoverable |
| AC14 | `strategies/README.md` documents the SDK with all available helpers |
| AC15 | Backend startup log shows "Found N Python strategies" |
| AC16 | Existing condition-based strategies are NOT affected (no changes to strategies/ module) |
| AC17 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/strategy_sdk/__init__.py` | Module init |
| `backend/app/strategy_sdk/base.py` | Strategy base class |
| `backend/app/strategy_sdk/signal.py` | StrategySignal dataclass |
| `backend/app/strategy_sdk/indicators.py` | Indicator helper methods |
| `backend/app/strategy_sdk/utils.py` | Time and pip utilities |
| `backend/app/strategy_sdk/registry.py` | Strategy discovery and registration |
| `backend/app/strategy_sdk/runner.py` | Python strategy executor |
| `backend/app/strategy_sdk/router.py` | API endpoints |
| `strategies/__init__.py` | Empty init |
| `strategies/README.md` | SDK documentation |
| `strategies/example_sma_cross.py` | Working example strategy |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/main.py` | Add strategy discovery on startup + register router |

## Files NOT to Touch

- `backend/app/strategies/` (existing condition engine — unchanged)
- Frontend code (TASK-046)
- Test files
- Studio files

---

## Builder Notes

- **The `strategies/` folder is at the repo root** (same level as `backend/`, `frontend/`). NOT inside `backend/app/`. Strategy files import from `app.strategy_sdk.base` using the full module path.
- **The runner's `on_new_bar()` is called by the market data stream.** The integration point is wherever the existing market data WebSocket manager pushes new bars. The builder needs to find that hookup point and add a call to `get_python_runner().on_new_bar()`. This might be in `backend/app/market_data/streams/manager.py` or similar.
- **The signal pipeline integration** depends on how `signal_service.create_signal()` works. The builder should inspect the existing condition runner's signal submission path and replicate it. The internal signal dict format should match what the condition engine produces.
- **Don't add pandas as a new dependency** — check if it's already in the project. If not, add it to pyproject.toml. The indicators module needs pandas for series operations.
- **The `_process_signal` method is the key integration point.** It converts a StrategySignal to whatever format the signal service expects. The builder should look at how the existing condition runner creates signals and match that format exactly.
- **Strategy state (`_state`) is in-memory only.** It persists across bars during a session but resets on restart. This is fine for V1.

## References

- strategies/london_breakout.py (uploaded by user) — reference implementation for session-based strategy
- backend/app/strategies/runner.py — existing condition runner (for signal submission format)
- backend/app/signals/service.py — signal creation (integration target)
- backend/app/market_data/streams/ — bar stream (hookup point for on_new_bar)
