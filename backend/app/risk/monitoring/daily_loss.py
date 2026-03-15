"""Daily loss monitoring — tracks realized losses per trading day."""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.risk.models import RiskConfig

logger = logging.getLogger(__name__)


class DailyLossMonitor:
    """Tracks daily realized losses.

    NOTE: Until TASK-013 provides real realized PnL data,
    daily loss is stubbed to zero.
    """

    async def get_daily_loss(self, db: AsyncSession, risk_config: RiskConfig,
                             portfolio_equity: Decimal) -> dict:
        """Return current daily loss state."""
        current_loss = await self._get_today_realized_loss(db)

        if risk_config.max_daily_loss_amount is not None:
            limit = risk_config.max_daily_loss_amount
        elif portfolio_equity > 0:
            limit = risk_config.max_daily_loss_percent / 100 * portfolio_equity
        else:
            limit = Decimal("0")

        if limit > 0:
            percent_used = current_loss / limit * 100
        else:
            percent_used = Decimal("0")

        threshold_status = "normal"
        if limit > 0:
            if current_loss >= limit:
                threshold_status = "breach"
            elif current_loss >= limit * Decimal("0.7"):
                threshold_status = "warning"

        # Emit audit event on daily loss breach
        if threshold_status == "breach":
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="risk.daily_loss.breach",
                        category="risk",
                        severity="error",
                        source_module="risk",
                        summary=f"🟠 Daily loss limit breached: ${current_loss}",
                        entity_type="daily_loss",
                        details={
                            "current_loss": str(current_loss),
                            "limit": str(limit),
                            "percent_used": str(percent_used),
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

        day_start, day_end = self._get_trading_day_boundaries("equities")

        return {
            "current_loss": current_loss,
            "limit": limit,
            "percent_used": percent_used,
            "threshold_status": threshold_status,
            "resets_at": day_end.isoformat(),
        }

    def _get_trading_day_boundaries(self, market: str) -> tuple[datetime, datetime]:
        """Get start/end of current trading day.

        Equities: midnight to midnight ET (UTC-5 / UTC-4)
        Forex: 5 PM ET to 5 PM ET
        """
        now = datetime.now(timezone.utc)
        # Approximate ET as UTC-5 for simplicity
        et_offset = timedelta(hours=-5)

        if market == "forex":
            # Forex day: 5 PM ET to 5 PM ET
            et_now = now + et_offset
            if et_now.hour >= 17:
                day_start_et = et_now.replace(hour=17, minute=0, second=0, microsecond=0)
                day_end_et = day_start_et + timedelta(days=1)
            else:
                day_end_et = et_now.replace(hour=17, minute=0, second=0, microsecond=0)
                day_start_et = day_end_et - timedelta(days=1)
        else:
            # Equities: midnight to midnight ET
            et_now = now + et_offset
            day_start_et = et_now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end_et = day_start_et + timedelta(days=1)

        # Convert back to UTC
        utc_offset = -et_offset
        return day_start_et + utc_offset, day_end_et + utc_offset

    async def _get_today_realized_loss(self, db: AsyncSession) -> Decimal:
        """Get total realized losses for today."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                from app.auth.models import User
                from sqlalchemy import select
                result = await db.execute(
                    select(User.id).where(User.role == "admin").limit(1)
                )
                user_id = result.scalar_one_or_none()
                if user_id:
                    return await portfolio_service.get_daily_realized_loss(db, user_id)
        except Exception:
            pass
        return Decimal("0")
