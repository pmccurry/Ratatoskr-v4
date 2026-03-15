"""Safety monitor — watches orphaned positions on a 1-minute cycle."""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.strategies.config import StrategyConfig
from app.strategies.models import Strategy
from app.strategies.repository import (
    PositionOverrideRepository,
    StrategyConfigRepository,
    StrategyRepository,
    StrategyStateRepository,
)

logger = logging.getLogger(__name__)

_strategy_repo = StrategyRepository()
_config_repo = StrategyConfigRepository()
_state_repo = StrategyStateRepository()
_override_repo = PositionOverrideRepository()


class SafetyMonitor:
    """Monitors orphaned positions (strategy paused/disabled/errored).

    Evaluates ONLY price-based exit rules:
    - Stop loss vs current price
    - Take profit vs current price
    - Trailing stop vs current price

    Does NOT evaluate indicator-based exit conditions.
    Runs every 1 minute regardless of strategy timeframe.
    """

    def __init__(self, config: StrategyConfig):
        self._config = config
        self._running = False
        self._task: asyncio.Task | None = None
        self._consecutive_failures = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Safety monitor started (interval=%ds)",
            self._config.safety_monitor_check_interval,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Safety monitor stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                from app.common.database import get_session_factory

                factory = get_session_factory()
                async with factory() as db:
                    try:
                        await self.run_check(db)
                        await db.commit()
                        self._consecutive_failures = 0
                    except Exception:
                        await db.rollback()
                        raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                await self._handle_failure(e)

            try:
                await asyncio.sleep(self._config.safety_monitor_check_interval)
            except asyncio.CancelledError:
                break

    async def run_check(self, db: AsyncSession) -> dict:
        from sqlalchemy import select, or_
        from app.strategies.models import Strategy

        result = await db.execute(
            select(Strategy).where(
                or_(
                    Strategy.status == "paused",
                    Strategy.status == "disabled",
                )
            )
        )
        strategies = list(result.scalars().all())

        strategies_checked = len(strategies)
        positions_checked = 0
        exits_triggered = 0

        for strategy in strategies:
            try:
                active_config = await _config_repo.get_active(db, strategy.id)
                if not active_config:
                    continue

                from app.strategies.validation import normalize_config_keys
                config_json = normalize_config_keys(active_config.config_json)

                # Query portfolio for open positions belonging to this strategy
                positions: list[dict] = []
                try:
                    from app.portfolio.startup import get_portfolio_service
                    portfolio_service = get_portfolio_service()
                    if portfolio_service:
                        open_positions = await portfolio_service.get_open_positions(
                            db, strategy.id
                        )
                        positions = [
                            {
                                "id": str(p.id),
                                "symbol": p.symbol,
                                "side": p.side,
                                "qty": p.qty,
                                "avg_entry_price": p.avg_entry_price,
                                "current_price": p.current_price,
                                "unrealized_pnl": p.unrealized_pnl,
                                "highest_price_since_entry": p.highest_price_since_entry,
                                "lowest_price_since_entry": p.lowest_price_since_entry,
                                "bars_held": p.bars_held,
                            }
                            for p in open_positions
                        ]
                except Exception:
                    pass

                for position in positions:
                    positions_checked += 1
                    symbol = position.get("symbol", "")

                    from app.market_data.service import MarketDataService
                    md_service = MarketDataService()
                    current_price = await md_service.get_latest_close(db, symbol)

                    if current_price is None:
                        logger.warning(
                            "Safety monitor: no price for %s (strategy %s)",
                            symbol, strategy.key,
                        )
                        continue

                    # Check position overrides first
                    position_id = position.get("id")
                    overrides = []
                    if position_id:
                        overrides = await _override_repo.get_active_for_position(
                            db, position_id
                        )

                    override_config = self._apply_overrides(config_json, overrides)

                    state = await _state_repo.get_or_create(db, strategy.id)
                    state_json = state.state_json or {}

                    exit_triggered = False

                    exit_reason = None

                    if self._check_stop_loss(position, override_config, current_price):
                        exit_reason = "stop_loss"

                    if not exit_reason and self._check_take_profit(
                        position, override_config, current_price
                    ):
                        exit_reason = "take_profit"

                    if not exit_reason and self._check_trailing_stop(
                        position, override_config, state_json, current_price
                    ):
                        exit_reason = "trailing_stop"

                    if exit_reason:
                        exit_triggered = True
                        exits_triggered += 1
                        await self._emit_safety_signal(
                            db, strategy, symbol, position, exit_reason,
                        )
                        logger.info(
                            "Safety monitor: %s triggered for %s (strategy %s)",
                            exit_reason, symbol, strategy.key,
                        )

                        # Emit safety monitor exit event
                        try:
                            from app.observability.startup import get_event_emitter
                            emitter = get_event_emitter()
                            if emitter:
                                await emitter.emit(
                                    event_type="strategy.safety_monitor.exit",
                                    category="strategies",
                                    severity="info",
                                    source_module="strategies",
                                    summary=f"🛑 Safety monitor exit: {symbol} ({exit_reason})",
                                    entity_type="strategy",
                                    entity_id=strategy.id,
                                    strategy_id=strategy.id,
                                    symbol=symbol,
                                    details={"exit_reason": exit_reason, "strategy_key": strategy.key},
                                )
                        except Exception:
                            pass  # Event emission never disrupts trading pipeline

                    state.state_json = state_json
                    await _state_repo.update(db, state)

            except Exception as e:
                logger.error(
                    "Safety monitor error for strategy %s: %s", strategy.key, e
                )

        return {
            "strategies_checked": strategies_checked,
            "positions_checked": positions_checked,
            "exits_triggered": exits_triggered,
        }

    def _apply_overrides(self, config: dict, overrides: list) -> dict:
        override_config = dict(config)
        for ovr in overrides:
            if ovr.override_type == "stop_loss":
                override_config["stop_loss"] = ovr.override_value_json
            elif ovr.override_type == "take_profit":
                override_config["take_profit"] = ovr.override_value_json
            elif ovr.override_type == "trailing_stop":
                override_config["trailing_stop"] = ovr.override_value_json
        return override_config

    def _check_stop_loss(
        self, position: dict, config: dict, current_price: Decimal
    ) -> bool:
        stop_loss = config.get("stop_loss")
        if not stop_loss or not stop_loss.get("value"):
            return False

        avg_entry = Decimal(str(position.get("avg_entry", 0)))
        side = position.get("side", "long")
        sl_type = stop_loss.get("type", "percent")
        value = Decimal(str(stop_loss.get("value", 0)))

        if sl_type == "percent":
            if side == "long":
                stop_price = avg_entry * (1 - value / 100)
                return current_price <= stop_price
            stop_price = avg_entry * (1 + value / 100)
            return current_price >= stop_price
        if sl_type == "fixed":
            if side == "long":
                return current_price <= avg_entry - value
            return current_price >= avg_entry + value
        return False

    def _check_take_profit(
        self, position: dict, config: dict, current_price: Decimal
    ) -> bool:
        take_profit = config.get("take_profit")
        if not take_profit or not take_profit.get("value"):
            return False

        avg_entry = Decimal(str(position.get("avg_entry", 0)))
        side = position.get("side", "long")
        tp_type = take_profit.get("type", "percent")
        value = Decimal(str(take_profit.get("value", 0)))

        if tp_type == "percent":
            if side == "long":
                target = avg_entry * (1 + value / 100)
                return current_price >= target
            target = avg_entry * (1 - value / 100)
            return current_price <= target
        if tp_type == "fixed":
            if side == "long":
                return current_price >= avg_entry + value
            return current_price <= avg_entry - value
        return False

    def _check_trailing_stop(
        self, position: dict, config: dict, state: dict, current_price: Decimal
    ) -> bool:
        trailing = config.get("trailing_stop")
        if not trailing or not trailing.get("enabled"):
            return False

        symbol = position.get("symbol", "")
        side = position.get("side", "long")
        sym_key = f"trailing_{symbol}"

        highest = Decimal(str(state.get(sym_key, str(current_price))))
        trail_value = Decimal(str(trailing.get("value", 0)))

        if side == "long":
            if current_price > highest:
                highest = current_price
                state[sym_key] = str(highest)

            if trailing.get("type") == "percent":
                trail_price = highest * (1 - trail_value / 100)
            else:
                trail_price = highest - trail_value

            return current_price <= trail_price
        else:
            if current_price < highest:
                highest = current_price
                state[sym_key] = str(highest)

            if trailing.get("type") == "percent":
                trail_price = highest * (1 + trail_value / 100)
            else:
                trail_price = highest + trail_value

            return current_price >= trail_price

    async def _emit_safety_signal(
        self,
        db: AsyncSession,
        strategy: Strategy,
        symbol: str,
        position: dict,
        exit_reason: str,
    ) -> None:
        """Create an exit signal with source='safety' via the signals module."""
        from datetime import datetime, timezone

        from app.signals.startup import get_signal_service

        now = datetime.now(timezone.utc)
        signal_service = get_signal_service()
        side = position.get("side", "long")

        signal_data = {
            "strategy_id": strategy.id,
            "strategy_version": strategy.current_version,
            "symbol": symbol,
            "market": strategy.market,
            "timeframe": "1m",
            "side": "sell" if side == "long" else "buy",
            "signal_type": "exit",
            "source": "safety",
            "ts": now,
            "exit_reason": exit_reason,
            "position_id": position.get("id"),
            "payload_json": {"reason": exit_reason, "monitor": "safety"},
        }
        result = await signal_service.create_signal(db, signal_data)
        if not result:
            logger.warning(
                "Safety monitor: failed to create signal for %s (strategy %s)",
                symbol, strategy.key,
            )

    async def _handle_failure(self, error: Exception) -> None:
        self._consecutive_failures += 1
        logger.critical(
            "Safety monitor failure (%d consecutive): %s",
            self._consecutive_failures, error,
        )

        if self._consecutive_failures >= self._config.safety_monitor_failure_alert_threshold:
            # TODO: Trigger alert via observability module (notification channels)
            logger.critical(
                "Safety monitor has failed %d times. Alert threshold reached.",
                self._consecutive_failures,
            )

        if self._config.global_kill_switch:
            # TODO: Create kill switch signal to close all positions
            logger.critical("Global kill switch is enabled — would close all positions")
