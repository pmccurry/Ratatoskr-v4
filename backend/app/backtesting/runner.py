"""Backtest engine — replays historical bars through strategy conditions."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.state import BacktestState, BacktestTradeRecord
from app.backtesting.sizing import calculate_position_size
from app.backtesting.metrics import compute_metrics

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Core backtest engine that walks bars chronologically."""

    async def run(self, backtest_run, db: AsyncSession) -> dict:
        """
        Execute a backtest synchronously within the request.

        Returns metrics dict.
        """
        from app.strategies.validation import normalize_config_keys

        config = normalize_config_keys(backtest_run.strategy_config)

        # Initialize condition engine (reuse strategy module's engine)
        from app.strategies.indicators import get_registry
        from app.strategies.formulas.parser import FormulaParser
        from app.strategies.conditions.engine import ConditionEngine

        registry = get_registry()
        formula_parser = FormulaParser(registry)
        condition_engine = ConditionEngine(registry, formula_parser)

        # Calculate warmup period
        warmup_bars = self._calculate_warmup_bars(config)

        # Load bars from database
        all_bars = await self._load_bars(
            db, backtest_run.symbols, backtest_run.timeframe,
            backtest_run.start_date, backtest_run.end_date,
            warmup_bars
        )

        if not all_bars:
            return {"total_trades": 0, "note": "No bars found", "bars_processed": 0}

        # Initialize state
        state = BacktestState(
            initial_capital=Decimal(str(backtest_run.initial_capital)),
            position_sizing=backtest_run.position_sizing,
            exit_config=backtest_run.exit_config or {},
            timeframe=backtest_run.timeframe,
        )

        # Determine entry side from config
        entry_side = config.get("entry_side", "buy")
        signal_side = "long" if entry_side == "buy" else "short"

        # Walk through bars per symbol
        for symbol in backtest_run.symbols:
            symbol_bars = all_bars.get(symbol, [])
            if not symbol_bars:
                continue

            # Convert to dict format for condition engine
            bar_dicts = self._bars_to_dicts(symbol_bars)

            for bar_index in range(len(bar_dicts)):
                current_bar = bar_dicts[bar_index]
                # Slice: all bars up to and including current
                bars_window = bar_dicts[:bar_index + 1]

                # Mark warmup complete after warmup period
                if bar_index >= warmup_bars and not state.warmup_complete:
                    state.warmup_complete = True

                # Check exits first (before entries)
                self._check_exits(state, current_bar, bar_index, symbol)

                # Evaluate entry conditions (only after warmup)
                if state.warmup_complete:
                    # Check entry conditions
                    entry_conditions = config.get("entry_conditions")
                    if entry_conditions and condition_engine.evaluate(entry_conditions, bars_window):
                        self._process_entry(state, symbol, signal_side, current_bar, bar_index)

                    # Check condition-based exits
                    exit_conditions = config.get("exit_conditions")
                    if exit_conditions:
                        for pos in state.open_positions[:]:
                            if pos.symbol == symbol and condition_engine.evaluate(exit_conditions, bars_window):
                                self._close_position(state, pos, current_bar["close"], current_bar, bar_index, "signal")

                # Update excursion for open positions
                for pos in state.open_positions:
                    if pos.symbol == symbol:
                        pos.update_excursion(current_bar)

                # Record equity
                state.record_equity(current_bar, bar_index)

        # Close remaining positions at end of data
        if all_bars:
            # Get last bar from first symbol that has bars
            for sym_bars in all_bars.values():
                if sym_bars:
                    last_bar_dicts = self._bars_to_dicts(sym_bars)
                    last_bar = last_bar_dicts[-1]
                    last_idx = len(last_bar_dicts) - 1
                    for pos in state.open_positions[:]:
                        self._close_position(state, pos, last_bar["close"], last_bar, last_idx, "end_of_data")
                    break

        # Compute metrics
        metrics = compute_metrics(state)

        # Store results
        await self._store_results(db, backtest_run, state, metrics)

        return metrics

    def _calculate_warmup_bars(self, strategy_config: dict) -> int:
        """Find maximum lookback needed by any indicator.

        Scans the strategy config for period-like integer parameters
        and returns the largest value plus a buffer.
        """
        max_period = self._find_max_period(strategy_config)

        # Add 20% buffer + 10
        return int(max_period * 1.2) + 10

    def _find_max_period(self, obj) -> int:
        """Recursively find the largest integer parameter in config."""
        max_val = 0
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key in ("period", "fast", "slow", "signal", "k_period", "d_period",
                          "slowing", "atr_period", "lookback_bars"):
                    if isinstance(val, int):
                        max_val = max(max_val, val)
                else:
                    max_val = max(max_val, self._find_max_period(val))
        elif isinstance(obj, list):
            for item in obj:
                max_val = max(max_val, self._find_max_period(item))
        return max_val

    async def _load_bars(self, db, symbols, timeframe, start_date, end_date, warmup_bars):
        """Load historical bars from DB, including warmup period."""
        from app.market_data.models import OHLCVBar
        from sqlalchemy import select

        result = {}
        for symbol in symbols:
            # First get warmup bars (before start_date)
            warmup_query = (
                select(OHLCVBar)
                .where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.timeframe == timeframe,
                    OHLCVBar.ts < start_date,
                )
                .order_by(OHLCVBar.ts.desc())
                .limit(warmup_bars)
            )
            warmup_result = await db.execute(warmup_query)
            warmup = list(reversed(warmup_result.scalars().all()))

            # Then get test period bars
            period_query = (
                select(OHLCVBar)
                .where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.timeframe == timeframe,
                    OHLCVBar.ts >= start_date,
                    OHLCVBar.ts <= end_date,
                )
                .order_by(OHLCVBar.ts.asc())
            )
            period_result = await db.execute(period_query)
            period = list(period_result.scalars().all())

            result[symbol] = warmup + period

        return result

    def _bars_to_dicts(self, bars) -> list[dict]:
        """Convert OHLCVBar objects to dict format for condition engine."""
        return [
            {
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "timestamp": b.ts,
            }
            for b in bars
        ]

    def _check_exits(self, state, bar, bar_index, symbol):
        """Check SL/TP/time exits for open positions."""
        exit_config = state.exit_config

        for pos in state.open_positions[:]:
            if pos.symbol != symbol:
                continue

            # Stop loss
            sl_pips = exit_config.get("stop_loss_pips")
            if sl_pips:
                pip_val = self._get_pip_value(symbol)
                if pos.side == "long":
                    sl_price = pos.entry_price - Decimal(str(sl_pips)) * pip_val
                    if bar["low"] <= sl_price:
                        self._close_position(state, pos, sl_price, bar, bar_index, "stop_loss")
                        continue
                else:
                    sl_price = pos.entry_price + Decimal(str(sl_pips)) * pip_val
                    if bar["high"] >= sl_price:
                        self._close_position(state, pos, sl_price, bar, bar_index, "stop_loss")
                        continue

            # Take profit
            tp_pips = exit_config.get("take_profit_pips")
            if tp_pips:
                pip_val = self._get_pip_value(symbol)
                if pos.side == "long":
                    tp_price = pos.entry_price + Decimal(str(tp_pips)) * pip_val
                    if bar["high"] >= tp_price:
                        self._close_position(state, pos, tp_price, bar, bar_index, "take_profit")
                        continue
                else:
                    tp_price = pos.entry_price - Decimal(str(tp_pips)) * pip_val
                    if bar["low"] <= tp_price:
                        self._close_position(state, pos, tp_price, bar, bar_index, "take_profit")
                        continue

            # Time-based exit
            max_hold = exit_config.get("max_hold_bars")
            if max_hold and (bar_index - pos.entry_bar_index) >= max_hold:
                self._close_position(state, pos, bar["close"], bar, bar_index, "time_exit")
                continue

    def _process_entry(self, state, symbol, side, bar, bar_index):
        """Process an entry signal."""
        exit_config = state.exit_config

        # Signal-based exit: close opposite positions first
        if exit_config.get("signal_exit"):
            opposite = "short" if side == "long" else "long"
            for pos in state.open_positions[:]:
                if pos.symbol == symbol and pos.side == opposite:
                    self._close_position(state, pos, bar["close"], bar, bar_index, "signal")

        # Don't open if already have same-direction position
        if any(p.symbol == symbol and p.side == side for p in state.open_positions):
            return

        # Calculate size
        equity = state.get_current_equity(bar)
        quantity = calculate_position_size(state.position_sizing, equity, bar["close"], symbol)
        if quantity <= 0:
            return

        # Check if enough cash
        cost = bar["close"] * quantity
        if cost > state.cash:
            return

        # Simulate fill
        fill_price = self._simulate_fill(side, bar, symbol)
        fees = self._calculate_fees(fill_price, quantity)

        # Open position
        trade = BacktestTradeRecord(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_time=bar["timestamp"],
            entry_price=fill_price,
            entry_bar_index=bar_index,
            fees=fees,
        )
        state.open_positions.append(trade)

        # Deduct cash
        if side == "long":
            state.cash -= (fill_price * quantity) + fees
        else:
            # Short: receive cash but set aside margin (simplified: same deduction)
            state.cash -= fees  # simplified short handling

        state._trade_occurred = True

    def _close_position(self, state, pos, exit_price, bar, bar_index, reason):
        """Close a position and record PnL."""
        pos.exit_time = bar["timestamp"]
        pos.exit_price = exit_price
        pos.exit_bar_index = bar_index
        pos.exit_reason = reason
        pos.hold_bars = bar_index - pos.entry_bar_index

        # Calculate PnL
        if pos.side == "long":
            pos.pnl = (exit_price - pos.entry_price) * pos.quantity
        else:
            pos.pnl = (pos.entry_price - exit_price) * pos.quantity

        cost = pos.entry_price * pos.quantity
        if cost > 0:
            pos.pnl_percent = (pos.pnl / cost * Decimal("100")).quantize(Decimal("0.01"))

        # Return cash
        if pos.side == "long":
            state.cash += exit_price * pos.quantity
        else:
            state.cash += pos.entry_price * pos.quantity + pos.pnl

        # Move from open to closed
        if pos in state.open_positions:
            state.open_positions.remove(pos)
        state.closed_trades.append(pos)
        state._trade_occurred = True

    def _simulate_fill(self, side, bar, symbol):
        """Simulate entry fill price with slippage."""
        price = bar["close"]
        pip_val = self._get_pip_value(symbol)
        slippage = Decimal("0.5") * pip_val  # 0.5 pips

        if side == "long":
            return price + slippage
        else:
            return price - slippage

    def _calculate_fees(self, price, quantity):
        """Calculate trading fees (spread cost)."""
        spread_bps = Decimal("2")  # 2 basis points
        return (price * quantity * spread_bps / Decimal("10000")).quantize(Decimal("0.00000001"))

    def _get_pip_value(self, symbol):
        """Get pip value for symbol."""
        if "JPY" in symbol.upper():
            return Decimal("0.01")
        return Decimal("0.0001")

    async def _store_results(self, db, backtest_run, state, metrics):
        """Store trades and equity curve to database."""
        from app.backtesting.models import BacktestTrade, BacktestEquityPoint

        # Store trades
        for trade in state.closed_trades:
            db_trade = BacktestTrade(
                backtest_id=backtest_run.id,
                symbol=trade.symbol,
                side=trade.side,
                quantity=trade.quantity,
                entry_time=trade.entry_time,
                entry_price=trade.entry_price,
                entry_bar_index=trade.entry_bar_index,
                exit_time=trade.exit_time,
                exit_price=trade.exit_price,
                exit_bar_index=trade.exit_bar_index,
                exit_reason=trade.exit_reason,
                pnl=trade.pnl,
                pnl_percent=trade.pnl_percent,
                fees=trade.fees,
                hold_bars=trade.hold_bars,
                max_favorable=trade.max_favorable,
                max_adverse=trade.max_adverse,
            )
            db.add(db_trade)

        # Store equity curve
        for point in state.equity_points:
            db_point = BacktestEquityPoint(
                backtest_id=backtest_run.id,
                bar_time=point.bar_time,
                bar_index=point.bar_index,
                equity=point.equity,
                cash=point.cash,
                open_positions=point.open_positions,
                unrealized_pnl=point.unrealized_pnl,
                drawdown_pct=point.drawdown_pct,
            )
            db.add(db_point)

        # Update run
        backtest_run.metrics = metrics
        backtest_run.bars_processed = state.bars_processed
        backtest_run.total_trades = len(state.closed_trades)

        await db.flush()
