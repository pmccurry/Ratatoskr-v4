# TASK-044 — Backtest Engine Integration for Python Strategies

## Goal

Modify the backtest engine to execute Python-based strategies (from the strategy_sdk) in addition to condition-based strategies. After this task, you can backtest any Python strategy file against historical data and get the same metrics, equity curve, and trade table as condition-based backtests.

## Depends On

TASK-043 (Strategy SDK)

## Architecture

The backtest engine currently does:
```
Load bars → for each bar → condition_engine.evaluate() → signals → fill sim → track PnL
```

After this task, it also supports:
```
Load bars → for each bar → strategy.on_bar() → signals → fill sim → track PnL
```

Same loop, same fill simulation, same equity tracking, same metrics. The only change is how signals are generated — `condition_engine.evaluate()` vs `strategy.on_bar()`.

## Scope

**In scope:**
- New API endpoint: `POST /api/v1/python-strategies/{name}/backtest`
- Backtest runner calls `strategy.on_bar(symbol, bar, history_df)` instead of condition engine
- Strategy receives a growing DataFrame of historical bars as `history`
- Strategy's `on_start()` called before bar loop, `on_stop()` after
- Strategy's position state updated between bars (so `has_position()` works)
- Strategy's signals include SL/TP which the backtest engine uses for exit logic
- Configurable parameters can be overridden per backtest run
- Results stored in same `backtest_runs`, `backtest_trades`, `backtest_equity_curve` tables
- Same metrics computation, same equity curve, same trade table
- CLI command: `python -m app.backtesting.cli backtest strategies/london_breakout.py`

**Out of scope:**
- London Breakout strategy (TASK-045)
- Frontend UI changes (TASK-046)
- Live paper trading hookup (market data stream integration)
- Changes to condition-based backtest path (stays working as-is)

---

## Deliverables

### D1 — Python Strategy Backtest Runner

Create `backend/app/backtesting/python_runner.py`:

```python
class PythonBacktestRunner:
    """
    Runs a Python strategy against historical bars for backtesting.
    
    Reuses the existing BacktestState, fill simulation, and metrics
    computation from the condition-based backtest runner.
    """
    
    async def run(self, backtest_run: BacktestRun, strategy: Strategy, db: AsyncSession):
        """
        Execute a Python strategy backtest.
        
        1. Load historical bars from DB (with warmup period)
        2. Call strategy.on_start()
        3. For each bar:
           a. Build history DataFrame (all bars up to current)
           b. Check exits on open positions (SL/TP/time from signal metadata)
           c. Call strategy.on_bar(symbol, bar, history)
           d. Process returned signals (simulate fills, track positions)
           e. Record equity curve
        4. Close remaining positions at end of data
        5. Call strategy.on_stop()
        6. Compute metrics
        7. Store results
        """
```

Key differences from the condition-based runner:

1. **Signal source:** `strategy.on_bar()` returns `StrategySignal` objects instead of the condition engine returning matches
2. **SL/TP per signal:** Each signal can have its own stop_loss and take_profit (dynamic, not fixed pips). The exit checker uses the signal's SL/TP, not a global config.
3. **Strategy state:** The runner updates `strategy.positions` and `strategy.equity` between bars so the strategy can make decisions based on current state.
4. **History DataFrame:** The strategy receives a growing pandas DataFrame of all bars up to the current one. The runner builds this incrementally.
5. **Parameter overrides:** The backtest request can override strategy class attributes (e.g., change `risk_reward` from 1.5 to 2.0 for a specific backtest).

### D2 — API Endpoint

Add to `backend/app/strategy_sdk/router.py` or `backend/app/backtesting/router.py`:

```python
@router.post("/api/v1/python-strategies/{name}/backtest")
async def backtest_python_strategy(
    name: str,
    request: PythonBacktestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run a backtest on a Python strategy.
    
    Request body:
    {
        "symbols": ["EUR_USD"],           # Override strategy's default symbols
        "timeframe": "1h",                # Override strategy's default timeframe
        "startDate": "2025-06-01",
        "endDate": "2026-03-01",
        "initialCapital": 100000,
        "positionSizing": {               # Backtest-specific sizing
            "type": "fixed",
            "amount": 10000
        },
        "parameterOverrides": {           # Override strategy class params
            "risk_reward": 2.0,
            "min_range_pips": 20
        }
    }
    
    Returns same BacktestRunResponse as condition-based backtests.
    """
```

The response format is identical to `GET /backtests/{id}` — same metrics, same structure. The results endpoints (`/backtests/{id}/trades`, `/backtests/{id}/equity-curve`) work for both strategy types since they read from the same tables.

### D3 — Request Schema

```python
class PythonBacktestRequest(BaseModel):
    symbols: list[str] | None = None        # None = use strategy defaults
    timeframe: str | None = None             # None = use strategy defaults
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000
    position_sizing: dict | None = None      # None = use signal quantities
    parameter_overrides: dict | None = None   # Override strategy class attributes
    
    class Config:
        alias_generator = to_camel
        populate_by_name = True
```

### D4 — Exit Logic for Python Strategies

Python strategies provide SL/TP per signal (not global pips). The exit checker needs to handle this:

```python
def _check_exits_python(self, state, bar, bar_index):
    """Check exits using per-trade SL/TP from the original signal."""
    for position in state.open_positions[:]:
        # Stop loss from the signal
        if position.stop_loss is not None:
            if position.side == "long" and bar["low"] <= float(position.stop_loss):
                self._close_position(state, position, float(position.stop_loss), 
                                    bar, bar_index, "stop_loss")
                continue
            elif position.side == "short" and bar["high"] >= float(position.stop_loss):
                self._close_position(state, position, float(position.stop_loss),
                                    bar, bar_index, "stop_loss")
                continue
        
        # Take profit from the signal
        if position.take_profit is not None:
            if position.side == "long" and bar["high"] >= float(position.take_profit):
                self._close_position(state, position, float(position.take_profit),
                                    bar, bar_index, "take_profit")
                continue
            elif position.side == "short" and bar["low"] <= float(position.take_profit):
                self._close_position(state, position, float(position.take_profit),
                                    bar, bar_index, "take_profit")
                continue
```

### D5 — Position Sizing Integration

When the signal includes a `quantity`, use it directly. When it doesn't, fall back to the backtest config's position sizing:

```python
def _get_quantity(self, signal: StrategySignal, state, bar):
    """Determine position size for a signal."""
    if signal.quantity is not None and signal.quantity > 0:
        return signal.quantity
    
    # Fall back to backtest config sizing
    if state.position_sizing:
        return calculate_size(state, signal.direction, bar, signal.symbol)
    
    # Default: 10,000 units for forex
    return Decimal("10000")
```

### D6 — Strategy State Synchronization

Between bars, update the strategy instance with current backtest state:

```python
# Before calling strategy.on_bar():
strategy.positions = self._get_open_positions_dict(state)
strategy.equity = state.get_current_equity(bar)
strategy.cash = state.cash
```

This way, `strategy.has_position("EUR_USD")` and `strategy.position_count()` return accurate values during backtesting.

### D7 — Parameter Override Support

Allow backtest requests to override strategy parameters:

```python
def _apply_overrides(self, strategy: Strategy, overrides: dict | None):
    """Apply parameter overrides to a strategy instance."""
    if not overrides:
        return
    
    declared_params = strategy.get_parameters()
    for key, value in overrides.items():
        if hasattr(strategy, key):
            # Validate against declared parameter constraints
            param_def = declared_params.get(key, {})
            if param_def.get("min") is not None and value < param_def["min"]:
                raise ValueError(f"Parameter {key} below minimum {param_def['min']}")
            if param_def.get("max") is not None and value > param_def["max"]:
                raise ValueError(f"Parameter {key} above maximum {param_def['max']}")
            setattr(strategy, key, value)
        else:
            raise ValueError(f"Unknown parameter: {key}")
```

### D8 — CLI Command (optional but useful)

Create `backend/app/backtesting/cli.py`:

```python
"""
CLI for running backtests.

Usage:
    cd backend
    python -m app.backtesting.cli backtest strategies/london_breakout.py \
        --symbols EUR_USD --timeframe 1h \
        --start 2025-06-01 --end 2026-03-01 \
        --capital 100000
"""
import asyncio
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Ratatoskr Backtest CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    bt_parser = subparsers.add_parser("backtest", help="Run a backtest")
    bt_parser.add_argument("strategy_file", help="Path to strategy Python file")
    bt_parser.add_argument("--symbols", nargs="+", help="Symbols to test")
    bt_parser.add_argument("--timeframe", default="1h")
    bt_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    bt_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    bt_parser.add_argument("--capital", type=float, default=100000)
    bt_parser.add_argument("--param", nargs=2, action="append", metavar=("KEY", "VALUE"),
                          help="Override strategy parameter")
    
    args = parser.parse_args()
    
    if args.command == "backtest":
        asyncio.run(run_backtest(args))
    else:
        parser.print_help()


async def run_backtest(args):
    """Execute a backtest from CLI arguments."""
    # Load strategy file
    # Connect to database
    # Run PythonBacktestRunner
    # Print results to stdout
    # Results also stored in DB (viewable in dashboard)
    ...


if __name__ == "__main__":
    main()
```

### D9 — BacktestRun Model Update

Add a `strategy_type` field to distinguish Python vs condition-based backtests:

```python
# In backtest_runs table / BacktestRun model:
strategy_type = Column(String(20), default="conditions")  # "conditions" or "python"
strategy_file = Column(String(255), nullable=True)         # "london_breakout.py" for python type
```

This is a small migration addition. Existing backtests get `strategy_type = "conditions"` as default.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `POST /api/v1/python-strategies/{name}/backtest` endpoint exists and returns results |
| AC2 | Python strategy's `on_start()` called before bar loop |
| AC3 | Python strategy's `on_bar()` called for each bar with correct symbol, bar dict, and history DataFrame |
| AC4 | Python strategy's `on_stop()` called after bar loop |
| AC5 | History DataFrame grows with each bar (strategy sees all bars up to current) |
| AC6 | Signals returned from `on_bar()` are processed through fill simulation |
| AC7 | Per-signal SL/TP used for exit checks (not global pips) |
| AC8 | When signal has no quantity, falls back to backtest position sizing config |
| AC9 | When signal has quantity, uses it directly |
| AC10 | Strategy's `positions`, `equity`, `cash` updated between bars |
| AC11 | `has_position()` and `position_count()` return accurate values during backtest |
| AC12 | Parameter overrides apply to strategy instance for that backtest run |
| AC13 | Invalid parameter overrides return 400 error |
| AC14 | Results stored in same tables as condition-based backtests |
| AC15 | Existing condition-based backtest path unchanged and still working |
| AC16 | `backtest_runs` table has `strategy_type` field ("conditions" or "python") |
| AC17 | Example SMA Crossover backtest produces trades and metrics |
| AC18 | CLI command runs a backtest and prints results (basic implementation) |
| AC19 | No frontend code modified |
| AC20 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/backtesting/python_runner.py` | Python strategy backtest execution |
| `backend/app/backtesting/cli.py` | CLI for running backtests |
| `backend/migrations/versions/xxx_add_strategy_type.py` | Migration adding strategy_type column |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/backtesting/models.py` | Add strategy_type and strategy_file columns |
| `backend/app/backtesting/schemas.py` | Add PythonBacktestRequest schema |
| `backend/app/strategy_sdk/router.py` | Add backtest endpoint |
| `backend/app/backtesting/state.py` | Ensure BacktestTradeRecord stores per-signal SL/TP |

## Files NOT to Touch

- `backend/app/backtesting/runner.py` (existing condition-based runner — unchanged)
- Frontend code
- Studio files
- Existing strategy_sdk files from TASK-043

---

## Builder Notes

- **Reuse as much as possible from the existing backtest runner.** The fill simulation, equity curve recording, metrics computation, and result storage are identical. Extract shared logic into helper functions if needed, or import directly from the existing runner.
- **The history DataFrame grows incrementally.** Don't rebuild it from scratch on each bar. Start with warmup bars as a DataFrame, then append each new bar. Use `pd.concat` or pre-allocate and slice.
- **Per-signal SL/TP is the key difference.** Condition-based backtests use global `exit_config.stop_loss_pips`. Python strategies set SL/TP on each signal individually (because London Breakout calculates SL from the session range, which changes daily).
- **The BacktestTradeRecord needs to store the signal's SL/TP.** When a signal creates a position, store `stop_loss` and `take_profit` on the trade record so the exit checker can reference them.
- **Parameter overrides create a fresh strategy instance.** Don't modify the registered singleton — create a new instance of the class and apply overrides to it. This way concurrent backtests with different params don't interfere.
- **The CLI is a convenience tool.** It connects to the database, runs the backtest, prints a summary table to stdout, and stores results in the DB. Keep it simple — argparse, asyncio.run, print results.
- **The migration should have a safe default.** Add `strategy_type` with `server_default="conditions"` so existing rows are automatically filled.

## References

- TASK-043 — Strategy SDK (base class, signals, indicators, runner)
- TASK-040 — Existing backtest engine (condition-based runner, state, metrics)
- backend/app/backtesting/runner.py — existing runner to reuse/reference
- backend/app/backtesting/state.py — BacktestState, BacktestTradeRecord
- backend/app/backtesting/metrics.py — metrics computation
