"""Stock split processing — adjusts positions for forward and reverse splits."""

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import Position, SplitAdjustment

logger = logging.getLogger(__name__)


class SplitProcessor:
    """Adjusts positions for stock splits."""

    async def process_splits(
        self, db: AsyncSession, user_id: UUID
    ) -> list[SplitAdjustment]:
        """Check for splits effective today and adjust positions."""
        from app.market_data.models import DividendAnnouncement

        today = date.today()

        # Query for split corporate actions effective today
        # Splits are stored as DividendAnnouncement with ca_type containing 'split'
        result = await db.execute(
            select(DividendAnnouncement).where(
                DividendAnnouncement.ex_date == today,
                DividendAnnouncement.ca_type.in_(
                    ["forward_split", "reverse_split"]
                ),
            )
        )
        split_actions = list(result.scalars().all())

        adjustments = []
        for action in split_actions:
            # Find open positions for this symbol
            pos_result = await db.execute(
                select(Position).where(
                    Position.user_id == user_id,
                    Position.symbol == action.symbol,
                    Position.status == "open",
                )
            )
            positions = list(pos_result.scalars().all())
            if not positions:
                continue

            # Determine split ratio
            if action.ca_type == "forward_split" and action.stock_rate:
                # Forward: stock_rate is the multiplier (e.g., 4.0 for 4:1)
                old_rate = 1
                new_rate = int(action.stock_rate)
                split_type = "forward"
            elif action.ca_type == "reverse_split" and action.stock_rate:
                # Reverse: stock_rate is the divisor (e.g., 0.1 for 1:10)
                old_rate = int(Decimal("1") / action.stock_rate)
                new_rate = 1
                split_type = "reverse"
            else:
                continue

            ratio = Decimal(str(new_rate)) / Decimal(str(old_rate))
            per_position_details = []

            for position in positions:
                before = {
                    "position_id": str(position.id),
                    "qty": str(position.qty),
                    "avg_entry_price": str(position.avg_entry_price),
                    "highest_price": str(position.highest_price_since_entry),
                    "lowest_price": str(position.lowest_price_since_entry),
                }

                # Adjust qty and price
                position.qty = position.qty * ratio
                position.avg_entry_price = position.avg_entry_price / ratio
                position.highest_price_since_entry = (
                    position.highest_price_since_entry / ratio
                )
                position.lowest_price_since_entry = (
                    position.lowest_price_since_entry / ratio
                )
                position.current_price = position.current_price / ratio
                # Cost basis unchanged

                # Update market value
                multiplier = Decimal(str(position.contract_multiplier))
                position.market_value = (
                    position.qty * position.current_price * multiplier
                )

                after = {
                    "position_id": str(position.id),
                    "qty": str(position.qty),
                    "avg_entry_price": str(position.avg_entry_price),
                    "highest_price": str(position.highest_price_since_entry),
                    "lowest_price": str(position.lowest_price_since_entry),
                }
                per_position_details.append({"before": before, "after": after})

            adjustment = SplitAdjustment(
                symbol=action.symbol,
                split_type=split_type,
                old_rate=old_rate,
                new_rate=new_rate,
                effective_date=today,
                positions_adjusted=len(positions),
                adjustments_json=per_position_details,
            )
            db.add(adjustment)
            adjustments.append(adjustment)

            logger.info(
                "Split adjustment: %s %s %d:%d, %d positions adjusted",
                action.symbol, split_type, old_rate, new_rate, len(positions),
            )

            # Emit audit event for split adjustment
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="portfolio.split.adjusted",
                        category="portfolio",
                        severity="info",
                        source_module="portfolio",
                        summary=f"⚙️ Split adjusted: {action.symbol} {old_rate}:{new_rate} ({len(positions)} positions)",
                        entity_type="position",
                        entity_id=positions[0].id if positions else None,
                        symbol=action.symbol,
                        details={
                            "split_type": split_type,
                            "old_rate": old_rate,
                            "new_rate": new_rate,
                            "positions_adjusted": len(positions),
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

        if adjustments:
            await db.flush()

        return adjustments
