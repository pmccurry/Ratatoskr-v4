"""Strategy runner — evaluates enabled strategies on schedule."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.strategies.conditions.engine import ConditionEngine
from app.strategies.config import StrategyConfig
from app.strategies.models import Strategy, StrategyConfigVersion, StrategyEvaluation
from app.strategies.repository import (
    StrategyConfigRepository,
    StrategyEvaluationRepository,
    StrategyRepository,
    StrategyStateRepository,
)

logger = logging.getLogger(__name__)

_strategy_repo = StrategyRepository()
_config_repo = StrategyConfigRepository()
_state_repo = StrategyStateRepository()
_eval_repo = StrategyEvaluationRepository()


class StrategyRunner:
    """Runs strategy evaluations on schedule.

    Called periodically (every runner_check_interval). Checks which strategies
    need evaluation based on their timeframe, then evaluates each one.
    """

    def __init__(self, config: StrategyConfig, condition_engine: ConditionEngine):
        self._config = config
        self._engine = condition_engine
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Strategy runner started (interval=%ds)", self._config.runner_check_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Strategy runner stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                from app.common.database import get_session_factory

                factory = get_session_factory()
                async with factory() as db:
                    try:
                        await self.run_evaluation_cycle(db)
                        await db.commit()
                    except Exception:
                        await db.rollback()
                        raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Strategy runner cycle error: %s", e)

            try:
                await asyncio.sleep(self._config.runner_check_interval)
            except asyncio.CancelledError:
                break

    async def run_evaluation_cycle(self, db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)
        strategies = await _strategy_repo.get_enabled(db)

        evaluated = 0
        total_signals = 0
        total_errors = 0

        due_strategies = []
        for strategy in strategies:
            active_config = await _config_repo.get_active(db, strategy.id)
            if not active_config:
                continue
            config_json = active_config.config_json
            if self._is_due(strategy, config_json, now):
                due_strategies.append((strategy, active_config))

        if not due_strategies:
            return {"evaluated": 0, "signals": 0, "errors": 0}

        tasks = [
            self.evaluate_strategy(db, s, c)
            for s, c in due_strategies
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (strategy, _config), result in zip(due_strategies, results):
            if isinstance(result, Exception):
                logger.error(
                    "Strategy %s evaluation error: %s", strategy.key, result
                )
                strategy.auto_pause_error_count += 1
                total_errors += 1

                if strategy.auto_pause_error_count >= self._config.auto_pause_error_threshold:
                    await self._handle_auto_pause(db, strategy)

                    # Emit auto-paused event
                    try:
                        from app.observability.startup import get_event_emitter
                        emitter = get_event_emitter()
                        if emitter:
                            await emitter.emit(
                                event_type="strategy.auto_paused",
                                category="strategies",
                                severity="error",
                                source_module="strategies",
                                summary=f"🟠 {strategy.name} auto-paused: {self._config.auto_pause_error_threshold} errors",
                                entity_type="strategy",
                                entity_id=strategy.id,
                                strategy_id=strategy.id,
                                details={"error_count": self._config.auto_pause_error_threshold},
                            )
                    except Exception:
                        pass  # Event emission never disrupts trading pipeline
                else:
                    await _strategy_repo.update(db, strategy)

                eval_record = StrategyEvaluation(
                    strategy_id=strategy.id,
                    strategy_version=strategy.current_version,
                    evaluated_at=now,
                    status="error",
                    duration_ms=0,
                    errors=1,
                    details_json={"error": str(result)},
                )
                await _eval_repo.create(db, eval_record)
                # Emit evaluation error event
                try:
                    from app.observability.startup import get_event_emitter
                    emitter = get_event_emitter()
                    if emitter:
                        await emitter.emit(
                            event_type="strategy.evaluation.error",
                            category="strategies",
                            severity="error",
                            source_module="strategies",
                            summary=f"🟠 {strategy.name} evaluation error: {result}",
                            entity_type="strategy",
                            entity_id=strategy.id,
                            strategy_id=strategy.id,
                            details={"error": str(result)},
                        )
                except Exception:
                    pass  # Event emission never disrupts trading pipeline
            else:
                evaluated += 1
                total_signals += result.get("signals_emitted", 0)
                strategy.auto_pause_error_count = 0
                strategy.last_evaluated_at = now
                await _strategy_repo.update(db, strategy)

        return {"evaluated": evaluated, "signals": total_signals, "errors": total_errors}

    def _is_due(self, strategy: Strategy, config: dict, now: datetime) -> bool:
        timeframe = config.get("timeframe", "1m")
        minute = now.minute
        hour = now.hour

        if timeframe == "1m":
            return True
        if timeframe == "5m":
            return minute % 5 == 0
        if timeframe == "15m":
            return minute % 15 == 0
        if timeframe == "1h":
            return minute == 0
        if timeframe == "4h":
            return hour % 4 == 0 and minute == 0
        return False

    def _is_market_open(self, market: str, trading_hours: dict, now: datetime) -> bool:
        mode = trading_hours.get("mode", "regular")

        if market == "forex":
            weekday = now.weekday()
            if weekday == 5:
                return False
            if weekday == 6:
                return now.hour >= 22
            if weekday == 4:
                return now.hour < 22
            return True

        if market in ("equities", "both"):
            weekday = now.weekday()
            if weekday >= 5:
                return False
            utc_hour = now.hour
            if mode == "regular":
                return 13 <= utc_hour < 21
            if mode == "extended":
                return 8 <= utc_hour < 24
            if mode == "custom":
                return True
        return True

    async def evaluate_strategy(
        self, db: AsyncSession, strategy: Strategy, active_config: StrategyConfigVersion
    ) -> dict:
        start_time = time.monotonic()
        config_json = active_config.config_json
        now = datetime.now(timezone.utc)

        trading_hours = config_json.get("trading_hours", {"mode": "regular"})
        if not self._is_market_open(strategy.market, trading_hours, now):
            eval_record = StrategyEvaluation(
                strategy_id=strategy.id,
                strategy_version=strategy.current_version,
                evaluated_at=now,
                status="skipped",
                skip_reason="market_closed",
                duration_ms=0,
            )
            await _eval_repo.create(db, eval_record)

            # Emit evaluation skipped event
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="strategy.evaluation.skipped",
                        category="strategies",
                        severity="info",
                        source_module="strategies",
                        summary=f"📊 {strategy.name} skipped: market closed",
                        entity_type="strategy",
                        entity_id=strategy.id,
                        strategy_id=strategy.id,
                        details={"reason": "market_closed"},
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

            return {"status": "skipped", "skip_reason": "market_closed"}

        symbols = await self._resolve_symbols(db, config_json)
        if not symbols:
            eval_record = StrategyEvaluation(
                strategy_id=strategy.id,
                strategy_version=strategy.current_version,
                evaluated_at=now,
                status="skipped",
                skip_reason="no_symbols",
                duration_ms=0,
            )
            await _eval_repo.create(db, eval_record)

            # Emit evaluation skipped event
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="strategy.evaluation.skipped",
                        category="strategies",
                        severity="info",
                        source_module="strategies",
                        summary=f"📊 {strategy.name} skipped: no symbols",
                        entity_type="strategy",
                        entity_id=strategy.id,
                        strategy_id=strategy.id,
                        details={"reason": "no_symbols"},
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

            return {"status": "skipped", "skip_reason": "no_symbols"}

        timeframe = config_json.get("timeframe", "1m")
        lookback = config_json.get("lookback_bars", 200)

        from app.market_data.service import MarketDataService
        md_service = MarketDataService()

        state = await _state_repo.get_or_create(db, strategy.id)
        state_json = state.state_json or {}

        signals_emitted = 0
        exits_triggered = 0
        errors = 0
        details: dict = {}

        for symbol in symbols:
            try:
                bars = await md_service.get_bars(db, symbol, timeframe, limit=lookback)
                bar_dicts = [
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

                if not bar_dicts:
                    details[symbol] = {"status": "no_data"}
                    continue

                # Query portfolio for open position
                position = None
                try:
                    from app.portfolio.startup import get_portfolio_service
                    portfolio_service = get_portfolio_service()
                    if portfolio_service:
                        pos = await portfolio_service.get_open_position_for_symbol(
                            db, strategy.id, symbol
                        )
                        if pos:
                            position = {
                                "id": str(pos.id),
                                "symbol": pos.symbol,
                                "side": pos.side,
                                "qty": pos.qty,
                                "avg_entry_price": pos.avg_entry_price,
                                "current_price": pos.current_price,
                                "unrealized_pnl": pos.unrealized_pnl,
                                "highest_price_since_entry": pos.highest_price_since_entry,
                                "lowest_price_since_entry": pos.lowest_price_since_entry,
                                "bars_held": pos.bars_held,
                            }
                except Exception:
                    pass

                if position is None:
                    signal_intent = await self._evaluate_entry(
                        config_json, bar_dicts, strategy.id, strategy.current_version, symbol
                    )
                    if signal_intent:
                        signal = await self._emit_signal(
                            db, strategy, config_json, signal_intent, now
                        )
                        if signal:
                            signals_emitted += 1
                            details[symbol] = {"status": "entry_signal", "signal_id": str(signal.id)}
                        else:
                            details[symbol] = {"status": "entry_signal_rejected"}
                    else:
                        details[symbol] = {"status": "no_signal"}
                else:
                    signal_intent = await self._evaluate_exit(
                        config_json, bar_dicts, position, state_json, symbol,
                        strategy.id, strategy.current_version,
                    )
                    if signal_intent:
                        signal = await self._emit_signal(
                            db, strategy, config_json, signal_intent, now
                        )
                        if signal:
                            exits_triggered += 1
                            details[symbol] = {"status": "exit_signal", "signal_id": str(signal.id)}
                        else:
                            details[symbol] = {"status": "exit_signal_rejected"}
                    else:
                        details[symbol] = {"status": "position_held"}
            except Exception as e:
                errors += 1
                details[symbol] = {"status": "error", "error": str(e)}
                logger.error("Strategy %s symbol %s error: %s", strategy.key, symbol, e)

        # Step 7b: Evaluate shadow position exits
        try:
            from app.paper_trading.shadow.evaluator import ShadowEvaluator
            from app.paper_trading.startup import get_paper_trading_service
            service = get_paper_trading_service()
            if hasattr(service, '_shadow_tracker') and service._shadow_tracker:
                shadow_evaluator = ShadowEvaluator(service._shadow_tracker)
                shadow_exits = await shadow_evaluator.evaluate_shadow_positions(
                    db, strategy.id, config_json
                )
                if shadow_exits:
                    logger.info(
                        "Strategy %s: %d shadow exits triggered",
                        strategy.key, len(shadow_exits),
                    )
        except Exception as e:
            logger.debug("Shadow evaluation skipped: %s", e)

        state.state_json = state_json
        await _state_repo.update(db, state)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        if errors > 0 and errors == len(symbols):
            eval_status = "error"
        elif errors > 0:
            eval_status = "partial_success"
        else:
            eval_status = "success"

        eval_record = StrategyEvaluation(
            strategy_id=strategy.id,
            strategy_version=strategy.current_version,
            evaluated_at=now,
            symbols_evaluated=len(symbols),
            signals_emitted=signals_emitted,
            exits_triggered=exits_triggered,
            errors=errors,
            duration_ms=duration_ms,
            status=eval_status,
            details_json=details,
        )
        await _eval_repo.create(db, eval_record)

        # Emit evaluation completed event
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="strategy.evaluation.completed",
                    category="strategies",
                    severity="info",
                    source_module="strategies",
                    summary=f"📊 {strategy.name}: {len(symbols)} symbols, {signals_emitted} signals",
                    entity_type="strategy",
                    entity_id=strategy.id,
                    strategy_id=strategy.id,
                    details={
                        "symbols_evaluated": len(symbols),
                        "signals_emitted": signals_emitted,
                        "exits_triggered": exits_triggered,
                        "errors": errors,
                        "duration_ms": duration_ms,
                        "status": eval_status,
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return {
            "status": eval_status,
            "symbols_evaluated": len(symbols),
            "signals_emitted": signals_emitted,
            "exits_triggered": exits_triggered,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def _resolve_symbols(self, db: AsyncSession, config: dict) -> list[str]:
        symbols_config = config.get("symbols", {})

        # Handle list format (frontend sends plain list)
        if isinstance(symbols_config, list):
            return symbols_config

        mode = symbols_config.get("mode", "explicit")

        if mode == "explicit":
            return symbols_config.get("list", [])

        if mode in ("watchlist", "filtered"):
            from app.market_data.service import MarketDataService
            md_service = MarketDataService()
            market = config.get("market")
            entries = await md_service.get_watchlist(db, market=market)
            symbol_list = [e.symbol for e in entries]

            if mode == "filtered":
                filters = symbols_config.get("filters", {})
                min_volume = filters.get("min_volume")
                min_price = filters.get("min_price")
                # Basic filtering — full filter is done at watchlist level
                if min_volume or min_price:
                    logger.debug("Filtered mode with filters: %s", filters)

            return symbol_list

        return []

    async def _evaluate_entry(
        self, config: dict, bars: list[dict],
        strategy_id: UUID, strategy_version: str, symbol: str,
    ) -> dict | None:
        entry_conditions = config.get("entry_conditions")
        if not entry_conditions:
            return None

        result = self._engine.evaluate(entry_conditions, bars)
        if not result:
            return None

        side = config.get("entry_side", "buy")
        return {
            "symbol": symbol,
            "side": side,
            "type": "entry",
            "reason": "conditions_met",
            "strategy_id": str(strategy_id),
            "strategy_version": strategy_version,
        }

    async def _evaluate_exit(
        self, config: dict, bars: list[dict],
        position: dict | None, state: dict, symbol: str,
        strategy_id: UUID, strategy_version: str,
    ) -> dict | None:
        if position is None:
            return None

        current_close = bars[-1]["close"] if bars else None
        if current_close is None:
            return None

        current_close = Decimal(str(current_close))
        avg_entry = Decimal(str(position.get("avg_entry", 0)))
        side = position.get("side", "long")

        # 1. Condition-based exit
        exit_conditions = config.get("exit_conditions")
        if exit_conditions:
            if self._engine.evaluate(exit_conditions, bars):
                return {
                    "symbol": symbol,
                    "side": "sell" if side == "long" else "buy",
                    "type": "exit",
                    "reason": "exit_conditions_met",
                    "strategy_id": str(strategy_id),
                    "strategy_version": strategy_version,
                }

        # 2. Stop loss
        stop_loss = config.get("stop_loss")
        if stop_loss and stop_loss.get("value"):
            stop_price = self._compute_stop_price(stop_loss, avg_entry, side, bars)
            if stop_price is not None:
                if (side == "long" and current_close <= stop_price) or \
                   (side == "short" and current_close >= stop_price):
                    return {
                        "symbol": symbol,
                        "side": "sell" if side == "long" else "buy",
                        "type": "exit",
                        "reason": "stop_loss",
                        "strategy_id": str(strategy_id),
                        "strategy_version": strategy_version,
                    }

        # 3. Take profit
        take_profit = config.get("take_profit")
        if take_profit and take_profit.get("value"):
            target = self._compute_take_profit(take_profit, avg_entry, stop_loss, side, bars)
            if target is not None:
                if (side == "long" and current_close >= target) or \
                   (side == "short" and current_close <= target):
                    return {
                        "symbol": symbol,
                        "side": "sell" if side == "long" else "buy",
                        "type": "exit",
                        "reason": "take_profit",
                        "strategy_id": str(strategy_id),
                        "strategy_version": strategy_version,
                    }

        # 4. Trailing stop
        trailing = config.get("trailing_stop")
        if trailing and trailing.get("enabled"):
            sym_key = f"trailing_{symbol}"
            highest = state.get(sym_key, str(current_close))
            highest = Decimal(str(highest))

            if side == "long":
                if current_close > highest:
                    highest = current_close
                    state[sym_key] = str(highest)

                trail_value = Decimal(str(trailing.get("value", 0)))
                if trailing.get("type") == "percent":
                    trail_price = highest * (1 - trail_value / 100)
                else:
                    trail_price = highest - trail_value

                if current_close <= trail_price:
                    return {
                        "symbol": symbol,
                        "side": "sell",
                        "type": "exit",
                        "reason": "trailing_stop",
                        "strategy_id": str(strategy_id),
                        "strategy_version": strategy_version,
                    }
            else:
                if current_close < highest:
                    highest = current_close
                    state[sym_key] = str(highest)

                trail_value = Decimal(str(trailing.get("value", 0)))
                if trailing.get("type") == "percent":
                    trail_price = highest * (1 + trail_value / 100)
                else:
                    trail_price = highest + trail_value

                if current_close >= trail_price:
                    return {
                        "symbol": symbol,
                        "side": "buy",
                        "type": "exit",
                        "reason": "trailing_stop",
                        "strategy_id": str(strategy_id),
                        "strategy_version": strategy_version,
                    }

        # 5. Max hold bars
        max_hold = config.get("max_hold_bars")
        if max_hold is not None:
            bars_held = position.get("bars_held", 0)
            if bars_held >= max_hold:
                return {
                    "symbol": symbol,
                    "side": "sell" if side == "long" else "buy",
                    "type": "exit",
                    "reason": "max_hold",
                    "strategy_id": str(strategy_id),
                    "strategy_version": strategy_version,
                }

        return None

    def _compute_stop_price(
        self, stop_loss: dict, avg_entry: Decimal, side: str, bars: list[dict]
    ) -> Decimal | None:
        sl_type = stop_loss.get("type", "percent")
        value = Decimal(str(stop_loss.get("value", 0)))

        if sl_type == "percent":
            if side == "long":
                return avg_entry * (1 - value / 100)
            return avg_entry * (1 + value / 100)
        if sl_type == "fixed":
            if side == "long":
                return avg_entry - value
            return avg_entry + value
        if sl_type == "atr_multiple":
            from app.strategies.indicators.compute import compute_atr
            atr = compute_atr(bars)
            if atr is None:
                return None
            if side == "long":
                return avg_entry - (atr * value)
            return avg_entry + (atr * value)
        return None

    def _compute_take_profit(
        self, take_profit: dict, avg_entry: Decimal,
        stop_loss: dict | None, side: str, bars: list[dict]
    ) -> Decimal | None:
        tp_type = take_profit.get("type", "percent")
        value = Decimal(str(take_profit.get("value", 0)))

        if tp_type == "percent":
            if side == "long":
                return avg_entry * (1 + value / 100)
            return avg_entry * (1 - value / 100)
        if tp_type == "fixed":
            if side == "long":
                return avg_entry + value
            return avg_entry - value
        if tp_type == "atr_multiple":
            from app.strategies.indicators.compute import compute_atr
            atr = compute_atr(bars)
            if atr is None:
                return None
            if side == "long":
                return avg_entry + (atr * value)
            return avg_entry - (atr * value)
        if tp_type == "risk_multiple":
            if stop_loss:
                stop_price = self._compute_stop_price(stop_loss, avg_entry, side, bars)
                if stop_price is not None:
                    risk = abs(avg_entry - stop_price)
                    if side == "long":
                        return avg_entry + (risk * value)
                    return avg_entry - (risk * value)
            return None
        return None

    async def _emit_signal(
        self,
        db: AsyncSession,
        strategy: Strategy,
        config: dict,
        intent: dict,
        now: datetime,
    ):
        """Create a signal via the signals module. Returns the Signal or None."""
        from app.signals.startup import get_signal_service

        signal_service = get_signal_service()
        signal_data = {
            "strategy_id": strategy.id,
            "strategy_version": strategy.current_version,
            "symbol": intent["symbol"],
            "market": strategy.market,
            "timeframe": config.get("timeframe", "1m"),
            "side": intent["side"],
            "signal_type": intent["type"],
            "source": "strategy",
            "ts": now,
            "payload_json": {"reason": intent.get("reason")},
        }
        position_id = intent.get("position_id")
        if position_id:
            signal_data["position_id"] = position_id
        exit_reason = intent.get("reason")
        if intent["type"] == "exit" and exit_reason:
            signal_data["exit_reason"] = exit_reason

        return await signal_service.create_signal(db, signal_data)

    async def _handle_auto_pause(self, db: AsyncSession, strategy: Strategy) -> None:
        strategy.status = "paused"
        strategy.auto_pause_error_count = 0
        await _strategy_repo.update(db, strategy)
        logger.warning(
            "Strategy %s auto-paused after %d consecutive errors",
            strategy.key, self._config.auto_pause_error_threshold,
        )
        # TODO: Trigger alert via observability module
