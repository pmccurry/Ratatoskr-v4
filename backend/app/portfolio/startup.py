"""Portfolio module startup and shutdown."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.config import PortfolioConfig
from app.portfolio.fill_processor import FillProcessor
from app.portfolio.mark_to_market import MarkToMarket
from app.portfolio.pnl import PnlLedger
from app.portfolio.service import PortfolioService
from app.portfolio.snapshots import SnapshotManager

logger = logging.getLogger(__name__)

_portfolio_service: PortfolioService | None = None
_mark_to_market: MarkToMarket | None = None
_snapshot_manager: SnapshotManager | None = None
_pnl_ledger: PnlLedger | None = None


async def start_portfolio(db: AsyncSession, user_id: object) -> None:
    """Initialize portfolio module."""
    global _portfolio_service, _mark_to_market, _snapshot_manager, _pnl_ledger

    config = PortfolioConfig()
    fill_processor = FillProcessor()
    _portfolio_service = PortfolioService(config, fill_processor)

    # Initialize cash balances
    await _portfolio_service.initialize_cash(db, user_id)

    # Start mark-to-market
    _mark_to_market = MarkToMarket(config)
    await _mark_to_market.start()

    # Initialize PnL ledger
    _pnl_ledger = PnlLedger()

    # Initialize and start snapshot manager
    _snapshot_manager = SnapshotManager(config)
    await _snapshot_manager.start_periodic()

    logger.info("Portfolio module started")


async def stop_portfolio() -> None:
    """Stop mark-to-market and snapshots."""
    global _mark_to_market, _snapshot_manager

    if _snapshot_manager:
        await _snapshot_manager.stop_periodic()
        _snapshot_manager = None

    if _mark_to_market:
        await _mark_to_market.stop()
        _mark_to_market = None

    logger.info("Portfolio module stopped")


def get_portfolio_service() -> PortfolioService | None:
    """Get the service singleton for inter-module use."""
    return _portfolio_service


def get_snapshot_manager() -> SnapshotManager | None:
    """Get the snapshot manager singleton."""
    return _snapshot_manager


def get_pnl_ledger() -> PnlLedger | None:
    """Get the PnL ledger singleton."""
    return _pnl_ledger
