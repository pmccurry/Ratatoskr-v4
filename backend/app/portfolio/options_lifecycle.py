"""Options lifecycle — handles expiration of options positions."""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import Position

logger = logging.getLogger(__name__)


class OptionsLifecycle:
    """Handles options expiration."""

    async def check_expirations(
        self, db: AsyncSession, user_id: UUID
    ) -> list[dict]:
        """Check for expiring options positions at daily close."""
        today = date.today()

        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.status == "open",
                Position.expiration_date <= today,
                Position.contract_type.isnot(None),
            )
        )
        expiring = list(result.scalars().all())

        expired_positions = []
        for position in expiring:
            # Get underlying price
            underlying_price = await self._get_underlying_price(
                db, position.underlying_symbol or position.symbol
            )
            if underlying_price is None:
                logger.warning(
                    "Cannot get underlying price for %s, skipping expiration",
                    position.symbol,
                )
                continue

            # Calculate intrinsic value
            strike = position.strike_price or Decimal("0")
            if position.contract_type == "call":
                intrinsic = max(Decimal("0"), underlying_price - strike)
            elif position.contract_type == "put":
                intrinsic = max(Decimal("0"), strike - underlying_price)
            else:
                continue

            multiplier = Decimal(str(position.contract_multiplier))

            if intrinsic > 0:
                # ITM — close at intrinsic value
                close_value = intrinsic * position.qty * multiplier
                if position.side == "long":
                    realized_pnl = close_value - position.cost_basis
                else:
                    realized_pnl = position.cost_basis - close_value
            else:
                # OTM — expire worthless
                if position.side == "long":
                    realized_pnl = -position.cost_basis
                else:
                    realized_pnl = position.cost_basis

            now = datetime.now(timezone.utc)

            # Capture qty before zeroing (needed for PnL entry)
            qty_at_expiry = position.qty

            position.realized_pnl = position.realized_pnl + realized_pnl
            position.qty = Decimal("0")
            position.market_value = Decimal("0")
            position.unrealized_pnl = Decimal("0")
            position.unrealized_pnl_percent = Decimal("0")
            position.status = "closed"
            position.closed_at = now
            position.close_reason = "expiration"
            position.current_price = intrinsic

            position.total_return = (
                position.realized_pnl + position.total_dividends_received
            )
            if position.cost_basis > 0:
                position.total_return_percent = (
                    position.total_return / position.cost_basis * 100
                )

            # Create PnL entry
            try:
                from app.portfolio.startup import get_pnl_ledger
                pnl_ledger = get_pnl_ledger()
                if pnl_ledger:
                    from app.portfolio.models import RealizedPnlEntry
                    entry = RealizedPnlEntry(
                        position_id=position.id,
                        strategy_id=position.strategy_id,
                        user_id=position.user_id,
                        symbol=position.symbol,
                        market=position.market,
                        side=position.side,
                        qty_closed=qty_at_expiry,
                        entry_price=position.avg_entry_price,
                        exit_price=intrinsic,
                        gross_pnl=realized_pnl,
                        fees=Decimal("0"),
                        net_pnl=realized_pnl,
                        pnl_percent=(
                            realized_pnl / position.cost_basis * 100
                            if position.cost_basis > 0
                            else Decimal("0")
                        ),
                        holding_period_bars=position.bars_held,
                        closed_at=now,
                    )
                    db.add(entry)
            except Exception as e:
                logger.warning("Could not create PnL entry for expiration: %s", e)

            expired_positions.append({
                "position_id": str(position.id),
                "symbol": position.symbol,
                "contract_type": position.contract_type,
                "strike": str(strike),
                "intrinsic": str(intrinsic),
                "realized_pnl": str(realized_pnl),
                "status": "itm" if intrinsic > 0 else "otm",
            })

            logger.info(
                "Option expired: %s %s strike=%s intrinsic=%s pnl=%s",
                position.symbol, position.contract_type,
                strike, intrinsic, realized_pnl,
            )

            # Emit audit event for option expiration
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="portfolio.option.expired",
                        category="portfolio",
                        severity="info",
                        source_module="portfolio",
                        summary=f"📂 Option expired: {position.symbol} PnL ${realized_pnl}",
                        entity_type="position",
                        entity_id=position.id,
                        strategy_id=position.strategy_id,
                        symbol=position.symbol,
                        details={
                            "contract_type": position.contract_type,
                            "strike": str(strike),
                            "intrinsic": str(intrinsic),
                            "realized_pnl": str(realized_pnl),
                            "status": "itm" if intrinsic > 0 else "otm",
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

        if expired_positions:
            await db.flush()

        return expired_positions

    async def _get_underlying_price(
        self, db: AsyncSession, symbol: str
    ) -> Decimal | None:
        """Get latest price for the underlying symbol."""
        try:
            from app.market_data.models import OHLCVBar
            result = await db.execute(
                select(OHLCVBar.close)
                .where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.timeframe == "1m",
                )
                .order_by(OHLCVBar.ts.desc())
                .limit(1)
            )
            price = result.scalar_one_or_none()
            return price
        except Exception:
            return None
