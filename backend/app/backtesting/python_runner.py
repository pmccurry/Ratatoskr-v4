"""Backtest runner for Python SDK strategies."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.state import BacktestState, BacktestTradeRecord
from app.backtesting.sizing import calculate_position_size
from app.backtesting.metrics import compute_metrics
from app.strategy_sdk.base import Strategy
from app.strategy_sdk.signal import StrategySignal

logger = logging.getLogger(__name__)


class PythonBacktestRunner:
    """Runs a Python strategy against historical bars for backtesting."""

    async def run(self, backtest_run, strategy: Strategy, db: AsyncSession, *, store_results: bool = True) -> dict:
        """Execute a Python strategy backtest."""
        symbols = backtest_run.symbols
        timeframe = backtest_run.timeframe

        # Load bars (reuse same logic as condition runner)
        warmup_bars = 200  # generous warmup for Python strategies
        all_bars = await self._load_bars(
            db, symbols, timeframe,
            backtest_run.start_date, backtest_run.end_date, warmup_bars
        )

        if not all_bars:
            return {"total_trades": 0, "note": "No bars found", "bars_processed": 0}

        # Initialize state
        state = BacktestState(
            initial_capital=Decimal(str(backtest_run.initial_capital)),
            position_sizing=backtest_run.position_sizing or {},
            exit_config={},  # Python strategies use per-signal SL/TP
            timeframe=timeframe,
        )

        # Call strategy lifecycle
        strategy.on_start()

        try:
            # Process bars per symbol
            for symbol in symbols:
                symbol_bars_raw = all_bars.get(symbol, [])
                if not symbol_bars_raw:
                    continue

                bar_dicts = self._bars_to_dicts(symbol_bars_raw)

                # Build DataFrame incrementally
                all_bar_dicts = bar_dicts

                for bar_index in range(len(all_bar_dicts)):
                    current_bar = all_bar_dicts[bar_index]

                    # Build history DataFrame (all bars up to and including current)
                    history_slice = all_bar_dicts[:bar_index + 1]
                    history_df = pd.DataFrame(history_slice)
                    # Ensure numeric columns are float (not Decimal)
                    for col in ["open", "high", "low", "close", "volume"]:
                        if col in history_df.columns:
                            history_df[col] = history_df[col].astype(float)

                    # Mark warmup complete
                    if bar_index >= warmup_bars and not state.warmup_complete:
                        state.warmup_complete = True

                    # Check exits first (per-signal SL/TP)
                    self._check_exits_python(state, current_bar, bar_index)

                    # Sync strategy state
                    strategy.positions = self._get_positions_dict(state)
                    strategy.equity = state.get_current_equity(current_bar)
                    strategy.cash = state.cash

                    # Call strategy (only after warmup)
                    if state.warmup_complete:
                        try:
                            signals = strategy.on_bar(symbol, current_bar, history_df)
                            if signals:
                                for sig in signals:
                                    self._process_signal(state, sig, current_bar, bar_index)
                        except Exception as e:
                            logger.error("Strategy error on bar %d: %s", bar_index, e)

                    # Update excursion
                    for pos in state.open_positions:
                        if pos.symbol == symbol:
                            pos.update_excursion(current_bar)

                    # Record equity
                    state.record_equity(current_bar, bar_index)

            # Ensure at least one equity point
            if not state.equity_points and all_bars:
                for sym_bars in all_bars.values():
                    if sym_bars:
                        last_dicts = self._bars_to_dicts(sym_bars)
                        last_bar = last_dicts[-1]
                        state._trade_occurred = True
                        state.record_equity(last_bar, len(last_dicts) - 1)
                        break

            # Close remaining positions
            if all_bars:
                for sym_bars in all_bars.values():
                    if sym_bars:
                        last_dicts = self._bars_to_dicts(sym_bars)
                        last_bar = last_dicts[-1]
                        last_idx = len(last_dicts) - 1
                        for pos in state.open_positions[:]:
                            self._close_position(state, pos, last_bar["close"], last_bar, last_idx, "end_of_data")
                        break
        finally:
            strategy.on_stop()

        # Compute metrics
        metrics = compute_metrics(state)

        # Store results (skipped in CLI mode)
        if store_results:
            await self._store_results(db, backtest_run, state, metrics)

        return metrics

    def _check_exits_python(self, state, bar, bar_index):
        """Check per-signal SL/TP exits."""
        for pos in state.open_positions[:]:
            # Stop loss (stored on trade record)
            if pos.stop_loss is not None:
                sl = float(pos.stop_loss)
                if pos.side == "long" and float(bar["low"]) <= sl:
                    self._close_position(state, pos, Decimal(str(sl)), bar, bar_index, "stop_loss")
                    continue
                elif pos.side == "short" and float(bar["high"]) >= sl:
                    self._close_position(state, pos, Decimal(str(sl)), bar, bar_index, "stop_loss")
                    continue

            # Take profit
            if pos.take_profit is not None:
                tp = float(pos.take_profit)
                if pos.side == "long" and float(bar["high"]) >= tp:
                    self._close_position(state, pos, Decimal(str(tp)), bar, bar_index, "take_profit")
                    continue
                elif pos.side == "short" and float(bar["low"]) <= tp:
                    self._close_position(state, pos, Decimal(str(tp)), bar, bar_index, "take_profit")
                    continue

    def _process_signal(self, state, signal: StrategySignal, bar, bar_index):
        """Process a StrategySignal into a position."""
        symbol = signal.symbol
        side = signal.direction

        # Don't open if already have same-direction position
        if any(p.symbol == symbol and p.side == side for p in state.open_positions):
            return

        # Determine quantity
        if signal.quantity is not None and signal.quantity > 0:
            quantity = Decimal(str(signal.quantity))
        elif state.position_sizing:
            equity = state.get_current_equity(bar)
            quantity = calculate_position_size(state.position_sizing, equity, bar["close"], symbol)
        else:
            quantity = Decimal("10000")  # Default forex

        if quantity <= 0:
            return

        # Check cash
        cost = bar["close"] * quantity
        if side == "long" and cost > state.cash:
            return

        # Fill price with slippage
        fill_price = self._simulate_fill(side, bar, symbol)
        fees = self._calculate_fees(fill_price, quantity)

        # Create trade record with per-signal SL/TP
        trade = BacktestTradeRecord(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_time=bar["timestamp"],
            entry_price=fill_price,
            entry_bar_index=bar_index,
            fees=fees,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
        state.open_positions.append(trade)

        # Deduct cash
        if side == "long":
            state.cash -= (fill_price * quantity) + fees
        else:
            state.cash -= fees

        state._trade_occurred = True

    def _close_position(self, state, pos, exit_price, bar, bar_index, reason):
        """Close a position and record PnL."""
        pos.exit_time = bar["timestamp"]
        pos.exit_price = exit_price
        pos.exit_bar_index = bar_index
        pos.exit_reason = reason
        pos.hold_bars = bar_index - pos.entry_bar_index

        if pos.side == "long":
            pos.pnl = (exit_price - pos.entry_price) * pos.quantity
        else:
            pos.pnl = (pos.entry_price - exit_price) * pos.quantity

        cost = pos.entry_price * pos.quantity
        if cost > 0:
            pos.pnl_percent = (pos.pnl / cost * Decimal("100")).quantize(Decimal("0.01"))

        if pos.side == "long":
            state.cash += exit_price * pos.quantity
        else:
            state.cash += pos.entry_price * pos.quantity + pos.pnl

        if pos in state.open_positions:
            state.open_positions.remove(pos)
        state.closed_trades.append(pos)
        state._trade_occurred = True

    def _simulate_fill(self, side, bar, symbol):
        """Simulate entry fill price with slippage."""
        pip_val = self._get_pip_value(symbol)
        slippage = Decimal("0.5") * pip_val
        price = bar["close"]
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        return price + slippage if side == "long" else price - slippage

    def _calculate_fees(self, price, quantity):
        """Calculate trading fees (spread cost)."""
        spread_bps = Decimal("2")
        return (price * quantity * spread_bps / Decimal("10000")).quantize(Decimal("0.00000001"))

    def _get_pip_value(self, symbol):
        """Get pip value for symbol."""
        if "JPY" in symbol.upper():
            return Decimal("0.01")
        return Decimal("0.0001")

    def _get_positions_dict(self, state) -> dict:
        """Build positions dict for strategy state sync."""
        positions = {}
        for pos in state.open_positions:
            if pos.symbol not in positions:
                positions[pos.symbol] = []
            positions[pos.symbol].append({
                "side": pos.side,
                "qty": float(pos.quantity),
                "entry_price": float(pos.entry_price),
                "entry_time": pos.entry_time,
                "unrealized_pnl": 0,  # Updated on next bar
            })
        return positions

    def _apply_overrides(self, strategy: Strategy, overrides: dict | None):
        """Apply parameter overrides to a strategy instance."""
        if not overrides:
            return
        declared_params = strategy.get_parameters()
        for key, value in overrides.items():
            if not hasattr(strategy, key):
                raise ValueError(f"Unknown parameter: {key}")
            param_def = declared_params.get(key, {})
            if param_def.get("min") is not None and value < param_def["min"]:
                raise ValueError(f"Parameter {key} below minimum {param_def['min']}")
            if param_def.get("max") is not None and value > param_def["max"]:
                raise ValueError(f"Parameter {key} above maximum {param_def['max']}")
            setattr(strategy, key, value)

    async def _load_bars(self, db, symbols, timeframe, start_date, end_date, warmup_bars):
        """Load historical bars from DB (same as condition runner)."""
        from app.market_data.models import OHLCVBar
        from sqlalchemy import select

        result = {}
        for symbol in symbols:
            warmup_query = (
                select(OHLCVBar)
                .where(OHLCVBar.symbol == symbol, OHLCVBar.timeframe == timeframe, OHLCVBar.ts < start_date)
                .order_by(OHLCVBar.ts.desc())
                .limit(warmup_bars)
            )
            warmup_result = await db.execute(warmup_query)
            warmup = list(reversed(warmup_result.scalars().all()))

            period_query = (
                select(OHLCVBar)
                .where(OHLCVBar.symbol == symbol, OHLCVBar.timeframe == timeframe,
                       OHLCVBar.ts >= start_date, OHLCVBar.ts <= end_date)
                .order_by(OHLCVBar.ts.asc())
            )
            period_result = await db.execute(period_query)
            period = list(period_result.scalars().all())

            result[symbol] = warmup + period
        return result

    def _bars_to_dicts(self, bars) -> list[dict]:
        """Convert OHLCVBar objects to dict format."""
        return [{"open": b.open, "high": b.high, "low": b.low, "close": b.close,
                 "volume": b.volume, "timestamp": b.ts} for b in bars]

    async def _store_results(self, db, backtest_run, state, metrics):
        """Store trades and equity curve to database."""
        from app.backtesting.models import BacktestTrade, BacktestEquityPoint

        for trade in state.closed_trades:
            db.add(BacktestTrade(
                backtest_id=backtest_run.id, symbol=trade.symbol, side=trade.side,
                quantity=trade.quantity, entry_time=trade.entry_time, entry_price=trade.entry_price,
                entry_bar_index=trade.entry_bar_index, exit_time=trade.exit_time,
                exit_price=trade.exit_price, exit_bar_index=trade.exit_bar_index,
                exit_reason=trade.exit_reason, pnl=trade.pnl, pnl_percent=trade.pnl_percent,
                fees=trade.fees, hold_bars=trade.hold_bars,
                max_favorable=trade.max_favorable, max_adverse=trade.max_adverse,
            ))

        for point in state.equity_points:
            db.add(BacktestEquityPoint(
                backtest_id=backtest_run.id, bar_time=point.bar_time, bar_index=point.bar_index,
                equity=point.equity, cash=point.cash, open_positions=point.open_positions,
                unrealized_pnl=point.unrealized_pnl, drawdown_pct=point.drawdown_pct,
            ))

        backtest_run.metrics = metrics
        backtest_run.bars_processed = state.bars_processed
        backtest_run.total_trades = len(state.closed_trades)
        await db.flush()
