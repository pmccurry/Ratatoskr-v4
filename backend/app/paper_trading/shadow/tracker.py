"""Shadow tracker — creates and manages shadow fills and positions."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.config import PaperTradingConfig
from app.paper_trading.fill_simulation.engine import FillSimulationEngine
from app.paper_trading.models import ShadowFill, ShadowPosition
from app.paper_trading.shadow.repository import (
    ShadowFillRepository,
    ShadowPositionRepository,
)

logger = logging.getLogger(__name__)


class ShadowTracker:
    """Creates and manages shadow fills and positions for contention-blocked signals.

    Activated ONLY when:
    - SHADOW_TRACKING_ENABLED = true
    - Signal was blocked with reason_code = "no_available_account"
    - SHADOW_TRACKING_FOREX_ONLY = true (only forex)
    """

    def __init__(
        self,
        fill_engine: FillSimulationEngine,
        config: PaperTradingConfig,
    ):
        self._fill_engine = fill_engine
        self._config = config
        self._position_repo = ShadowPositionRepository()
        self._fill_repo = ShadowFillRepository()

    async def create_shadow_entry(
        self,
        db: AsyncSession,
        signal: object,
        order: object,
        reference_price: Decimal,
    ) -> ShadowPosition:
        """Create a shadow fill and position for a blocked entry signal."""
        now = datetime.now(timezone.utc)

        # Simulate fill using same engine
        fill_result = await self._fill_engine.simulate(order, reference_price)

        # Get strategy config for SL/TP/trailing
        stop_loss_price = None
        take_profit_price = None
        trailing_stop_price = None

        try:
            from app.strategies.repository import StrategyConfigRepository
            config_repo = StrategyConfigRepository()
            active_config = await config_repo.get_active(db, signal.strategy_id)
            if active_config:
                exit_rules = active_config.config_json.get("exit_rules", {})

                # Stop loss
                sl = exit_rules.get("stop_loss", {})
                if sl.get("enabled"):
                    sl_pct = Decimal(str(sl.get("percent", "0")))
                    if sl_pct > 0:
                        if signal.side == "buy":
                            stop_loss_price = fill_result.price * (1 - sl_pct / 100)
                        else:
                            stop_loss_price = fill_result.price * (1 + sl_pct / 100)

                # Take profit
                tp = exit_rules.get("take_profit", {})
                if tp.get("enabled"):
                    tp_pct = Decimal(str(tp.get("percent", "0")))
                    if tp_pct > 0:
                        if signal.side == "buy":
                            take_profit_price = fill_result.price * (1 + tp_pct / 100)
                        else:
                            take_profit_price = fill_result.price * (1 - tp_pct / 100)

                # Trailing stop
                ts = exit_rules.get("trailing_stop", {})
                if ts.get("enabled"):
                    ts_pct = Decimal(str(ts.get("percent", "0")))
                    if ts_pct > 0:
                        if signal.side == "buy":
                            trailing_stop_price = fill_result.price * (1 - ts_pct / 100)
                        else:
                            trailing_stop_price = fill_result.price * (1 + ts_pct / 100)
        except Exception:
            pass

        # Create shadow position
        position = ShadowPosition(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side="long" if signal.side == "buy" else "short",
            qty=fill_result.qty,
            avg_entry_price=fill_result.price,
            current_price=fill_result.price,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            status="open",
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trailing_stop_price=trailing_stop_price,
            highest_price_since_entry=fill_result.price,
            opened_at=now,
            entry_signal_id=signal.id,
        )
        position = await self._position_repo.create(db, position)

        # Create shadow fill
        shadow_fill = ShadowFill(
            signal_id=signal.id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=signal.side,
            qty=fill_result.qty,
            reference_price=fill_result.reference_price,
            price=fill_result.price,
            fee=fill_result.fee,
            slippage_bps=fill_result.slippage_bps,
            gross_value=fill_result.gross_value,
            net_value=fill_result.net_value,
            fill_type="entry",
            shadow_position_id=position.id,
            filled_at=now,
        )
        await self._fill_repo.create(db, shadow_fill)

        logger.info(
            "Shadow entry created: %s %s qty=%s price=%s (position=%s)",
            signal.side, signal.symbol, fill_result.qty, fill_result.price, position.id,
        )

        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="paper_trading.shadow.fill_created",
                    category="trading",
                    severity="info",
                    source_module="paper_trading",
                    summary=f"👻 Shadow fill: {signal.side} {signal.symbol} ({signal.strategy_id})",
                    entity_type="shadow_fill",
                    entity_id=shadow_fill.id,
                    strategy_id=signal.strategy_id,
                    symbol=signal.symbol,
                    details={
                        "position_id": str(position.id),
                        "qty": str(fill_result.qty),
                        "price": str(fill_result.price),
                        "side": signal.side,
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return position

    async def close_shadow_position(
        self,
        db: AsyncSession,
        position: ShadowPosition,
        exit_price: Decimal,
        close_reason: str,
    ) -> ShadowPosition:
        """Close a shadow position with an exit fill."""
        now = datetime.now(timezone.utc)

        # Calculate realized PnL
        if position.side == "long":
            gross_pnl = (exit_price - position.avg_entry_price) * position.qty
        else:
            gross_pnl = (position.avg_entry_price - exit_price) * position.qty

        # Apply exit fee using same model as real fills
        from app.paper_trading.fill_simulation.fees import FeeModel
        gross_value_for_fee = exit_price * position.qty
        fee = FeeModel().calculate(gross_value_for_fee, "forex", self._config)

        net_pnl = gross_pnl - fee

        # Create exit fill
        exit_side = "sell" if position.side == "long" else "buy"
        gross_value = exit_price * position.qty
        shadow_fill = ShadowFill(
            signal_id=position.entry_signal_id,
            strategy_id=position.strategy_id,
            symbol=position.symbol,
            side=exit_side,
            qty=position.qty,
            reference_price=exit_price,
            price=exit_price,
            fee=fee,
            slippage_bps=Decimal("0"),
            gross_value=gross_value,
            net_value=gross_value - fee if exit_side == "sell" else gross_value + fee,
            fill_type="exit",
            shadow_position_id=position.id,
            filled_at=now,
        )
        await self._fill_repo.create(db, shadow_fill)

        # Update position
        position.realized_pnl = net_pnl
        position.unrealized_pnl = Decimal("0")
        position.current_price = exit_price
        position.status = "closed"
        position.closed_at = now
        position.close_reason = close_reason
        await self._position_repo.update(db, position)

        logger.info(
            "Shadow position closed: %s %s pnl=%s reason=%s",
            position.symbol, position.side, net_pnl, close_reason,
        )

        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="paper_trading.shadow.position_closed",
                    category="trading",
                    severity="info",
                    source_module="paper_trading",
                    summary=f"👻 Shadow position closed: {position.symbol} PnL ${net_pnl}",
                    entity_type="shadow_position",
                    entity_id=position.id,
                    strategy_id=position.strategy_id,
                    symbol=position.symbol,
                    details={
                        "pnl": str(net_pnl),
                        "close_reason": close_reason,
                        "exit_price": str(exit_price),
                        "side": position.side,
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return position

    def should_track(self, signal: object, rejection_reason: str) -> bool:
        """Check if shadow tracking should activate."""
        from app.common.config import get_settings
        settings = get_settings()

        if not settings.shadow_tracking_enabled:
            return False

        if rejection_reason != "no_available_account":
            return False

        if settings.shadow_tracking_forex_only:
            market = getattr(signal, "market", "equities")
            if market != "forex":
                return False

        return True
