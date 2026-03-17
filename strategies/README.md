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

All indicator methods accept a DataFrame (`history`) and extract the source column internally.
You never need to write `history["close"]` — just pass `history`.

**Scalar (latest value):**
- `self.indicators.sma(history, period, source="close")` — Simple Moving Average
- `self.indicators.ema(history, period, source="close")` — Exponential Moving Average
- `self.indicators.rsi(history, period=14, source="close")` — Relative Strength Index (0-100)
- `self.indicators.atr(history, period=14)` — Average True Range
- `self.indicators.bollinger(history, period=20, std_dev=2.0, source="close")` — (upper, middle, lower)
- `self.indicators.macd(history, fast=12, slow=26, signal=9, source="close")` — (macd, signal, histogram)
- `self.indicators.highest(history, period, source="high")` — Highest value over N bars
- `self.indicators.lowest(history, period, source="low")` — Lowest value over N bars

**Series (for crossover detection):**
- `self.indicators.sma_series(history, period, source="close")` — SMA as pd.Series

**Crossover helpers (accept pd.Series or scalar):**
- `self.indicators.crosses_above(series_a, series_b)` — True if A crossed above B
- `self.indicators.crosses_below(series_a, series_b)` — True if A crossed below B

**Example — SMA crossover:**
```python
sma_fast = self.indicators.sma_series(history, 20)
sma_slow = self.indicators.sma_series(history, 50)
if self.indicators.crosses_above(sma_fast, sma_slow):
    # Go long
```

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
