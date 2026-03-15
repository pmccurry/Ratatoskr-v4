# TASK-040 — Backtest Engine (Backend)

## Goal

Build a synchronous backtest engine that replays historical bars through the existing strategy condition engine, simulates fills, tracks positions/PnL/equity, and stores results. After this task, users can trigger a backtest via API and get comprehensive performance metrics.

## Depends On

TASK-039 (event emissions complete)

## Scope

**In scope:**
- Database models: `backtest_runs`, `backtest_trades`, `backtest_equity_curve`
- Alembic migration for new tables
- Backtest runner: chronological bar replay with indicator computation and condition evaluation
- Fill simulation using existing `FillSimulationEngine`
- Position tracking with configurable exit logic (SL/TP, signal-based, time-based)
- Performance metrics calculation (win rate, Sharpe, drawdown, profit factor, etc.)
- Configurable position sizing (fixed units, fixed cash, percent equity, percent risk)
- API endpoints: POST trigger, GET results/trades/equity-curve, GET list per strategy
- Repository layer for backtest data

**Out of scope:**
- Frontend UI (TASK-041)
- WebSocket progress updates (synchronous design)
- Multi-strategy backtests
- Walk-forward optimization
- Monte Carlo simulation

---

## Database Models

### `backtest_runs`

```python
class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    strategy_id = Column(UUID, ForeignKey("strategies.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    
    # Frozen strategy config at backtest time (so results are reproducible)
    strategy_config = Column(JSONB, nullable=False)
    
    # Backtest parameters
    symbols = Column(JSONB, nullable=False)         # ["EUR_USD", "GBP_USD"]
    timeframe = Column(String(10), nullable=False)   # "1m", "1h", "4h", "1d"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Numeric(20, 2), nullable=False, default=100000)
    
    # Position sizing config
    position_sizing = Column(JSONB, nullable=False)
    # { "type": "fixed", "amount": 10000 }
    # { "type": "fixed_cash", "amount": 5000 }
    # { "type": "percent_equity", "percent": 2 }
    # { "type": "percent_risk", "percent": 1, "stop_pips": 50 }
    
    # Exit configuration
    exit_config = Column(JSONB, nullable=False, default={})
    # {
    #   "stop_loss_pips": 50,        (optional — close at SL)
    #   "take_profit_pips": 100,     (optional — close at TP)
    #   "signal_exit": true,         (close on opposite signal)
    #   "max_hold_bars": 200,        (optional — time-based exit)
    # }
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Results (populated on completion)
    metrics = Column(JSONB, nullable=True)
    bars_processed = Column(Integer, nullable=True)
    total_trades = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
```

### `backtest_trades`

```python
class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    backtest_id = Column(UUID, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)       # "long" or "short"
    quantity = Column(Numeric(20, 6), nullable=False)
    
    entry_time = Column(DateTime, nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=False)
    entry_bar_index = Column(Integer, nullable=False)
    
    exit_time = Column(DateTime, nullable=True)      # null if still open at end
    exit_price = Column(Numeric(20, 8), nullable=True)
    exit_bar_index = Column(Integer, nullable=True)
    exit_reason = Column(String(20), nullable=True)  # "signal", "stop_loss", "take_profit", "time_exit", "end_of_data"
    
    pnl = Column(Numeric(20, 8), nullable=True)
    pnl_percent = Column(Numeric(10, 4), nullable=True)
    fees = Column(Numeric(20, 8), nullable=True)
    
    hold_bars = Column(Integer, nullable=True)
    max_favorable = Column(Numeric(20, 8), nullable=True)   # max favorable excursion (pips)
    max_adverse = Column(Numeric(20, 8), nullable=True)     # max adverse excursion (pips)
```

### `backtest_equity_curve`

```python
class BacktestEquityPoint(Base):
    __tablename__ = "backtest_equity_curve"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    backtest_id = Column(UUID, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    bar_time = Column(DateTime, nullable=False)
    bar_index = Column(Integer, nullable=False)
    equity = Column(Numeric(20, 2), nullable=False)
    cash = Column(Numeric(20, 2), nullable=False)
    open_positions = Column(Integer, nullable=False, default=0)
    unrealized_pnl = Column(Numeric(20, 8), nullable=False, default=0)
    drawdown_pct = Column(Numeric(10, 4), nullable=False, default=0)
```

**Index on `(backtest_id, bar_index)`** for equity curve queries.

---

## Backtest Runner

### Core Algorithm

```python
class BacktestRunner:
    async def run(self, backtest_run: BacktestRun, db: AsyncSession) -> BacktestRun:
        """
        Synchronous (within the request) backtest execution.
        """
        # 1. Load historical bars from DB
        bars = await self._load_bars(
            db, backtest_run.symbols, backtest_run.timeframe,
            backtest_run.start_date, backtest_run.end_date
        )
        
        # 2. Initialize state
        state = BacktestState(
            initial_capital=backtest_run.initial_capital,
            position_sizing=backtest_run.position_sizing,
            exit_config=backtest_run.exit_config,
        )
        
        # 3. Build indicator lookback buffer
        # Need N extra bars before start_date for indicator warmup
        # (e.g., SMA(200) needs 200 bars before the first evaluation)
        
        # 4. Walk through bars chronologically
        for bar_index, bar in enumerate(bars):
            # 4a. Update indicators with new bar
            state.update_indicators(bar)
            
            # 4b. Check exit conditions on open positions
            self._check_exits(state, bar, bar_index)
            
            # 4c. If indicator warmup complete, evaluate entry conditions
            if state.warmup_complete:
                signals = self._evaluate_conditions(
                    backtest_run.strategy_config, state, bar
                )
                
                # 4d. Process entry signals
                for signal in signals:
                    self._process_entry(state, signal, bar, bar_index)
            
            # 4e. Record equity curve point (every N bars for detailed mode)
            state.record_equity(bar, bar_index)
        
        # 5. Close any remaining open positions at last bar
        self._close_all_positions(state, bars[-1], len(bars) - 1, reason="end_of_data")
        
        # 6. Compute final metrics
        metrics = self._compute_metrics(state)
        
        # 7. Store results
        await self._store_results(db, backtest_run, state, metrics)
        
        return backtest_run
```

### Indicator Warmup

The runner must load extra bars BEFORE `start_date` to warm up indicators. The warmup period is determined by the strategy's indicator configuration:

```python
def _calculate_warmup_bars(self, strategy_config: dict) -> int:
    """Find the maximum lookback needed by any indicator."""
    max_period = 0
    for indicator in strategy_config.get("indicators", []):
        for param in indicator.get("params", {}).values():
            if isinstance(param, int):
                max_period = max(max_period, param)
    # Add 20% buffer for indicators like MACD that compound lookbacks
    return int(max_period * 1.2) + 10
```

### Exit Logic

The exit checker runs BEFORE entry evaluation on each bar:

```python
def _check_exits(self, state: BacktestState, bar: dict, bar_index: int):
    for position in state.open_positions[:]:  # copy to allow removal during iteration
        
        # Stop loss check
        if state.exit_config.get("stop_loss_pips"):
            sl_pips = state.exit_config["stop_loss_pips"]
            if position.side == "long":
                sl_price = position.entry_price - Decimal(str(sl_pips)) * Decimal("0.0001")
                if bar["low"] <= sl_price:
                    self._close_position(state, position, sl_price, bar, bar_index, "stop_loss")
                    continue
            else:  # short
                sl_price = position.entry_price + Decimal(str(sl_pips)) * Decimal("0.0001")
                if bar["high"] >= sl_price:
                    self._close_position(state, position, sl_price, bar, bar_index, "stop_loss")
                    continue
        
        # Take profit check
        if state.exit_config.get("take_profit_pips"):
            tp_pips = state.exit_config["take_profit_pips"]
            if position.side == "long":
                tp_price = position.entry_price + Decimal(str(tp_pips)) * Decimal("0.0001")
                if bar["high"] >= tp_price:
                    self._close_position(state, position, tp_price, bar, bar_index, "take_profit")
                    continue
            else:  # short
                tp_price = position.entry_price - Decimal(str(tp_pips)) * Decimal("0.0001")
                if bar["low"] <= tp_price:
                    self._close_position(state, position, tp_price, bar, bar_index, "take_profit")
                    continue
        
        # Time-based exit
        if state.exit_config.get("max_hold_bars"):
            if (bar_index - position.entry_bar_index) >= state.exit_config["max_hold_bars"]:
                self._close_position(state, position, bar["close"], bar, bar_index, "time_exit")
                continue
        
        # Update max favorable/adverse excursion
        position.update_excursion(bar)
```

### Signal-Based Exit

When `exit_config.signal_exit` is true, an entry signal for the opposite direction closes existing positions before opening new ones:

```python
def _process_entry(self, state, signal, bar, bar_index):
    # If signal_exit enabled, close opposite positions first
    if state.exit_config.get("signal_exit"):
        for pos in state.open_positions[:]:
            if pos.symbol == signal.symbol and pos.side != signal.side:
                self._close_position(state, pos, bar["close"], bar, bar_index, "signal")
    
    # Don't open if already have position in same direction for this symbol
    if any(p.symbol == signal.symbol and p.side == signal.side for p in state.open_positions):
        return
    
    # Calculate position size
    quantity = self._calculate_size(state, signal, bar)
    if quantity <= 0:
        return
    
    # Simulate fill
    fill_price = self._simulate_fill(signal.side, bar, state.exit_config)
    fees = self._calculate_fees(fill_price, quantity)
    
    # Open position
    trade = BacktestTradeRecord(
        symbol=signal.symbol,
        side=signal.side,
        quantity=quantity,
        entry_time=bar["timestamp"],
        entry_price=fill_price,
        entry_bar_index=bar_index,
        fees=fees,
    )
    state.open_positions.append(trade)
    state.cash -= (fill_price * quantity) + fees  # for long; reversed for short
```

### Equity Curve Sampling

For detailed mode, record equity at configurable intervals:

```python
def record_equity(self, bar, bar_index):
    # Always record at trade events
    # For detailed mode: record every bar (or every N bars for 1m data)
    sample_interval = 1 if self.timeframe != "1m" else 10  # Every 10 bars for 1m
    
    if bar_index % sample_interval == 0 or self._trade_occurred:
        unrealized = sum(
            self._calc_unrealized(pos, bar) for pos in self.open_positions
        )
        equity = self.cash + unrealized
        peak = max(self.peak_equity, equity)
        drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
        
        self.equity_points.append(EquityPoint(
            bar_time=bar["timestamp"],
            bar_index=bar_index,
            equity=equity,
            cash=self.cash,
            open_positions=len(self.open_positions),
            unrealized_pnl=unrealized,
            drawdown_pct=drawdown,
        ))
        self.peak_equity = peak
```

---

## Performance Metrics

Computed after all bars processed:

```python
def _compute_metrics(self, state: BacktestState) -> dict:
    trades = state.closed_trades
    if not trades:
        return {"total_trades": 0, "note": "No trades generated"}
    
    winners = [t for t in trades if t.pnl > 0]
    losers = [t for t in trades if t.pnl <= 0]
    
    gross_profit = sum(t.pnl for t in winners)
    gross_loss = abs(sum(t.pnl for t in losers))
    
    # Equity curve stats
    returns = []  # per-trade returns for Sharpe
    for t in trades:
        returns.append(float(t.pnl / (t.entry_price * t.quantity)))
    
    metrics = {
        # Trade counts
        "total_trades": len(trades),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": len(winners) / len(trades) * 100,
        
        # PnL
        "total_pnl": float(sum(t.pnl for t in trades)),
        "total_fees": float(sum(t.fees for t in trades)),
        "net_pnl": float(sum(t.pnl - t.fees for t in trades)),
        "avg_pnl_per_trade": float(sum(t.pnl for t in trades) / len(trades)),
        "best_trade": float(max(t.pnl for t in trades)),
        "worst_trade": float(min(t.pnl for t in trades)),
        
        # Ratios
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "avg_win": float(gross_profit / len(winners)) if winners else 0,
        "avg_loss": float(gross_loss / len(losers)) if losers else 0,
        "avg_win_loss_ratio": (float(gross_profit / len(winners)) / float(gross_loss / len(losers))) if losers and winners else 0,
        
        # Risk
        "max_drawdown_pct": float(max(p.drawdown_pct for p in state.equity_points)) if state.equity_points else 0,
        "sharpe_ratio": self._annualized_sharpe(returns, state.timeframe),
        
        # Duration
        "avg_hold_bars": sum(t.hold_bars for t in trades) / len(trades),
        "max_hold_bars": max(t.hold_bars for t in trades),
        
        # Streaks
        "max_winning_streak": self._max_streak(trades, winning=True),
        "max_losing_streak": self._max_streak(trades, winning=False),
        
        # Excursion
        "avg_max_favorable": float(sum(t.max_favorable or 0 for t in trades) / len(trades)),
        "avg_max_adverse": float(sum(t.max_adverse or 0 for t in trades) / len(trades)),
        
        # Capital
        "initial_capital": float(state.initial_capital),
        "final_equity": float(state.equity_points[-1].equity) if state.equity_points else float(state.initial_capital),
        "total_return_pct": 0,  # computed below
        "bars_processed": state.bars_processed,
    }
    
    metrics["total_return_pct"] = (
        (metrics["final_equity"] - metrics["initial_capital"]) 
        / metrics["initial_capital"] * 100
    )
    
    return metrics
```

### Sharpe Ratio (annualized)

```python
def _annualized_sharpe(self, returns: list[float], timeframe: str) -> float:
    if len(returns) < 2:
        return 0.0
    
    import numpy as np
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    if std_return == 0:
        return 0.0
    
    # Annualization factor depends on timeframe
    periods_per_year = {
        "1m": 525600,   # 365 * 24 * 60
        "1h": 8760,     # 365 * 24
        "4h": 2190,     # 365 * 6
        "1d": 365,
    }
    factor = periods_per_year.get(timeframe, 365)
    
    # Sharpe = (mean / std) * sqrt(annualization_factor)
    # But we compute per-trade, so use trades per year instead
    return float((mean_return / std_return) * np.sqrt(min(len(returns), factor)))
```

---

## API Endpoints

### `POST /api/v1/strategies/{strategy_id}/backtest`

Triggers a backtest. Synchronous — blocks until complete (30-120 seconds typical).

```python
@router.post("/{strategy_id}/backtest")
async def create_backtest(
    strategy_id: UUID,
    request: BacktestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Load and validate strategy exists
    strategy = await strategy_service.get_by_id(db, strategy_id, user.id)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    
    # 2. Create backtest run record
    run = BacktestRun(
        strategy_id=strategy_id,
        status="running",
        strategy_config=strategy.config,  # freeze current config
        symbols=request.symbols,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        position_sizing=request.position_sizing,
        exit_config=request.exit_config,
        started_at=datetime.utcnow(),
    )
    await backtest_repo.create(db, run)
    await db.commit()
    
    # 3. Run backtest (synchronous within this request)
    try:
        runner = BacktestRunner()
        run = await runner.run(run, db)
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
    except Exception as e:
        run.status = "failed"
        run.error = str(e)
        run.completed_at = datetime.utcnow()
    
    await db.commit()
    
    # 4. Return results
    return {"data": backtest_run_to_response(run)}
```

**Request body:**
```json
{
  "symbols": ["EUR_USD", "GBP_USD"],
  "timeframe": "1h",
  "startDate": "2025-06-01T00:00:00Z",
  "endDate": "2025-12-31T23:59:59Z",
  "initialCapital": 100000,
  "positionSizing": {
    "type": "fixed",
    "amount": 10000
  },
  "exitConfig": {
    "stopLossPips": 50,
    "takeProfitPips": 100,
    "signalExit": true,
    "maxHoldBars": 200
  }
}
```

### `GET /api/v1/backtests/{backtest_id}`

Returns the backtest run with metrics.

### `GET /api/v1/backtests/{backtest_id}/trades`

Returns the trade list with pagination (`?page=1&limit=50`).

### `GET /api/v1/backtests/{backtest_id}/equity-curve`

Returns the equity curve points. Supports `?sample=100` to downsample for charting.

### `GET /api/v1/strategies/{strategy_id}/backtests`

Returns all backtests for a strategy, ordered by created_at desc.

---

## Position Sizing Implementation

```python
def _calculate_size(self, state: BacktestState, signal, bar) -> Decimal:
    config = state.position_sizing
    sizing_type = config["type"]
    price = bar["close"]
    
    if sizing_type == "fixed":
        return Decimal(str(config["amount"]))
    
    elif sizing_type == "fixed_cash":
        cash_amount = Decimal(str(config["amount"]))
        return (cash_amount / price).quantize(Decimal("0.01"))
    
    elif sizing_type == "percent_equity":
        equity = state.get_current_equity(bar)
        cash_amount = equity * Decimal(str(config["percent"])) / Decimal("100")
        return (cash_amount / price).quantize(Decimal("0.01"))
    
    elif sizing_type == "percent_risk":
        equity = state.get_current_equity(bar)
        risk_amount = equity * Decimal(str(config["percent"])) / Decimal("100")
        stop_pips = Decimal(str(config.get("stop_pips", 50)))
        pip_value = Decimal("0.0001")  # forex standard
        return (risk_amount / (stop_pips * pip_value)).quantize(Decimal("0.01"))
    
    return Decimal("0")
```

---

## Fill Simulation

Reuse the existing `FillSimulationEngine` where possible. For backtest fills:

```python
def _simulate_fill(self, side: str, bar: dict, exit_config: dict) -> Decimal:
    """Simulate entry fill price with slippage."""
    price = bar["close"]  # fill at close of signal bar
    
    # Apply slippage (configurable, default 0.5 pips for forex)
    slippage = Decimal("0.00005")  # 0.5 pips
    if side == "long":
        return price + slippage
    else:
        return price - slippage

def _calculate_fees(self, price: Decimal, quantity: Decimal) -> Decimal:
    """Calculate trading fees (spread cost)."""
    spread_bps = Decimal("2")  # 2 bps default
    return (price * quantity * spread_bps / Decimal("10000")).quantize(Decimal("0.00000001"))
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Alembic migration creates `backtest_runs`, `backtest_trades`, `backtest_equity_curve` tables |
| AC2 | `POST /strategies/{id}/backtest` runs synchronously and returns complete results |
| AC3 | Backtest runner walks bars chronologically and evaluates strategy conditions correctly |
| AC4 | Indicator warmup: loads extra bars before start_date, doesn't generate signals during warmup |
| AC5 | Fill simulation applies slippage and fees |
| AC6 | Stop loss exit works: position closes when bar low/high crosses SL price |
| AC7 | Take profit exit works: position closes when bar high/low crosses TP price |
| AC8 | Signal-based exit works: opposite signal closes existing position |
| AC9 | Time-based exit works: position closes after max_hold_bars |
| AC10 | Open positions force-closed at end of data with reason "end_of_data" |
| AC11 | All 4 position sizing types work correctly (fixed, fixed_cash, percent_equity, percent_risk) |
| AC12 | Performance metrics computed correctly (win rate, Sharpe, drawdown, profit factor, etc.) |
| AC13 | Equity curve recorded at appropriate intervals (every bar for 1h/4h/1d, sampled for 1m) |
| AC14 | `GET /backtests/{id}` returns run details with metrics |
| AC15 | `GET /backtests/{id}/trades` returns trade list with pagination |
| AC16 | `GET /backtests/{id}/equity-curve` returns equity points with optional downsampling |
| AC17 | `GET /strategies/{id}/backtests` returns list of all backtests for strategy |
| AC18 | Strategy config is frozen at backtest time (changes to strategy don't affect past results) |
| AC19 | Failed backtests store error message and set status to "failed" |
| AC20 | All financial calculations use Decimal (not float) |
| AC21 | No frontend code modified |
| AC22 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/backtesting/__init__.py` | Module init |
| `backend/app/backtesting/models.py` | BacktestRun, BacktestTrade, BacktestEquityPoint |
| `backend/app/backtesting/runner.py` | BacktestRunner with bar replay loop |
| `backend/app/backtesting/state.py` | BacktestState (positions, equity, indicators) |
| `backend/app/backtesting/metrics.py` | Performance metrics computation |
| `backend/app/backtesting/sizing.py` | Position sizing logic |
| `backend/app/backtesting/repository.py` | Database operations |
| `backend/app/backtesting/router.py` | API endpoints |
| `backend/app/backtesting/schemas.py` | Pydantic request/response schemas |
| `backend/alembic/versions/xxx_create_backtest_tables.py` | Migration |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/main.py` | Register backtest router |

## Files NOT to Touch

- Frontend code
- Existing strategy/indicator/condition code (import and reuse, don't modify)
- Studio files
- Test files

---

## Builder Notes

- **Reuse the existing indicator library.** The strategy runner already computes SMA, EMA, RSI, MACD, Bollinger, etc. Import and use the same indicator computation functions. Don't reimplement.
- **Reuse the existing condition engine.** The condition evaluator (`evaluate_conditions()` or equivalent) already handles all 9 operators. Import and use it.
- **Forex pip value.** For forex, 1 pip = 0.0001 for most pairs, 0.01 for JPY pairs. Handle this in the SL/TP calculations.
- **Synchronous within async.** The endpoint is `async def` but the backtest runs in-process. Use `await` for DB operations but the bar loop itself is CPU-bound Python. For 43K bars (30 days of 1m data), this should complete in 5-30 seconds.
- **Don't over-engineer.** This is V1. A simple `for bar in bars` loop with indicator updates is fine. No vectorized/numpy operations needed yet.
- **The `backtesting` module is a NEW module.** It follows the same structure as other modules (models, repository, service/runner, router, schemas). Register it as `/api/v1/backtesting/` for run-specific endpoints and add the trigger under `/api/v1/strategies/{id}/backtest`.

## References

- strategy_module_spec.md — indicator library, condition engine, formula parser
- paper_trading_module_spec.md — fill simulation engine
- cross_cutting_specs.md §5 — API conventions (response envelope, camelCase)
- DECISIONS.md — Decimal for financial values
