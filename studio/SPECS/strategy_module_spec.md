# STRATEGY_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the strategy module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The strategy module owns:

- Strategy registration, validation, and lifecycle management
- Strategy configuration and versioning
- Indicator library and catalog
- Formula expression parser
- Condition engine
- Strategy runner and evaluation scheduling
- Strategy state persistence
- Safety monitor for orphaned positions
- Manual position close flow (signal origination)

The strategy module does NOT own:

- Market data fetching (calls market_data_service)
- Signal persistence (writes to signals table, owned by signals module)
- Risk evaluation (downstream of signals)
- Order execution (downstream of risk)
- Position persistence (reads from portfolio module)
- Portfolio accounting (owned by portfolio module)

---

## 1. Strategy Architecture Overview

### Design Philosophy

Strategies are primarily **config-driven**. Users build strategies through the
UI by selecting indicators, setting conditions, and configuring risk parameters.
No code is required for the vast majority of strategies.

The system has three layers:

- **Indicator Library** — built-in technical indicators with defined parameters
- **Condition Engine** — combines indicator outputs into logical conditions
- **Strategy Runner** — orchestrates evaluation: load config → fetch bars → compute → decide

### Strategy Types

```
strategy.type: "config" | "custom_code"
```

**Config strategies (Tier 1 + Tier 2):**
Defined entirely through structured configuration. Includes both simple
indicator conditions (Tier 1) and custom formula expressions (Tier 2).
No code required. Built through the UI.

**Custom code strategies (Tier 3, deferred):**
For logic that cannot be expressed through config (ML models, complex
statistical methods). Requires a sandboxed code editor in the browser.
Deferred to a future phase. Architecture should accommodate it but
implementation is not in MVP scope.

---

## 2. Indicator Library

### Purpose

A catalog of technical indicators the system knows how to compute.
Each indicator has defined inputs, parameters, and outputs.
The catalog is exposed via API so the frontend can dynamically
render the strategy builder UI.

### Indicator Registration Schema

```
IndicatorDefinition:
  - key: str                      (e.g., "rsi")
  - name: str                     (e.g., "Relative Strength Index")
  - category: str                 (trend | momentum | volatility | volume | trend_strength | price)
  - description: str
  - parameters:
      - name: str                 (e.g., "period")
      - type: str                 (int | float | select)
      - default: value
      - min: value, nullable      (for int/float)
      - max: value, nullable      (for int/float)
      - options: list, nullable   (for select type)
      - description: str
  - outputs:                      (for multi-output indicators)
      - key: str                  (e.g., "macd_line")
      - name: str                 (e.g., "MACD Line")
  - output_type: str              (number | series | boolean)
  - output_range: [min, max], nullable (e.g., [0, 100] for RSI)
```

### MVP Indicator Catalog

**Trend:**

| Key | Name | Parameters | Outputs |
|-----|------|-----------|---------|
| sma | Simple Moving Average | period (int, 2-500, default 20), source (select: close/open/high/low/hl2/hlc3/ohlc4, default close) | number |
| ema | Exponential Moving Average | period (int, 2-500, default 20), source (select, default close) | number |
| wma | Weighted Moving Average | period (int, 2-500, default 20), source (select, default close) | number |
| vwap | Volume Weighted Average Price | (none, session-based) | number |

**Momentum:**

| Key | Name | Parameters | Outputs |
|-----|------|-----------|---------|
| rsi | Relative Strength Index | period (int, 2-200, default 14), source (select, default close) | number (0-100) |
| macd | MACD | fast (int, 2-100, default 12), slow (int, 2-200, default 26), signal (int, 2-50, default 9) | macd_line, signal_line, histogram |
| stochastic | Stochastic Oscillator | k_period (int, 2-100, default 14), d_period (int, 2-100, default 3), slowing (int, 1-10, default 3) | k, d |
| cci | Commodity Channel Index | period (int, 2-200, default 20) | number |
| mfi | Money Flow Index | period (int, 2-200, default 14) | number (0-100) |
| williams_r | Williams %R | period (int, 2-200, default 14) | number (-100 to 0) |

**Volatility:**

| Key | Name | Parameters | Outputs |
|-----|------|-----------|---------|
| bbands | Bollinger Bands | period (int, 2-200, default 20), std_dev (float, 0.5-5.0, default 2.0) | upper, middle, lower |
| atr | Average True Range | period (int, 2-200, default 14) | number |
| keltner | Keltner Channels | period (int, 2-200, default 20), atr_multiplier (float, 0.5-5.0, default 1.5) | upper, middle, lower |

**Volume:**

| Key | Name | Parameters | Outputs |
|-----|------|-----------|---------|
| volume | Volume | (none, raw bar volume) | number |
| volume_sma | Volume SMA | period (int, 2-200, default 20) | number |
| obv | On Balance Volume | (none) | number |

**Trend Strength:**

| Key | Name | Parameters | Outputs |
|-----|------|-----------|---------|
| adx | Average Directional Index | period (int, 2-100, default 14) | number (0-100) |
| plus_di | Plus Directional Indicator | period (int, 2-100, default 14) | number |
| minus_di | Minus Directional Indicator | period (int, 2-100, default 14) | number |

**Price Reference:**

| Key | Name | Parameters | Outputs |
|-----|------|-----------|---------|
| close | Close Price | (none) | number |
| open | Open Price | (none) | number |
| high | High Price | (none) | number |
| low | Low Price | (none) | number |
| prev_close | Previous Bar Close | (none) | number |
| prev_high | Previous Bar High | (none) | number |
| prev_low | Previous Bar Low | (none) | number |

### Derived Price Sources

Indicators that accept a `source` parameter support derived values:

```
hl2  = (high + low) / 2
hlc3 = (high + low + close) / 3
ohlc4 = (open + high + low + close) / 4
```

Computed automatically from bar data when selected.

### Multi-Output Indicator Handling

When a multi-output indicator is used in a condition, the user specifies
which output to reference:

```
Condition:
  left:
    indicator: "macd"
    params: {"fast": 12, "slow": 26, "signal": 9}
    output: "histogram"
  operator: "crosses_above"
  right:
    type: "value"
    value: 0
```

The UI renders a secondary dropdown for output selection when a
multi-output indicator is chosen.

### Indicator API Endpoint

```
GET /api/v1/strategies/indicators

Response: list of IndicatorDefinition objects
```

The frontend reads this to dynamically render the strategy builder.
Adding a new indicator to the backend automatically makes it available
in the UI with no frontend code changes.

### Implementation Notes

- All indicators are implemented as pure functions
- Each function takes a list of bars and parameters, returns computed values
- Indicators are stateless — the full lookback window is provided each time
- Computation is lightweight: 300 symbols × 5 indicators × 200 bars
  is well under 1 second on modern hardware
- Within a single strategy evaluation, identical indicator computations
  are deduplicated (RSI(14) used in 3 conditions → computed once)

---

## 3. Formula Expression Parser (Tier 2)

### Purpose

Allow power users to define custom indicator expressions without writing
Python code. Expressions are safe by design — the parser only understands
trading math concepts.

### Supported Tokens

```
Numbers:        42, 3.14, 0.5
Arithmetic:     +, -, *, /, %
Comparison:     >, <, >=, <=, ==, !=
Logic:          and, or, not
Grouping:       ( )
Functions:      sma(), ema(), rsi(), atr(), macd(), etc. (all catalog indicators)
Bar fields:     open, high, low, close, volume
History:        prev(expr) — previous bar's value
                prev(expr, N) — N bars ago
Math:           abs(), min(), max()
Cross:          crosses_above(a, b), crosses_below(a, b)
Symbol scoping: close("AAPL"), rsi("MSFT", 14)
```

### NOT Supported (by design)

```
Variable assignment
Loops or iteration
Imports
Function definitions
String operations (beyond symbol names)
File or network access
Any Python builtins beyond basic math
```

### Integration with Condition Engine

Formulas are used anywhere an indicator can be used in a condition:

```
Condition:
  left:
    type: "formula"
    expression: "(close - ema(close, 200)) / atr(14)"
  operator: "greater_than"
  right:
    type: "value"
    value: 1.5
```

The condition engine checks the left/right type:
- type = "indicator" → compute from the catalog
- type = "formula" → run the expression parser

### Validation

Expression validation happens at strategy save time, not at runtime.
The parser checks:

- Syntax is valid
- All function names exist in the indicator whitelist
- All function arguments are the correct count and type
- Symbol references exist on the watchlist

Invalid expressions produce clear error messages:

```
"Formula error: unknown function 'smo', did you mean 'sma'?"
"Formula error: rsi() expects 1-2 arguments (source, period), got 0"
"Formula error: unmatched parenthesis at position 24"
```

---

## 4. Condition Engine

### Purpose

Evaluate condition groups against computed indicator values.
Returns true/false for a given set of conditions against current bar data.

### Condition Structure

**Single condition:**

```
Condition:
  - left:
      type: "indicator" | "formula"
      indicator: str              (if type = indicator)
      params: dict                (if type = indicator)
      output: str, nullable       (for multi-output indicators)
      expression: str             (if type = formula)
  - operator: str
  - right:
      type: "value" | "indicator" | "formula" | "range"
      value: number               (if type = value)
      indicator: str              (if type = indicator)
      params: dict                (if type = indicator)
      output: str, nullable       (if type = indicator, multi-output)
      expression: str             (if type = formula)
      min: number                 (if type = range)
      max: number                 (if type = range)
```

### Supported Operators

**Comparison:**
- greater_than (>)
- less_than (<)
- greater_than_or_equal (>=)
- less_than_or_equal (<=)
- equal (==)

**Crossover (requires current + previous values):**
- crosses_above (was below, now above)
- crosses_below (was above, now below)

**Range:**
- between (left is within [min, max])
- outside (left is outside [min, max])

### Condition Groups

```
ConditionGroup:
  - logic: "and" | "or"
  - conditions: list[Condition | ConditionGroup]
```

Groups can nest for complex logic:

```
AND:
  - RSI(14) > 30
  - RSI(14) < 70
  - OR:
      - close crosses_above EMA(200)
      - close crosses_above SMA(50)
  - ADX(14) > 25
  - volume > 500000
```

### Crossover Detection Logic

```python
def evaluate_crossover(left_series, right_series, direction):
    current_left = left_series[-1]
    previous_left = left_series[-2]
    current_right = right_series[-1]
    previous_right = right_series[-2]

    if direction == "crosses_above":
        return previous_left < previous_right and current_left >= current_right
    elif direction == "crosses_below":
        return previous_left > previous_right and current_left <= current_right
```

### Evaluation Flow

```
1. Parse the condition group from strategy config
2. Collect all unique indicators referenced (deduplicate)
3. Compute each indicator against the bar data (cache results)
4. If formula expressions exist, evaluate through the parser
5. Evaluate each condition using computed values
6. Apply group logic (AND/OR) to combine results
7. Return: true (conditions met) or false (not met)
```

### Error Handling

- Not enough bars for lookback → condition evaluates to false, log warning
- NaN or infinite value → condition evaluates to false, log warning
- Invalid indicator key → caught at save time, never reaches runtime
- Invalid parameters → caught at save time

The engine never crashes. Bad data produces false (don't trade) plus a warning.

---

## 5. Strategy Definition Schema

### Complete Strategy Config

```
StrategyDefinition:
  # Identity
  key: str                          (unique programmatic identifier)
  name: str                         (human-readable display name)
  description: str
  type: str                         (config | custom_code)

  # Scope
  market: str                       (equities | forex | both)
  symbols:
    mode: str                       (explicit | watchlist | filtered)
    list: list[str], nullable       (if mode = explicit)
    market: str, nullable           (if mode = watchlist: equities | forex | all)
    filters: dict, nullable         (if mode = filtered)
      min_volume: int, nullable
      min_price: float, nullable
      sectors: list[str], nullable  (future)
  timeframe: str                    (1m | 5m | 15m | 1h | 4h)
  additional_timeframes: list[str]  (for multi-timeframe strategies)
  lookback_bars: int                (how many bars indicators need)

  # Entry Rules
  entry_conditions: ConditionGroup
  entry_side: str                   (buy | sell | both)

  # Exit Rules
  exit_conditions: ConditionGroup, nullable
  stop_loss:
    type: str                       (percent | atr_multiple | fixed)
    value: float
  take_profit:
    type: str                       (percent | atr_multiple | fixed | risk_multiple)
    value: float
  trailing_stop:
    enabled: bool
    type: str                       (percent | atr_multiple)
    value: float
  max_hold_bars: int, nullable      (time-based exit after N bars)

  # Position Sizing
  position_sizing:
    method: str                     (fixed_qty | fixed_dollar | percent_equity | risk_based)
    value: float
    max_positions: int              (max concurrent positions for this strategy)

  # Execution
  order_type: str                   (market | limit)

  # Schedule
  trading_hours:
    mode: str                       (regular | extended | custom)
    start: str, nullable            (if custom, e.g., "08:00")
    end: str, nullable              (if custom, e.g., "15:00")
    timezone: str, nullable         (if custom, e.g., "US/Eastern")

  # Behavior
  re_entry_cooldown_bars: int       (default: 1, wait N bars before re-entering
                                     after a manual close)

  # State
  enabled: bool
```

### Example: RSI + EMA Momentum Strategy

```json
{
  "key": "rsi_ema_momentum",
  "name": "RSI + EMA Momentum",
  "description": "Enters long when RSI is in range and price crosses above EMA with strong trend",
  "type": "config",
  "market": "equities",
  "symbols": {
    "mode": "explicit",
    "list": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
  },
  "timeframe": "1h",
  "additional_timeframes": [],
  "lookback_bars": 200,

  "entry_conditions": {
    "logic": "and",
    "conditions": [
      {
        "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
        "operator": "less_than",
        "right": {"type": "value", "value": 70}
      },
      {
        "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
        "operator": "greater_than",
        "right": {"type": "value", "value": 30}
      },
      {
        "left": {"type": "indicator", "indicator": "close"},
        "operator": "crosses_above",
        "right": {"type": "indicator", "indicator": "ema", "params": {"period": 200}}
      },
      {
        "left": {"type": "indicator", "indicator": "adx", "params": {"period": 14}},
        "operator": "greater_than",
        "right": {"type": "value", "value": 25}
      },
      {
        "left": {"type": "indicator", "indicator": "volume"},
        "operator": "greater_than",
        "right": {"type": "value", "value": 500000}
      }
    ]
  },

  "entry_side": "buy",

  "exit_conditions": {
    "logic": "or",
    "conditions": [
      {
        "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
        "operator": "greater_than",
        "right": {"type": "value", "value": 75}
      },
      {
        "left": {"type": "indicator", "indicator": "close"},
        "operator": "crosses_below",
        "right": {"type": "indicator", "indicator": "ema", "params": {"period": 200}}
      }
    ]
  },

  "stop_loss": {"type": "percent", "value": 2.0},
  "take_profit": {"type": "risk_multiple", "value": 2.0},
  "trailing_stop": {"enabled": false, "type": "percent", "value": 0},
  "max_hold_bars": null,

  "position_sizing": {
    "method": "percent_equity",
    "value": 5.0,
    "max_positions": 3
  },

  "order_type": "market",

  "trading_hours": {"mode": "regular"},

  "re_entry_cooldown_bars": 1,

  "enabled": true
}
```

---

## 6. Strategy Data Model

### Database Tables

```
Strategy:
  - id: UUID
  - key: str (unique)
  - name: str
  - description: str
  - type: str (config | custom_code)
  - status: str (draft | enabled | paused | disabled)
  - current_version: str
  - market: str (equities | forex | both)
  - auto_pause_error_count: int (default 0)
  - last_evaluated_at: datetime, nullable
  - created_at: datetime
  - updated_at: datetime

  Indexes:
    UNIQUE (key)
    INDEX (status)
    INDEX (market, status)

StrategyConfig:
  - id: UUID
  - strategy_id: UUID (FK → Strategy)
  - version: str
  - config_json: dict (full strategy definition)
  - is_active: bool
  - created_at: datetime

  Indexes:
    INDEX (strategy_id, is_active)
    UNIQUE (strategy_id, version)

StrategyState:
  - id: UUID
  - strategy_id: UUID (FK → Strategy)
  - state_json: dict (runtime state between evaluations)
  - updated_at: datetime

  Notes:
    - One row per strategy
    - state_json stores small tracking values only
    - Persisted periodically and on shutdown
    - Loaded at evaluation start

StrategyEvaluation:
  - id: UUID
  - strategy_id: UUID (FK → Strategy)
  - strategy_version: str
  - evaluated_at: datetime
  - symbols_evaluated: int
  - signals_emitted: int
  - exits_triggered: int
  - errors: int
  - duration_ms: int
  - status: str (success | partial_success | error | skipped)
  - skip_reason: str, nullable
  - details_json: dict, nullable (per-symbol evaluation summary)
  - created_at: datetime

  Indexes:
    INDEX (strategy_id, evaluated_at)
    INDEX (status)

PositionOverride:
  - id: UUID
  - position_id: UUID (FK → Position in portfolio module)
  - strategy_id: UUID (FK → Strategy)
  - override_type: str (stop_loss | take_profit | trailing_stop)
  - original_value_json: dict
  - override_value_json: dict
  - reason: str, nullable
  - created_by: str (user | system)
  - is_active: bool
  - created_at: datetime
  - updated_at: datetime

  Indexes:
    INDEX (position_id, is_active)
```

---

## 7. Strategy Lifecycle

### States

```
draft → enabled → paused → disabled
                    ↑         │
                    └─────────┘
```

**Draft:** Exists but never activated. Freely editable. Not evaluated.

**Enabled:** Live. Runner evaluates on schedule. Signals generated.

**Paused:** Temporarily stopped. Positions remain open under safety monitor.
User explicitly paused, or system auto-paused due to errors.

**Disabled:** Permanently stopped until re-enabled. Positions under safety monitor.

### State Transitions

```
draft → enabled:      user clicks "Enable"
enabled → paused:     user clicks "Pause"
                      OR system auto-pauses after STRATEGY_AUTO_PAUSE_ERROR_THRESHOLD errors
enabled → disabled:   user clicks "Disable"
                      OR risk kill switch triggers
paused → enabled:     user clicks "Resume"
paused → disabled:    user clicks "Disable"
disabled → enabled:   user clicks "Re-enable"
any → draft:          not allowed (once enabled, history exists)
```

### Auto-Pause on Errors

If a strategy throws exceptions on consecutive evaluation cycles:

```
STRATEGY_AUTO_PAUSE_ERROR_THRESHOLD=5
```

After 5 consecutive errors:
1. Strategy status set to "paused"
2. Open positions transfer to safety monitor
3. Alert pushed to user with error details
4. Error count resets when strategy is resumed and evaluates successfully

---

## 8. Strategy Versioning

### When Versions Are Created

A new version is created when any of the following change on an enabled strategy:

- Entry conditions
- Exit conditions
- Indicator parameters
- Stop loss / take profit / trailing stop values
- Position sizing
- Symbol selection
- Timeframe
- Formula expressions

A new version is NOT created for:

- Enable/disable/pause state changes
- Name or description edits

### Version Format

Auto-incrementing: 1.0.0, 1.1.0, 1.2.0, etc.
Minor version bumps for all config changes.
User does not manage version numbers.

### Version Tracking

- Every signal references strategy_id AND strategy_version
- Every evaluation log references strategy_version
- Previous versions are immutable and retained for audit
- The is_active flag marks which config version is current

---

## 9. Live Editing Behavior

### Editing While Enabled

Strategies CAN be edited while enabled. No need to disable first.

**Exit rule changes (stop loss, take profit, trailing stop, exit conditions):**
Apply to existing positions on the next evaluation cycle.
Logged clearly: "Position AAPL stop loss updated from 2.0% to 1.5%
due to strategy config change v1.2.0 → v1.3.0"

**Entry rule changes:**
Affect future evaluations only. Existing positions were entered under
old rules and are not retroactively affected.

**Symbol removal with open positions:**
System prompts the user with three options:
1. Close the position now (emit immediate exit signal)
2. Keep position open with current exit rules (stop/TP still monitored,
   no new entries for this symbol)
3. Transfer to manual management (position stays open, no automated monitoring)

### Edit Confirmation UI

The UI shows a diff before saving:

```
Changes to "RSI + EMA Momentum" (v1.2.0 → v1.3.0):

  Entry Conditions:
    RSI period: 14 → 21
    ADX threshold: 25 → 30

  Exit:
    Stop loss: 2.0% → 1.5%

  ⚠ Warning: Stop loss change will apply to existing positions.

  [Cancel] [Save & Apply]
```

### Position-Level Overrides

Users can override exit rules on individual positions without changing
the strategy config:

```
PositionOverride:
  - position_id: UUID
  - override_type: stop_loss | take_profit | trailing_stop
  - override_value: dict
  - reason: str
```

The evaluation pipeline checks: does this position have an active override?
If yes, use the override. If no, use the strategy config.

Overrides are visible in the UI on the position row and in the position history.

---

## 10. Manual Position Actions

### Available Actions

Users can manually control any position at any time:

- **Close full position** — immediate exit signal for entire position
- **Close partial position** — specify quantity to close (scaling out)
- **Close all positions for a strategy** — liquidate everything under one strategy
- **Close all positions globally** — emergency button, closes everything

### Flow Through the Pipeline

Manual closes go through the standard pipeline (for logging and audit):

```
User clicks "Close Position"
  → POST /api/v1/positions/{id}/close
  → Signal created with source = "manual"
  → Risk gate evaluates (light check — should almost always approve)
  → Paper order created → fill simulated → position updated
```

### Signal Source Values

```
Signal.source:
  - "strategy"    → generated by strategy evaluation
  - "manual"      → user-initiated through the UI
  - "safety"      → generated by the safety monitor
  - "system"      → generated by kill switch or auto-close
```

### Re-Entry Cooldown

After a manual close, the strategy respects a cooldown before re-entering:

```
Strategy config:
  re_entry_cooldown_bars: int (default: 1)
```

Cooldown of 1 = wait at least 1 bar before re-entering that symbol.
Cooldown of 0 = no restriction, can re-enter immediately.

---

## 11. Safety Monitor

### Purpose

Ensures positions always have something watching them, even when their
strategy is paused, disabled, or errored.

### When It Activates

- Strategy paused by user
- Strategy disabled by user
- Strategy auto-paused due to errors
- Strategy evaluation skipped (market data unhealthy)

### What It Does

The safety monitor evaluates ONLY exit rules for orphaned positions:

- Stop loss check against current price
- Take profit check against current price
- Trailing stop check against current price
- Does NOT evaluate entry conditions
- Does NOT run indicator-based exit conditions (only price-based exits)

### Frequency

Runs on the 1m cycle regardless of the strategy's original timeframe.
Tighter monitoring for unmanaged positions.

```
SAFETY_MONITOR_CHECK_INTERVAL_SEC=60
```

### Failure Handling

If the safety monitor itself cannot run (database down, market data unavailable):

1. Log critical error
2. Fire notification channels (email, webhook)
3. Surface persistent banner on dashboard
4. If SAFETY_MONITOR_GLOBAL_KILL_SWITCH is enabled, close all positions

```
SAFETY_MONITOR_FAILURE_ALERT_THRESHOLD=3
SAFETY_MONITOR_GLOBAL_KILL_SWITCH=false  (opt-in)
```

### Alerting on Auto-Pause

```
🚨 ALERT: Strategy "RSI + EMA Momentum" has been auto-paused.

Reason: 5 consecutive evaluation errors
Last error: "KeyError: 'close' in indicator computation"

2 open positions are now under safety monitoring:
  AAPL: 100 shares, stop loss at $183.75
  MSFT: 50 shares, stop loss at $207.90

Action required:
  [View Errors]  [Resume Strategy]  [Close All Positions]
```

---

## 12. Strategy Runner

### Scheduling Model

A single loop runs every minute and checks which strategies need evaluation:

```
Every minute:
  current_time = now()

  for each enabled strategy:
    if strategy.timeframe aligns with current_time:
      queue for evaluation
```

Alignment logic:
- 1m: always aligns
- 5m: minute % 5 == 0
- 15m: minute % 15 == 0
- 1h: minute == 0
- 4h: hour % 4 == 0 and minute == 0

### Evaluation Pipeline (Per Strategy, Per Cycle)

```
1. Pre-checks
   a. Is strategy still enabled?
   b. Is market data healthy for this strategy's symbols?
      → unhealthy: skip, log reason
   c. Is market open for this strategy's market?
      → closed: skip, log reason

2. Resolve symbols
   a. explicit: use the list
   b. watchlist: query current watchlist for strategy's market
   c. filtered: query watchlist with filters applied

3. Fetch bar data
   For each symbol, for each timeframe:
     bars = market_data_service.get_bars(symbol, timeframe, limit=lookback_bars)

   Package as:
   {
     "AAPL": {"1h": [bars...], "4h": [bars...]},
     "MSFT": {"1h": [bars...], "4h": [bars...]}
   }

4. Fetch current positions for this strategy
   positions = portfolio_service.get_positions(strategy_id=strategy.id)

5. Compute indicators
   a. Parse condition groups from config
   b. Collect unique indicators, deduplicate
   c. Compute each against bar data, cache results
   d. Evaluate formula expressions if present

6. Evaluate entry conditions (symbols without positions)
   For each symbol with no position:
     if entry conditions met → create entry signal

7. Evaluate exit conditions (symbols with positions)
   For each symbol with a position:
     Check position overrides first
     if exit conditions met → create exit signal
     Check stop loss → if hit, create exit signal (reason: stop_loss)
     Check take profit → if hit, create exit signal (reason: take_profit)
     Check trailing stop → if triggered, create exit signal (reason: trailing_stop)
     Check max hold bars → if exceeded, create exit signal (reason: max_hold)

8. Emit signals
   For each signal:
     validate (symbol valid, side valid)
     persist to signals table
     log details

9. Log evaluation summary
   "Strategy 'rsi_ema_momentum': symbols=5, signals=1 (BUY AAPL),
    exits=0, duration=45ms"

10. Update strategy state
    Persist state changes
    Update last_evaluated_at
    Reset error count (if was > 0)
```

### Stop Loss / Take Profit Evaluation Detail

**Stop loss (long position):**

```
percent:       stop_price = avg_entry * (1 - value / 100)
atr_multiple:  stop_price = avg_entry - (atr * value)
fixed:         stop_price = avg_entry - value

if current_close <= stop_price → trigger exit
```

For short positions, logic inverts (stop is above entry).

**Take profit (long position):**

```
percent:       target = avg_entry * (1 + value / 100)
atr_multiple:  target = avg_entry + (atr * value)
fixed:         target = avg_entry + value
risk_multiple: target = avg_entry + (risk_amount * value)
               where risk_amount = avg_entry - stop_price

if current_close >= target → trigger exit
```

**Trailing stop:**

```
Track highest_price_since_entry in strategy state (for longs)
trail_price = highest_since_entry * (1 - value / 100)
if current_close <= trail_price → trigger exit

Update highest_price_since_entry on every evaluation
```

### Evaluation Isolation

Each strategy evaluates in its own async task. Strategies cannot affect
each other. Exceptions are caught per-strategy.

```python
async def run_evaluation_cycle():
    due = get_strategies_due_now()
    tasks = [evaluate_strategy(s) for s in due]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for strategy, result in zip(due, results):
        if isinstance(result, Exception):
            log_error(strategy, result)
            increment_error_count(strategy)
            if error_count >= threshold:
                auto_pause(strategy)
        else:
            log_success(strategy, result)
            reset_error_count(strategy)
```

### Market Hours Awareness

**Equities:**
- Regular: 9:30 AM - 4:00 PM ET, Monday-Friday
- Extended: 4:00 AM - 8:00 PM ET (if enabled in strategy config)
- Holidays: closed (holiday calendar required)

**Forex:**
- Open: Sunday 5:00 PM ET through Friday 5:00 PM ET
- Closed: weekends

Strategy config `trading_hours.mode` controls which schedule applies.
Runner skips evaluation outside applicable hours with logged reason.

---

## 13. Strategy Validation Rules

### Validation at Save Time

**Config completeness:**
- At least one entry condition exists
- At least one exit mechanism (exit conditions, stop loss, OR take profit)
- Position sizing defined
- At least one symbol selected (or mode is watchlist/filtered)
- Timeframe set
- Lookback bars >= max indicator period in any condition

**Indicator validity:**
- Every indicator key exists in the catalog
- Every parameter within catalog's min/max range
- Parameter types match (int for int, float for float)
- Multi-output indicators have output field specified

**Formula validity:**
- Expression parses without syntax errors
- All functions in whitelist
- All function arguments correct count and type
- Symbol references on watchlist (if explicit)

**Symbol validity:**
- If mode = explicit: all symbols on active watchlist
- If mode = filtered: at least one symbol matches filter

**Risk sanity checks:**
- Stop loss: 0.1% to 50% (prevents typos)
- Position size: <= 100% of equity
- Max positions: >= 1

### Validation Response

```json
{
  "valid": false,
  "errors": [
    {
      "field": "entry_conditions[2].left.params.period",
      "message": "RSI period must be between 2 and 200, got 500",
      "severity": "error"
    }
  ],
  "warnings": [
    {
      "field": "position_sizing.value",
      "message": "Position size of 25% is high. Consider reducing.",
      "severity": "warning"
    }
  ]
}
```

Errors block saving. Warnings are informational only.

---

## 14. Position Protection Summary

```
Scenario                          Positions
────────────────────────────────────────────────────────
Strategy edited while enabled     Exit rules update next cycle
                                  Entry rules affect future only
                                  Symbol removal prompts user

Strategy paused by user           Safety monitor takes over
                                  Stop/TP still enforced

Strategy disabled by user         Safety monitor takes over
                                  User prompted to close or manage

Strategy auto-paused (errors)     Safety monitor takes over immediately
                                  Alert pushed to user

Market data unhealthy             Evaluation skipped
                                  Safety monitor uses last known prices

Manual close by user              Goes through pipeline (logged/audited)
                                  Cooldown before re-entry

System-level failure              Critical alert
                                  Optional global kill switch
```

Core principle: **a position always has something watching it.**

---

## 15. Folder Structure

```
backend/app/strategies/
    __init__.py
    service.py              ← strategy CRUD, validation, lifecycle
    runner.py               ← evaluation scheduler and pipeline
    models.py               ← SQLAlchemy models
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← strategy module configuration
    safety_monitor.py       ← orphaned position monitoring
    validation.py           ← strategy config validation logic
    indicators/
        __init__.py
        catalog.py          ← indicator registration and metadata
        trend.py            ← SMA, EMA, WMA, VWAP implementations
        momentum.py         ← RSI, MACD, Stochastic, CCI, MFI, Williams %R
        volatility.py       ← Bollinger Bands, ATR, Keltner
        volume.py           ← Volume, Volume SMA, OBV
        trend_strength.py   ← ADX, +DI, -DI
        price.py            ← close, open, high, low, prev values
    conditions/
        __init__.py
        engine.py           ← condition evaluation logic
        operators.py        ← comparison, crossover, range operators
    formulas/
        __init__.py
        parser.py           ← expression tokenizer and AST builder
        evaluator.py        ← expression evaluation against bar data
        validator.py        ← expression validation at save time
    custom/                 ← future: custom code strategies
        __init__.py
        base.py             ← StrategyBase class for custom implementations
```

---

## 16. API Endpoints

```
# Strategy CRUD
GET    /api/v1/strategies                    → list all strategies with status
GET    /api/v1/strategies/:id                → strategy detail with current config
POST   /api/v1/strategies                    → create new strategy (starts as draft)
PUT    /api/v1/strategies/:id                → update strategy config (creates new version if enabled)
DELETE /api/v1/strategies/:id                → delete strategy (only if draft, no history)

# Lifecycle
POST   /api/v1/strategies/:id/enable         → enable (draft → enabled, or re-enable)
POST   /api/v1/strategies/:id/pause          → pause
POST   /api/v1/strategies/:id/resume         → resume from pause
POST   /api/v1/strategies/:id/disable        → disable

# Versioning
GET    /api/v1/strategies/:id/versions        → list all config versions
GET    /api/v1/strategies/:id/versions/:ver   → specific version config

# Evaluation History
GET    /api/v1/strategies/:id/evaluations     → evaluation log with pagination

# Indicator Catalog
GET    /api/v1/strategies/indicators          → full indicator catalog for UI

# Validation
POST   /api/v1/strategies/validate            → validate config without saving

# Manual Position Actions
POST   /api/v1/positions/:id/close            → close full position
POST   /api/v1/positions/:id/close-partial    → close partial (body: {qty})
POST   /api/v1/strategies/:id/close-all       → close all positions for strategy
POST   /api/v1/positions/close-all            → emergency: close all positions globally

# Position Overrides
POST   /api/v1/positions/:id/overrides        → create override (stop loss, TP, etc.)
DELETE /api/v1/positions/:id/overrides/:oid    → remove override
```

---

## 17. Configuration Variables

```
# Strategy Runner
STRATEGY_RUNNER_CHECK_INTERVAL_SEC=60
STRATEGY_AUTO_PAUSE_ERROR_THRESHOLD=5
STRATEGY_EVALUATION_TIMEOUT_SEC=30
STRATEGY_MAX_CONCURRENT_EVALUATIONS=20

# Safety Monitor
SAFETY_MONITOR_CHECK_INTERVAL_SEC=60
SAFETY_MONITOR_FAILURE_ALERT_THRESHOLD=3
SAFETY_MONITOR_GLOBAL_KILL_SWITCH=false

# Validation
STRATEGY_MAX_STOP_LOSS_PERCENT=50
STRATEGY_MAX_POSITION_SIZE_PERCENT=100
```

---

## 18. Database Tables Owned by This Module

| Table | Purpose |
|---|---|
| strategies | Strategy identity, status, lifecycle |
| strategy_configs | Versioned config snapshots |
| strategy_state | Runtime state between evaluations |
| strategy_evaluations | Evaluation log per cycle |
| position_overrides | Per-position exit rule overrides |

---

## Acceptance Criteria

This spec is accepted when:

- Config-driven strategy model is fully defined
- Indicator catalog with all MVP indicators is enumerated
- Condition engine operators (comparison, crossover, range) are specified
- Formula expression parser scope and limits are defined
- Strategy definition schema covers all fields with types and constraints
- Strategy lifecycle states and transitions are explicit
- Live editing behavior and position impact are documented
- Manual position close flow is specified
- Safety monitor responsibilities and failure handling are defined
- Strategy runner evaluation pipeline is step-by-step
- Stop loss / take profit / trailing stop evaluation logic is explicit
- Validation rules cover all edge cases
- Position protection for every scenario is documented
- All API endpoints are listed
- All configuration variables are listed
- All database tables are enumerated
- A builder agent can implement this module without asking engineering design questions
