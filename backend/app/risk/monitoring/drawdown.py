"""Drawdown monitoring — peak equity tracking and threshold status."""

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.risk.models import RiskConfig

logger = logging.getLogger(__name__)

# Initial paper trading cash (fallback)
_DEFAULT_INITIAL_EQUITY = Decimal("100000.00")


class DrawdownMonitor:
    """Tracks peak equity and calculates current drawdown.

    Peak equity is always read from the portfolio service (persisted in
    PortfolioMeta). No in-memory fallback — if the portfolio service is
    unavailable, drawdown status is reported as "degraded".
    """

    async def get_current_drawdown(self, db: AsyncSession, risk_config: RiskConfig) -> dict:
        """Return current drawdown state."""
        equity_available, current_equity = await self._get_current_equity(db)
        peak_available, peak = await self._get_peak_equity(db)

        if not equity_available or not peak_available:
            return {
                "peak_equity": peak,
                "current_equity": current_equity,
                "drawdown_percent": Decimal("0"),
                "threshold_status": "degraded",
                "max_drawdown_percent": risk_config.max_drawdown_percent,
                "catastrophic_percent": risk_config.max_drawdown_catastrophic_percent,
            }

        if peak <= 0:
            drawdown_pct = Decimal("0")
        else:
            drawdown_pct = (peak - current_equity) / peak * 100

        threshold_status = self._get_threshold_status(drawdown_pct, risk_config)

        # Emit audit events for non-normal drawdown thresholds
        if threshold_status != "normal" and threshold_status != "degraded":
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    if threshold_status == "warning":
                        await emitter.emit(
                            event_type="risk.drawdown.warning",
                            category="risk",
                            severity="warning",
                            source_module="risk",
                            summary=f"🟡 Drawdown at {drawdown_pct:.1f}% (limit: {risk_config.max_drawdown_percent}%)",
                            entity_type="drawdown",
                            details={
                                "drawdown_percent": str(drawdown_pct),
                                "peak_equity": str(peak),
                                "current_equity": str(current_equity),
                                "limit_percent": str(risk_config.max_drawdown_percent),
                            },
                        )
                    elif threshold_status == "breach":
                        await emitter.emit(
                            event_type="risk.drawdown.breach",
                            category="risk",
                            severity="error",
                            source_module="risk",
                            summary=f"🟠 Drawdown breach: {drawdown_pct:.1f}% exceeds {risk_config.max_drawdown_percent}%",
                            entity_type="drawdown",
                            details={
                                "drawdown_percent": str(drawdown_pct),
                                "peak_equity": str(peak),
                                "current_equity": str(current_equity),
                                "limit_percent": str(risk_config.max_drawdown_percent),
                            },
                        )
                    elif threshold_status == "catastrophic":
                        await emitter.emit(
                            event_type="risk.drawdown.catastrophic",
                            category="risk",
                            severity="critical",
                            source_module="risk",
                            summary=f"🔴 Catastrophic drawdown: {drawdown_pct:.1f}% — kill switch activated",
                            entity_type="drawdown",
                            details={
                                "drawdown_percent": str(drawdown_pct),
                                "peak_equity": str(peak),
                                "current_equity": str(current_equity),
                                "catastrophic_percent": str(risk_config.max_drawdown_catastrophic_percent),
                            },
                        )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

        return {
            "peak_equity": peak,
            "current_equity": current_equity,
            "drawdown_percent": drawdown_pct,
            "threshold_status": threshold_status,
            "max_drawdown_percent": risk_config.max_drawdown_percent,
            "catastrophic_percent": risk_config.max_drawdown_catastrophic_percent,
        }

    async def get_peak_equity(self, db: AsyncSession, current_equity: Decimal | None = None) -> Decimal:
        """Get current peak equity (high-water mark) from portfolio service."""
        _, peak = await self._get_peak_equity(db)
        return peak

    async def reset_peak_equity(self, db: AsyncSession, admin_user: str) -> None:
        """Manual peak equity reset (admin only). Logged."""
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
                    await portfolio_service.reset_peak_equity(db, user_id, admin_user)
                    logger.info("Peak equity reset by %s", admin_user)
                    return
        except Exception as e:
            logger.error("Failed to reset peak equity: %s", e)

    def _get_threshold_status(self, drawdown_pct: Decimal, config: RiskConfig) -> str:
        """Determine threshold level.

        normal: drawdown < max * 0.7
        warning: drawdown >= max * 0.7
        breach: drawdown >= max
        catastrophic: drawdown >= catastrophic threshold
        """
        if drawdown_pct >= config.max_drawdown_catastrophic_percent:
            return "catastrophic"
        if drawdown_pct >= config.max_drawdown_percent:
            return "breach"
        if drawdown_pct >= config.max_drawdown_percent * Decimal("0.7"):
            return "warning"
        return "normal"

    async def _get_current_equity(self, db: AsyncSession) -> tuple[bool, Decimal]:
        """Get current portfolio equity from portfolio service.

        Returns (available: bool, equity: Decimal). If the portfolio
        service is unavailable, returns (False, default_equity).
        """
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
                    equity = await portfolio_service.get_equity(db, user_id)
                    return True, equity
        except Exception:
            pass
        return False, _DEFAULT_INITIAL_EQUITY

    async def _get_peak_equity(self, db: AsyncSession) -> tuple[bool, Decimal]:
        """Get peak equity from portfolio service (PortfolioMeta).

        Returns (available: bool, peak: Decimal).
        """
        try:
            from app.portfolio.repository import PortfolioMetaRepository
            from app.auth.models import User
            from sqlalchemy import select

            result = await db.execute(
                select(User.id).where(User.role == "admin").limit(1)
            )
            user_id = result.scalar_one_or_none()
            if user_id:
                meta_repo = PortfolioMetaRepository()
                peak_str = await meta_repo.get(db, "peak_equity", user_id)
                if peak_str:
                    return True, Decimal(peak_str)
                # No peak recorded yet — use current equity as initial peak
                available, equity = await self._get_current_equity(db)
                return available, equity
        except Exception:
            pass
        return False, _DEFAULT_INITIAL_EQUITY
