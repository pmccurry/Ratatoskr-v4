"""Shadow position evaluator — evaluates exit conditions on shadow positions."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.shadow.repository import ShadowPositionRepository
from app.paper_trading.shadow.tracker import ShadowTracker

logger = logging.getLogger(__name__)


class ShadowEvaluator:
    """Evaluates exit conditions on open shadow positions.

    Uses the same price-based exit logic as the safety monitor:
    stop loss, take profit, trailing stop checks.
    """

    def __init__(self, tracker: ShadowTracker):
        self._tracker = tracker
        self._position_repo = ShadowPositionRepository()

    async def evaluate_shadow_positions(
        self, db: AsyncSession, strategy_id: UUID, config: dict
    ) -> list[dict]:
        """Evaluate all open shadow positions for a strategy."""
        positions = await self._position_repo.get_open_by_strategy(db, strategy_id)
        if not positions:
            return []

        results = []

        for position in positions:
            # Get current price
            current_price = await self._get_current_price(db, position.symbol)
            if current_price is None:
                continue

            # Update position tracking
            position.current_price = current_price

            # Update unrealized PnL
            if position.side == "long":
                position.unrealized_pnl = (
                    (current_price - position.avg_entry_price) * position.qty
                )
            else:
                position.unrealized_pnl = (
                    (position.avg_entry_price - current_price) * position.qty
                )

            # Update highest price
            if position.highest_price_since_entry is None or current_price > position.highest_price_since_entry:
                position.highest_price_since_entry = current_price

            # Check exit conditions
            close_reason = None

            # Stop loss
            if position.stop_loss_price is not None:
                if position.side == "long" and current_price <= position.stop_loss_price:
                    close_reason = "stop_loss"
                elif position.side == "short" and current_price >= position.stop_loss_price:
                    close_reason = "stop_loss"

            # Take profit
            if close_reason is None and position.take_profit_price is not None:
                if position.side == "long" and current_price >= position.take_profit_price:
                    close_reason = "take_profit"
                elif position.side == "short" and current_price <= position.take_profit_price:
                    close_reason = "take_profit"

            # Trailing stop
            if close_reason is None and position.trailing_stop_price is not None:
                # Update trailing stop based on highest price
                exit_rules = config.get("exit_rules", {})
                ts = exit_rules.get("trailing_stop", {})
                ts_pct = Decimal(str(ts.get("percent", "0")))

                if ts_pct > 0 and position.highest_price_since_entry is not None:
                    if position.side == "long":
                        new_trailing = position.highest_price_since_entry * (1 - ts_pct / 100)
                        if new_trailing > position.trailing_stop_price:
                            position.trailing_stop_price = new_trailing
                        if current_price <= position.trailing_stop_price:
                            close_reason = "trailing_stop"
                    else:
                        # For short, trailing stop moves down with lowest price
                        new_trailing = position.highest_price_since_entry * (1 + ts_pct / 100)
                        if new_trailing < position.trailing_stop_price:
                            position.trailing_stop_price = new_trailing
                        if current_price >= position.trailing_stop_price:
                            close_reason = "trailing_stop"

            if close_reason:
                closed = await self._tracker.close_shadow_position(
                    db, position, current_price, close_reason
                )
                results.append({
                    "position_id": str(closed.id),
                    "symbol": closed.symbol,
                    "side": closed.side,
                    "close_reason": close_reason,
                    "realized_pnl": str(closed.realized_pnl),
                })
            else:
                await self._position_repo.update(db, position)

        return results

    async def mark_to_market_shadows(self, db: AsyncSession) -> int:
        """Update all open shadow positions with current prices."""
        positions = await self._position_repo.get_all_open(db)
        updated = 0

        for position in positions:
            current_price = await self._get_current_price(db, position.symbol)
            if current_price is None:
                continue

            position.current_price = current_price
            if position.side == "long":
                position.unrealized_pnl = (
                    (current_price - position.avg_entry_price) * position.qty
                )
            else:
                position.unrealized_pnl = (
                    (position.avg_entry_price - current_price) * position.qty
                )

            if position.highest_price_since_entry is None or current_price > position.highest_price_since_entry:
                position.highest_price_since_entry = current_price

            updated += 1

        await db.flush()
        return updated

    async def _get_current_price(
        self, db: AsyncSession, symbol: str
    ) -> Decimal | None:
        """Get current price from market data."""
        try:
            from app.market_data.service import MarketDataService
            return await MarketDataService().get_latest_close(db, symbol, "1m")
        except Exception:
            return None
