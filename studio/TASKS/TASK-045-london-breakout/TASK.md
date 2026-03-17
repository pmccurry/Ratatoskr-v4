# TASK-045 — London/NY Breakout Strategy

## Goal

Port the London Breakout strategy to the new Strategy SDK and backtest it against EUR_USD historical data. This is the first real strategy using the Python SDK and validates the entire pipeline: strategy → signals → backtest → results.

## Depends On

TASK-044 (Python backtest integration)

## Reference

The original strategy file was uploaded by the user (`london_breakout.py`). Key logic:

```
RANGE PHASE (3:00-4:00 AM ET):
  → Record high/low of all bars in this window
  → Filter: range must be 15-50 pips

ENTRY PHASE (8:00 AM - 12:00 PM ET, London/NY overlap):
  → LONG: close > range_high + 2 pip buffer
  → SHORT: close < range_low - 2 pip buffer
  → CONFIRM: candle body ≥ 60% of total range (momentum)
  → CONFIRM: candle direction matches breakout direction

EXIT:
  → Stop loss: opposite side of range + 3 pip buffer
  → Take profit: risk × risk_reward ratio (default 1.5)
  → One trade per day max

SCORING (quality filter):
  → Range 20-40 pips ideal: 25%
  → Strong momentum (70%+ body): 30%
  → Clean break (within 5 pips): 15%
  → Optimal time (8-10 AM): 15%
  → Volume increase: 15%
```

## Scope

**In scope:**
- `strategies/london_breakout.py` — Full strategy implementation using Strategy SDK
- Session range detection (configurable hours)
- Breakout detection with momentum confirmation
- Dynamic SL/TP from range bounds
- One-trade-per-day limit
- Quality scoring system
- Configurable parameters exposed via `get_parameters()`
- Backtest verification against EUR_USD 1h data

**Out of scope:**
- Frontend UI for this strategy (TASK-046)
- Live paper trading hookup
- Multi-timeframe analysis
- Correlation filters

---

## Implementation

### `strategies/london_breakout.py`

```python
"""
London/NY Breakout Strategy
============================
Detects London session range and enters on NY overlap breakout.

Range:  First hour of London session (configurable, default 3-4 AM ET)
Entry:  Breakout during London/NY overlap (8 AM - 12 PM ET)
Confirm: Strong momentum candle (60%+ body)
Stop:   Opposite side of range + buffer
Target: Risk × reward ratio (default 1.5:1)

One trade per day maximum.
"""
from app.strategy_sdk.base import Strategy


class LondonBreakout(Strategy):
    name = "London/NY Breakout"
    description = "Enters on price breaking out of the London session range during NY overlap"
    symbols = ["EUR_USD"]
    timeframe = "5m"
    market = "forex"
    
    # === Range Detection ===
    range_start_hour = 3        # 3 AM ET — start of London range window
    range_end_hour = 4          # 4 AM ET — end of range window
    min_range_pips = 15.0       # Minimum range size (filter noise)
    max_range_pips = 50.0       # Maximum range size (filter volatility events)
    
    # === Entry Window ===
    entry_start_hour = 8        # 8 AM ET — NY overlap begins
    entry_end_hour = 12         # 12 PM ET — entry window closes
    
    # === Breakout Confirmation ===
    breakout_buffer_pips = 2.0  # Price must exceed range by this much
    min_body_pct = 0.6          # Candle body must be 60%+ of range (momentum)
    
    # === Risk Management ===
    risk_reward = 1.5           # Take profit = risk × this ratio
    stop_buffer_pips = 3.0      # Stop placed beyond range + this buffer
    
    # === Trade Management ===
    max_trades_per_day = 1      # Only one trade per day
    
    @classmethod
    def get_parameters(cls):
        return {
            "range_start_hour": {"type": "int", "default": 3, "min": 0, "max": 12, "label": "Range Start (hour ET)"},
            "range_end_hour": {"type": "int", "default": 4, "min": 1, "max": 12, "label": "Range End (hour ET)"},
            "min_range_pips": {"type": "float", "default": 15.0, "min": 5.0, "max": 100.0, "label": "Min Range (pips)"},
            "max_range_pips": {"type": "float", "default": 50.0, "min": 10.0, "max": 200.0, "label": "Max Range (pips)"},
            "entry_start_hour": {"type": "int", "default": 8, "min": 4, "max": 16, "label": "Entry Start (hour ET)"},
            "entry_end_hour": {"type": "int", "default": 12, "min": 8, "max": 20, "label": "Entry End (hour ET)"},
            "breakout_buffer_pips": {"type": "float", "default": 2.0, "min": 0.0, "max": 10.0, "label": "Breakout Buffer (pips)"},
            "min_body_pct": {"type": "float", "default": 0.6, "min": 0.3, "max": 0.95, "label": "Min Body % (momentum)"},
            "risk_reward": {"type": "float", "default": 1.5, "min": 0.5, "max": 5.0, "label": "Risk:Reward Ratio"},
            "stop_buffer_pips": {"type": "float", "default": 3.0, "min": 0.0, "max": 20.0, "label": "Stop Buffer (pips)"},
            "max_trades_per_day": {"type": "int", "default": 1, "min": 1, "max": 5, "label": "Max Trades Per Day"},
        }
    
    def on_start(self):
        """Initialize daily state tracking."""
        self.set_state("current_date", None)
        self.set_state("range_high", None)
        self.set_state("range_low", None)
        self.set_state("range_bars", [])
        self.set_state("trades_today", 0)
        self.set_state("range_valid", False)
    
    def on_bar(self, symbol, bar, history):
        """
        Main strategy logic — called on every bar.
        
        Flow:
        1. Check if new day → reset state
        2. During range window → accumulate high/low
        3. After range window → validate range
        4. During entry window → check for breakout
        """
        bar_date = self.time.date_et(bar)
        hour = self.time.hour_et(bar)
        
        # === New day reset ===
        if bar_date != self.get_state("current_date"):
            self.set_state("current_date", bar_date)
            self.set_state("range_high", None)
            self.set_state("range_low", None)
            self.set_state("range_bars", [])
            self.set_state("trades_today", 0)
            self.set_state("range_valid", False)
        
        # === Range accumulation phase ===
        if self.range_start_hour <= hour < self.range_end_hour:
            self._accumulate_range(bar)
            return []
        
        # === Validate range (once, after range window closes) ===
        if hour >= self.range_end_hour and not self.get_state("range_valid"):
            self._validate_range(symbol)
            # Even if invalid, mark as checked so we don't re-check
            if self.get_state("range_high") is None:
                return []
        
        # === Entry window ===
        if not self.time.is_between_hours(bar, self.entry_start_hour, self.entry_end_hour):
            return []
        
        # === Guards ===
        if not self.get_state("range_valid"):
            return []
        if self.get_state("trades_today") >= self.max_trades_per_day:
            return []
        if self.has_position(symbol):
            return []
        
        # === Check for breakout ===
        return self._check_breakout(symbol, bar)
    
    def _accumulate_range(self, bar):
        """Record high/low during range window."""
        range_high = self.get_state("range_high")
        range_low = self.get_state("range_low")
        
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])
        
        if range_high is None or bar_high > range_high:
            self.set_state("range_high", bar_high)
        if range_low is None or bar_low < range_low:
            self.set_state("range_low", bar_low)
        
        bars = self.get_state("range_bars")
        bars.append(bar)
        self.set_state("range_bars", bars)
    
    def _validate_range(self, symbol):
        """
        Validate the accumulated range.
        Must be between min_range_pips and max_range_pips.
        """
        range_high = self.get_state("range_high")
        range_low = self.get_state("range_low")
        
        if range_high is None or range_low is None:
            self.set_state("range_valid", False)
            return
        
        range_pips = self.pips.to_pips(range_high - range_low, symbol)
        
        if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
            self.set_state("range_valid", False)
            return
        
        self.set_state("range_valid", True)
        self.set_state("range_pips", range_pips)
    
    def _check_breakout(self, symbol, bar):
        """
        Check if current bar breaks out of the range with momentum.
        
        Long: close > range_high + buffer AND bullish momentum candle
        Short: close < range_low - buffer AND bearish momentum candle
        """
        range_high = self.get_state("range_high")
        range_low = self.get_state("range_low")
        
        close = float(bar["close"])
        pip_val = self.pips.pip_value(symbol)
        buffer = self.breakout_buffer_pips * pip_val
        
        direction = None
        
        # === Bullish breakout ===
        if close > range_high + buffer:
            if self.pips.candle_body_pct(bar) >= self.min_body_pct:
                if self.pips.candle_direction(bar) == "bullish":
                    direction = "long"
        
        # === Bearish breakout ===
        elif close < range_low - buffer:
            if self.pips.candle_body_pct(bar) >= self.min_body_pct:
                if self.pips.candle_direction(bar) == "bearish":
                    direction = "short"
        
        if direction is None:
            return []
        
        # === Calculate trade setup ===
        stop_buffer = self.stop_buffer_pips * pip_val
        
        if direction == "long":
            entry_price = close
            stop_loss = range_low - stop_buffer
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.risk_reward)
        else:
            entry_price = close
            stop_loss = range_high + stop_buffer
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward)
        
        risk_pips = self.pips.to_pips(risk, symbol)
        
        # === Score the setup ===
        score = self._score_setup(bar, range_high, range_low, buffer, direction, symbol)
        
        # === Record trade for daily limit ===
        self.set_state("trades_today", self.get_state("trades_today") + 1)
        
        # === Build signal ===
        return [self.signal(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                "strategy": "london_breakout",
                "range_high": range_high,
                "range_low": range_low,
                "range_pips": self.get_state("range_pips"),
                "risk_pips": risk_pips,
                "reward_pips": risk_pips * self.risk_reward,
                "body_pct": self.pips.candle_body_pct(bar),
                "score": score,
                "hour_et": self.time.hour_et(bar),
            },
        )]
    
    def _score_setup(self, bar, range_high, range_low, buffer, direction, symbol):
        """
        Score the quality of this setup (0-100).
        
        Factors:
        - Range size in ideal zone (20-40 pips): 25%
        - Strong momentum (70%+ body): 30%
        - Clean break (close within 5 pips of breakout level): 15%
        - Optimal time (8-10 AM ET): 15%
        - Volume increase (not available for forex, default true): 15%
        """
        score = 0
        range_pips = self.get_state("range_pips")
        pip_val = self.pips.pip_value(symbol)
        
        # Range size (25%)
        if 20 <= range_pips <= 40:
            score += 25
        elif 15 <= range_pips <= 50:
            score += 15
        
        # Momentum (30%)
        body_pct = self.pips.candle_body_pct(bar)
        if body_pct >= 0.7:
            score += 30
        elif body_pct >= 0.6:
            score += 20
        
        # Clean break (15%)
        close = float(bar["close"])
        if direction == "long":
            breakout_level = range_high + buffer
            distance_pips = self.pips.to_pips(close - breakout_level, symbol)
        else:
            breakout_level = range_low - buffer
            distance_pips = self.pips.to_pips(breakout_level - close, symbol)
        
        if distance_pips < 5:
            score += 15
        elif distance_pips < 10:
            score += 10
        
        # Time optimality (15%)
        hour = self.time.hour_et(bar)
        if 8 <= hour <= 10:
            score += 15
        elif 10 < hour <= 11:
            score += 10
        
        # Volume (15%) — forex has no volume, default credit
        score += 15
        
        return score


class LondonBreakoutGBP(LondonBreakout):
    """London Breakout on GBP/USD with same parameters."""
    name = "London/NY Breakout GBP"
    description = "London session breakout strategy on GBP/USD"
    symbols = ["GBP_USD"]
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `strategies/london_breakout.py` exists and is auto-discovered on startup |
| AC2 | Strategy has all configurable parameters exposed via `get_parameters()` |
| AC3 | Range detection accumulates high/low during configured range window (default 3-4 AM ET) |
| AC4 | Range validation rejects ranges outside min/max pips thresholds |
| AC5 | Daily state resets at midnight ET (new range, trade counter reset) |
| AC6 | Breakout detected when close exceeds range + buffer with momentum candle |
| AC7 | Momentum confirmation requires body ≥ min_body_pct AND correct candle direction |
| AC8 | Stop loss set at opposite range bound + stop_buffer_pips |
| AC9 | Take profit set at entry + (risk × risk_reward ratio) |
| AC10 | One trade per day limit enforced (configurable max_trades_per_day) |
| AC11 | No signals generated outside entry window (default 8 AM - 12 PM ET) |
| AC12 | Quality scoring system produces scores 0-100 based on 5 weighted factors |
| AC13 | Signal metadata includes range_high, range_low, range_pips, risk_pips, score |
| AC14 | GBP_USD variant exists as a subclass with correct symbol |
| AC15 | Backtest via API produces trades when run against EUR_USD 1h or 5m data |
| AC16 | No existing files modified (only new file in strategies/) |
| AC17 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `strategies/london_breakout.py` | London/NY Breakout strategy + GBP variant |

## Files NOT to Touch

- Backend code (strategy_sdk, backtesting engine)
- Frontend code
- Studio files
- Any existing strategy files

---

## Builder Notes

- **This is a single file.** The entire strategy lives in `strategies/london_breakout.py`. No backend changes needed — the SDK and backtest integration from TASK-043 and TASK-044 handle everything.
- **Use 5m timeframe for the strategy** but backtest on both 5m and 1h to verify. The range detection needs 5m bars during the 3-4 AM window (12 bars per range hour). With 1h bars, you only get 1 bar in the range window, which may not detect the range accurately. The strategy works best with 5m data, but should not crash on 1h — it'll just have fewer range bars.
- **Test the backtest via API after implementation:**
  ```bash
  curl -X POST https://production.ratatoskr.trade/api/v1/python-strategies/London%2FNY%20Breakout/backtest \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{
      "symbols": ["EUR_USD"],
      "timeframe": "1h",
      "startDate": "2025-09-01T00:00:00Z",
      "endDate": "2026-03-17T00:00:00Z",
      "initialCapital": 100000
    }'
  ```
- **The `_validate_range` is called once per day** — after the range window closes. The `range_valid` flag prevents re-validation.
- **The `bar["high"]`, `bar["low"]`, etc. may be Decimal or float** depending on how the backtest runner passes them. Use `float()` conversion to be safe.
- **Volume data:** OANDA forex bars have volume=0 (OANDA doesn't provide tick volume). The scoring system gives 15% credit for volume by default since we can't check it.

## Verification

After building, test with:
```
POST /api/v1/python-strategies/London%2FNY%20Breakout/backtest
Body: {
  "symbols": ["EUR_USD"],
  "timeframe": "1h",
  "startDate": "2025-09-01",
  "endDate": "2026-03-17",
  "initialCapital": 100000
}
```

Expected: trades generated during Dec-Mar period when EUR_USD had clear breakout setups. If 0 trades, check:
1. Are range bars being accumulated? (Add logging temporarily)
2. Is the range valid? (15-50 pips)
3. Does any bar close beyond range + buffer during entry window?
4. Does the momentum filter pass? (Try lowering min_body_pct to 0.4 to test)

## References

- `london_breakout.py` (uploaded by user) — original strategy implementation
- TASK-043 — Strategy SDK base class, indicators, utilities
- TASK-044 — Python backtest integration
