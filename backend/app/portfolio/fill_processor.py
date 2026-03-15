"""Fill processor — turns paper trading fills into position updates."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import Position
from app.portfolio.repository import CashBalanceRepository, PositionRepository

logger = logging.getLogger(__name__)

_position_repo = PositionRepository()
_cash_repo = CashBalanceRepository()


class FillProcessor:
    """Processes fills from the paper trading engine into position updates.

    Handles all four scenarios: entry, scale-in, scale-out, full exit.
    """

    async def process_fill(
        self, db: AsyncSession, fill: object, order: object, user_id: UUID
    ) -> Position:
        """Process a fill and update/create position.

        Runs within the same transaction as the fill creation (atomic).
        """
        existing = await _position_repo.get_open_by_strategy_symbol(
            db, order.strategy_id, order.symbol
        )

        scenario = self._determine_scenario(existing, order)

        if scenario == "entry":
            position = await self._process_entry(db, fill, order, user_id)
        elif scenario == "scale_in":
            position = await self._process_scale_in(db, existing, fill, order)
        elif scenario == "scale_out":
            position = await self._process_scale_out(db, existing, fill, order)
        else:
            position = await self._process_full_exit(db, existing, fill, order)

        await self._adjust_cash(db, user_id, fill, order)

        logger.info(
            "Fill processed: %s %s %s qty=%s scenario=%s (position=%s)",
            order.side, order.symbol, order.signal_type,
            fill.qty, scenario, position.id,
        )

        # Take event snapshot after fill processing
        try:
            from app.portfolio.startup import get_snapshot_manager
            snapshot_mgr = get_snapshot_manager()
            if snapshot_mgr:
                await snapshot_mgr.take_snapshot(db, user_id, "event")
        except Exception as e:
            logger.debug("Event snapshot skipped: %s", e)

        return position

    async def _process_entry(
        self, db: AsyncSession, fill: object, order: object, user_id: UUID
    ) -> Position:
        """No existing position. Create new position."""
        multiplier = Decimal(str(order.contract_multiplier))
        market_value = fill.qty * fill.price * multiplier

        position = Position(
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            market=order.market,
            side="long" if order.side == "buy" else "short",
            qty=fill.qty,
            avg_entry_price=fill.price,
            cost_basis=fill.net_value,
            current_price=fill.price,
            market_value=market_value,
            unrealized_pnl=Decimal("0"),
            unrealized_pnl_percent=Decimal("0"),
            realized_pnl=Decimal("0"),
            total_fees=fill.fee,
            total_dividends_received=Decimal("0"),
            total_return=Decimal("0"),
            total_return_percent=Decimal("0"),
            status="open",
            opened_at=fill.filled_at,
            highest_price_since_entry=fill.price,
            lowest_price_since_entry=fill.price,
            bars_held=0,
            broker_account_id=getattr(fill, "broker_account_id", None),
            underlying_symbol=getattr(order, "underlying_symbol", None),
            contract_type=getattr(order, "contract_type", None),
            strike_price=getattr(order, "strike_price", None),
            expiration_date=getattr(order, "expiration_date", None),
            contract_multiplier=order.contract_multiplier,
            user_id=user_id,
        )
        return await _position_repo.create(db, position)

    async def _process_scale_in(
        self, db: AsyncSession, position: Position, fill: object, order: object
    ) -> Position:
        """Existing position, same direction. Increase size."""
        old_qty = position.qty
        new_qty = old_qty + fill.qty

        # Weighted average entry price
        position.avg_entry_price = (
            (old_qty * position.avg_entry_price) + (fill.qty * fill.price)
        ) / new_qty

        position.qty = new_qty
        position.cost_basis = position.cost_basis + fill.net_value
        position.total_fees = position.total_fees + fill.fee

        # Update market value
        multiplier = Decimal(str(position.contract_multiplier))
        position.market_value = new_qty * position.current_price * multiplier

        # Recalculate unrealized PnL
        self._update_unrealized_pnl(position)

        return await _position_repo.update(db, position)

    async def _process_scale_out(
        self, db: AsyncSession, position: Position, fill: object, order: object
    ) -> Position:
        """Existing position, partial close. Reduce size."""
        multiplier = Decimal(str(position.contract_multiplier))

        # Calculate realized PnL on closed portion
        if position.side == "long":
            gross_pnl = (fill.price - position.avg_entry_price) * fill.qty * multiplier
        else:
            gross_pnl = (position.avg_entry_price - fill.price) * fill.qty * multiplier

        net_pnl = gross_pnl - fill.fee

        # Adjust position
        old_qty = position.qty
        remaining_qty = old_qty - fill.qty

        # Cost basis adjusted proportionally
        position.cost_basis = position.cost_basis * (remaining_qty / old_qty)

        position.qty = remaining_qty
        position.realized_pnl = position.realized_pnl + net_pnl
        position.total_fees = position.total_fees + fill.fee

        # Update market value
        position.market_value = remaining_qty * position.current_price * multiplier

        # Recalculate unrealized PnL and total return
        self._update_unrealized_pnl(position)
        position.total_return = (
            position.unrealized_pnl + position.realized_pnl + position.total_dividends_received
        )
        if position.cost_basis > 0:
            position.total_return_percent = position.total_return / position.cost_basis * 100
        else:
            position.total_return_percent = Decimal("0")

        # Record PnL ledger entry for scale-out
        try:
            from app.portfolio.startup import get_pnl_ledger
            pnl_ledger = get_pnl_ledger()
            if pnl_ledger:
                await pnl_ledger.record_close(
                    db, position, fill, fill.price,
                    fill.qty, gross_pnl, fill.fee, net_pnl,
                )
        except Exception as e:
            logger.debug("PnL ledger entry skipped (scale-out): %s", e)

        return await _position_repo.update(db, position)

    async def _process_full_exit(
        self, db: AsyncSession, position: Position, fill: object, order: object
    ) -> Position:
        """Close entire position."""
        multiplier = Decimal(str(position.contract_multiplier))
        qty_closed = position.qty  # Capture before zeroing

        # Calculate realized PnL on full position
        if position.side == "long":
            gross_pnl = (fill.price - position.avg_entry_price) * position.qty * multiplier
        else:
            gross_pnl = (position.avg_entry_price - fill.price) * position.qty * multiplier

        net_pnl = gross_pnl - fill.fee

        position.realized_pnl = position.realized_pnl + net_pnl
        position.total_fees = position.total_fees + fill.fee
        position.qty = Decimal("0")
        position.market_value = Decimal("0")
        position.unrealized_pnl = Decimal("0")
        position.unrealized_pnl_percent = Decimal("0")
        position.status = "closed"
        position.closed_at = fill.filled_at
        position.current_price = fill.price

        # Get close reason from signal's exit_reason via order
        close_reason = None
        try:
            from app.signals.models import Signal
            from sqlalchemy import select
            result = await db.execute(
                select(Signal.exit_reason).where(Signal.id == order.signal_id)
            )
            close_reason = result.scalar_one_or_none()
        except Exception:
            pass
        position.close_reason = close_reason

        position.total_return = (
            position.realized_pnl + position.total_dividends_received
        )
        if position.cost_basis > 0:
            position.total_return_percent = position.total_return / position.cost_basis * 100
        else:
            position.total_return_percent = Decimal("0")

        # Record PnL ledger entry for full exit
        try:
            from app.portfolio.startup import get_pnl_ledger
            pnl_ledger = get_pnl_ledger()
            if pnl_ledger:
                await pnl_ledger.record_close(
                    db, position, fill, fill.price,
                    qty_closed, gross_pnl, fill.fee, net_pnl,
                )
        except Exception as e:
            logger.debug("PnL ledger entry skipped (full exit): %s", e)

        return await _position_repo.update(db, position)

    async def _adjust_cash(
        self, db: AsyncSession, user_id: UUID, fill: object, order: object
    ) -> None:
        """Adjust cash balance based on fill."""
        # Determine account scope
        broker_account_id = getattr(fill, "broker_account_id", None)
        if broker_account_id and order.market == "forex":
            account_scope = broker_account_id
        else:
            account_scope = "equities"

        # Buys debit cash, sells credit cash
        if order.side == "buy":
            delta = -fill.net_value
        else:
            delta = fill.net_value

        await _cash_repo.update_balance(db, account_scope, user_id, delta)

    def _determine_scenario(
        self, position: Position | None, order: object
    ) -> str:
        """Determine which fill scenario applies."""
        if position is None:
            return "entry"

        # Same direction → scale in
        pos_buy_side = position.side == "long"
        order_buy_side = order.side == "buy"

        if pos_buy_side == order_buy_side:
            return "scale_in"

        # Opposite direction → check qty
        # For simplicity, use requested_qty from order
        order_qty = getattr(order, "filled_qty", None) or getattr(order, "requested_qty", Decimal("0"))
        if order_qty >= position.qty:
            return "full_exit"
        return "scale_out"

    def _update_unrealized_pnl(self, position: Position) -> None:
        """Update unrealized PnL fields on a position."""
        multiplier = Decimal(str(position.contract_multiplier))
        if position.side == "long":
            position.unrealized_pnl = (
                (position.current_price - position.avg_entry_price)
                * position.qty * multiplier
            )
        else:
            position.unrealized_pnl = (
                (position.avg_entry_price - position.current_price)
                * position.qty * multiplier
            )

        if position.avg_entry_price > 0:
            if position.side == "long":
                position.unrealized_pnl_percent = (
                    (position.current_price - position.avg_entry_price)
                    / position.avg_entry_price * 100
                )
            else:
                position.unrealized_pnl_percent = (
                    (position.avg_entry_price - position.current_price)
                    / position.avg_entry_price * 100
                )
        else:
            position.unrealized_pnl_percent = Decimal("0")
