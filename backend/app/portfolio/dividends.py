"""Dividend processing — ex-date eligibility and payable-date cash credits."""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import DividendPayment, Position
from app.portfolio.repository import CashBalanceRepository

logger = logging.getLogger(__name__)

_cash_repo = CashBalanceRepository()


class DividendProcessor:
    """Processes dividend payments for held positions."""

    async def process_ex_date(
        self, db: AsyncSession, user_id: UUID
    ) -> list[DividendPayment]:
        """Check for ex-dates today and create pending dividend payments."""
        from app.market_data.models import DividendAnnouncement

        today = date.today()

        # Get announcements with ex_date = today
        result = await db.execute(
            select(DividendAnnouncement).where(
                DividendAnnouncement.ex_date == today
            )
        )
        announcements = list(result.scalars().all())

        payments = []
        for announcement in announcements:
            # Find open positions in this symbol for the user
            pos_result = await db.execute(
                select(Position).where(
                    Position.user_id == user_id,
                    Position.symbol == announcement.symbol,
                    Position.status == "open",
                )
            )
            positions = list(pos_result.scalars().all())

            for position in positions:
                # Check if payment already exists
                existing = await db.execute(
                    select(func.count()).select_from(DividendPayment).where(
                        DividendPayment.position_id == position.id,
                        DividendPayment.announcement_id == announcement.id,
                    )
                )
                if existing.scalar_one() > 0:
                    continue

                gross_amount = position.qty * announcement.cash_amount
                payment = DividendPayment(
                    position_id=position.id,
                    announcement_id=announcement.id,
                    user_id=user_id,
                    symbol=announcement.symbol,
                    ex_date=announcement.ex_date,
                    payable_date=announcement.payable_date,
                    shares_held=position.qty,
                    amount_per_share=announcement.cash_amount,
                    gross_amount=gross_amount,
                    net_amount=gross_amount,  # Same as gross for MVP
                    status="pending",
                )
                db.add(payment)
                payments.append(payment)

        if payments:
            await db.flush()
            logger.info("Created %d pending dividend payments", len(payments))

        return payments

    async def process_payable_date(
        self, db: AsyncSession, user_id: UUID
    ) -> list[DividendPayment]:
        """Process pending dividends where payable_date <= today."""
        today = date.today()

        result = await db.execute(
            select(DividendPayment).where(
                DividendPayment.user_id == user_id,
                DividendPayment.status == "pending",
                DividendPayment.payable_date <= today,
            )
        )
        payments = list(result.scalars().all())

        processed = []
        for payment in payments:
            # Credit cash to equities account (dividends are equity-market)
            await _cash_repo.update_balance(
                db, "equities", user_id, payment.net_amount
            )

            # Update position total_dividends_received
            pos_result = await db.execute(
                select(Position).where(Position.id == payment.position_id)
            )
            position = pos_result.scalar_one_or_none()
            if position:
                position.total_dividends_received = (
                    position.total_dividends_received + payment.net_amount
                )

            payment.status = "paid"
            payment.paid_at = datetime.now(timezone.utc)
            processed.append(payment)

            # Emit audit event for dividend paid
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="portfolio.dividend.paid",
                        category="portfolio",
                        severity="info",
                        source_module="portfolio",
                        summary=f"💵 Dividend paid: ${payment.net_amount} for {payment.symbol}",
                        entity_type="position",
                        entity_id=payment.position_id,
                        symbol=payment.symbol,
                        details={
                            "amount_per_share": str(payment.amount_per_share),
                            "shares_held": str(payment.shares_held),
                            "gross_amount": str(payment.gross_amount),
                            "net_amount": str(payment.net_amount),
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

        if processed:
            await db.flush()
            logger.info("Processed %d dividend payments", len(processed))

        return processed

    async def get_upcoming(
        self, db: AsyncSession, user_id: UUID
    ) -> list[dict]:
        """Get upcoming dividends for positions the user holds."""
        from app.market_data.models import DividendAnnouncement

        today = date.today()

        # Get user's open position symbols
        pos_result = await db.execute(
            select(Position.symbol).where(
                Position.user_id == user_id,
                Position.status == "open",
            ).distinct()
        )
        symbols = [row[0] for row in pos_result.all()]
        if not symbols:
            return []

        # Get upcoming announcements
        ann_result = await db.execute(
            select(DividendAnnouncement).where(
                DividendAnnouncement.symbol.in_(symbols),
                DividendAnnouncement.ex_date >= today,
            ).order_by(DividendAnnouncement.ex_date.asc())
        )
        announcements = list(ann_result.scalars().all())

        upcoming = []
        for ann in announcements:
            # Get position qty for this symbol
            qty_result = await db.execute(
                select(func.coalesce(func.sum(Position.qty), Decimal("0")))
                .where(
                    Position.user_id == user_id,
                    Position.symbol == ann.symbol,
                    Position.status == "open",
                )
            )
            total_qty = qty_result.scalar_one()

            upcoming.append({
                "symbol": ann.symbol,
                "ex_date": ann.ex_date,
                "payable_date": ann.payable_date,
                "amount_per_share": ann.cash_amount,
                "shares_held": total_qty,
                "estimated_amount": total_qty * ann.cash_amount,
            })

        return upcoming

    async def get_payment_history(
        self,
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DividendPayment], int]:
        """Query dividend payment history."""
        query = select(DividendPayment).where(
            DividendPayment.user_id == user_id
        )
        count_query = select(func.count()).select_from(DividendPayment).where(
            DividendPayment.user_id == user_id
        )

        query = query.order_by(DividendPayment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        payments = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return payments, total

    async def get_income_summary(
        self, db: AsyncSession, user_id: UUID
    ) -> dict:
        """Dividend income summary."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now.hour < 5:
            today_start -= timedelta(days=1)
        month_start = now.replace(day=1, hour=5, minute=0, second=0, microsecond=0)
        year_start = now.replace(
            month=1, day=1, hour=5, minute=0, second=0, microsecond=0
        )

        base = [
            DividendPayment.user_id == user_id,
            DividendPayment.status == "paid",
        ]

        async def _sum_after(after: datetime) -> Decimal:
            result = await db.execute(
                select(
                    func.coalesce(
                        func.sum(DividendPayment.net_amount), Decimal("0")
                    )
                ).where(*base, DividendPayment.paid_at >= after)
            )
            return result.scalar_one()

        today = await _sum_after(today_start)
        this_month = await _sum_after(month_start)
        this_year = await _sum_after(year_start)

        total_result = await db.execute(
            select(
                func.coalesce(
                    func.sum(DividendPayment.net_amount), Decimal("0")
                )
            ).where(*base)
        )
        total = total_result.scalar_one()

        # By symbol
        by_symbol_result = await db.execute(
            select(
                DividendPayment.symbol,
                func.sum(DividendPayment.net_amount),
            )
            .where(*base)
            .group_by(DividendPayment.symbol)
        )
        by_symbol = {
            row[0]: row[1] for row in by_symbol_result.all()
        }

        return {
            "today": today,
            "this_month": this_month,
            "this_year": this_year,
            "total": total,
            "by_symbol": by_symbol,
        }
