"""Market data service — inter-module interface.

Other modules call these methods. Health monitoring remains
as NotImplementedError until TASK-007.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.adapters.alpaca import AlpacaAdapter
from app.market_data.config import get_market_data_config
from app.market_data.models import OHLCVBar, WatchlistEntry
from app.market_data.options.chain import OptionChainCache
from app.market_data.repository import (
    DividendAnnouncementRepository,
    OHLCVBarRepository,
    WatchlistRepository,
)

_bar_repo = OHLCVBarRepository()
_watchlist_repo = WatchlistRepository()
_dividend_repo = DividendAnnouncementRepository()
_option_cache = OptionChainCache(ttl_sec=get_market_data_config().option_cache_ttl)


class MarketDataService:
    """Market data service — inter-module interface."""

    async def get_bars(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        limit: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[OHLCVBar]:
        """Get OHLCV bars for a symbol. Used by: strategy runner, portfolio MTM."""
        return await _bar_repo.get_bars(
            db, symbol, timeframe, limit=limit or 200, start=start, end=end
        )

    async def get_latest_close(
        self, db: AsyncSession, symbol: str, timeframe: str = "1m"
    ) -> Decimal | None:
        """Get the most recent close price. Used by: paper trading, portfolio MTM."""
        return await _bar_repo.get_latest_close(db, symbol, timeframe)

    async def is_symbol_on_watchlist(
        self, db: AsyncSession, symbol: str
    ) -> bool:
        """Check if a symbol is on the active watchlist. Used by: risk, signals."""
        entry = await _watchlist_repo.get_by_symbol(db, symbol)
        return entry is not None

    async def get_watchlist(
        self, db: AsyncSession, market: str | None = None
    ) -> list[WatchlistEntry]:
        """Get the current active watchlist. Used by: strategy runner."""
        return await _watchlist_repo.get_active(db, market)

    async def get_health(self, db: AsyncSession) -> dict:
        """Get market data health status. Used by: strategy runner, dashboard."""
        from app.market_data.startup import get_health_monitor

        monitor = get_health_monitor()
        if monitor is None:
            return {
                "overall_status": "unhealthy",
                "connections": {},
                "stale_symbols": [],
                "write_pipeline": {
                    "queue_depth": 0,
                    "queue_capacity": 0,
                    "queue_utilization_percent": 0,
                    "status": "unknown",
                },
                "backfill": {"pending_jobs": 0, "running_jobs": 0, "failed_jobs": 0},
            }
        return await monitor.get_health_status(db)

    async def get_option_chain(self, underlying_symbol: str) -> dict | None:
        """Get option chain snapshot with caching."""
        # Check cache first
        cached = _option_cache.get(underlying_symbol)
        if cached is not None:
            return cached

        # Fetch from Alpaca
        adapter = AlpacaAdapter()
        chain = await adapter.fetch_option_chain(underlying_symbol)
        if chain is not None:
            _option_cache.set(underlying_symbol, chain)

        return chain

    async def get_upcoming_dividends(
        self, db: AsyncSession, symbol: str | None = None
    ) -> list:
        """Get upcoming dividend announcements. Used by: strategy runner, portfolio."""
        return await _dividend_repo.get_upcoming(db, symbol)

    async def get_dividend_yield(
        self, db: AsyncSession, symbol: str
    ) -> Decimal | None:
        """Calculate annualized dividend yield from stored dividends.

        1. Get recent dividends for symbol (last 12 months)
        2. Sum the per-share amounts
        3. Get current price
        4. yield = annual_dividends / current_price * 100
        """
        today = date.today()
        one_year_ago = today - timedelta(days=365)

        # Get dividends paid in last 12 months
        from sqlalchemy import select
        from app.market_data.models import DividendAnnouncement
        result = await db.execute(
            select(DividendAnnouncement).where(
                DividendAnnouncement.symbol == symbol,
                DividendAnnouncement.ex_date >= one_year_ago,
                DividendAnnouncement.ex_date <= today,
            )
        )
        dividends = list(result.scalars().all())

        if not dividends:
            return None

        annual_amount = sum(d.cash_amount for d in dividends)

        # Get current price
        current_price = await _bar_repo.get_latest_close(db, symbol)
        if not current_price or current_price == 0:
            return None

        dividend_yield = (annual_amount / current_price) * Decimal("100")
        return dividend_yield.quantize(Decimal("0.01"))

    async def get_next_ex_date(self, db: AsyncSession, symbol: str) -> date | None:
        """Get next ex-dividend date. Used by: strategy indicators."""
        upcoming = await _dividend_repo.get_upcoming(db, symbol, days_ahead=365)
        if upcoming:
            return upcoming[0].ex_date
        return None

    async def run_universe_filter(self, db: AsyncSession) -> dict:
        """Run the universe filter for all markets."""
        from app.market_data.universe.filter import run_universe_filter
        return await run_universe_filter(db)

    async def run_backfill(
        self,
        db: AsyncSession,
        symbols: list[str] | None = None,
        timeframes: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        """Run historical backfill."""
        from app.market_data.backfill.runner import run_backfill
        return await run_backfill(db, symbols=symbols, timeframes=timeframes, force=force)

    async def fetch_corporate_actions(
        self, db: AsyncSession, symbols: list[str] | None = None
    ) -> dict:
        """Fetch and store corporate actions."""
        from app.market_data.universe.corporate_actions import fetch_corporate_actions
        return await fetch_corporate_actions(db, symbols=symbols)
