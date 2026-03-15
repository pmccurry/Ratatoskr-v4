"""Exposure calculations — per-symbol, per-strategy, portfolio-wide."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.risk.models import RiskConfig

logger = logging.getLogger(__name__)

_DEFAULT_INITIAL_EQUITY = Decimal("100000.00")


class ExposureCalculator:
    """Calculates exposure per-symbol, per-strategy, and portfolio-wide.

    NOTE: Until TASK-013, all exposure values return zero.
    """

    async def get_exposure(self, db: AsyncSession, risk_config: RiskConfig) -> dict:
        """Calculate all exposure metrics."""
        portfolio_equity = await self._get_portfolio_equity(db)
        by_symbol = await self._get_symbol_exposure(db)
        by_strategy = await self._get_strategy_exposure(db)
        total_value = sum(by_symbol.values(), Decimal("0"))

        total_pct = Decimal("0")
        if portfolio_equity > 0:
            total_pct = total_value / portfolio_equity * 100

        return {
            "total_percent": total_pct,
            "total_value": total_value,
            "by_symbol": by_symbol,
            "by_strategy": by_strategy,
            "portfolio_equity": portfolio_equity,
        }

    async def get_symbol_exposure(self, db: AsyncSession, symbol: str) -> Decimal:
        """Total value of positions in a symbol across all strategies."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                return await portfolio_service.get_symbol_exposure(db, symbol)
        except Exception:
            pass
        return Decimal("0")

    async def get_strategy_exposure(self, db: AsyncSession, strategy_id: UUID) -> Decimal:
        """Total value of positions for a strategy."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                return await portfolio_service.get_strategy_exposure(db, strategy_id)
        except Exception:
            pass
        return Decimal("0")

    async def _get_symbol_exposure(self, db: AsyncSession) -> dict[str, Decimal]:
        """Get exposure by symbol from portfolio."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                from app.portfolio.repository import PositionRepository
                repo = PositionRepository()
                from app.portfolio.models import Position
                from sqlalchemy import select
                result = await db.execute(
                    select(Position.symbol, Position.market_value)
                    .where(Position.status == "open")
                )
                exposure: dict[str, Decimal] = {}
                for row in result.all():
                    sym, val = row
                    exposure[sym] = exposure.get(sym, Decimal("0")) + val
                return exposure
        except Exception:
            pass
        return {}

    async def _get_strategy_exposure(self, db: AsyncSession) -> dict[str, Decimal]:
        """Get exposure by strategy from portfolio."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                from app.portfolio.models import Position
                from sqlalchemy import select
                result = await db.execute(
                    select(Position.strategy_id, Position.market_value)
                    .where(Position.status == "open")
                )
                exposure: dict[str, Decimal] = {}
                for row in result.all():
                    sid, val = row
                    key = str(sid)
                    exposure[key] = exposure.get(key, Decimal("0")) + val
                return exposure
        except Exception:
            pass
        return {}

    async def _get_portfolio_equity(self, db: AsyncSession) -> Decimal:
        """Get portfolio equity."""
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
                    return await portfolio_service.get_equity(db, user_id)
        except Exception:
            pass
        return _DEFAULT_INITIAL_EQUITY
