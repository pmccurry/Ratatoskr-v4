"""Higher-level watchlist operations."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.models import WatchlistEntry
from app.market_data.repository import WatchlistRepository

_repo = WatchlistRepository()


async def get_active_watchlist(
    db: AsyncSession, market: str | None = None
) -> list[WatchlistEntry]:
    """Get all active watchlist entries, optionally filtered by market."""
    return await _repo.get_active(db, market)


async def is_symbol_active(db: AsyncSession, symbol: str) -> bool:
    """Check if a symbol is on the active watchlist."""
    entry = await _repo.get_by_symbol(db, symbol)
    return entry is not None


async def get_watchlist_symbols(
    db: AsyncSession, market: str | None = None
) -> list[str]:
    """Get just the symbol strings from the active watchlist."""
    entries = await _repo.get_active(db, market)
    return [e.symbol for e in entries]


async def get_watchlist_stats(db: AsyncSession) -> dict:
    """Return counts: total, equities, forex, recently_added, recently_removed."""
    from datetime import datetime, timedelta, timezone

    all_entries = await _repo.get_active(db)
    equities = [e for e in all_entries if e.market == "equities"]
    forex = [e for e in all_entries if e.market == "forex"]

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    recently_added = [e for e in all_entries if e.added_at and e.added_at >= cutoff]

    # Count recently removed (inactive with removed_at in last 24h)
    result = await db.execute(
        select(func.count())
        .select_from(WatchlistEntry)
        .where(
            WatchlistEntry.status == "inactive",
            WatchlistEntry.removed_at >= cutoff,
        )
    )
    recently_removed_count = result.scalar_one()

    return {
        "total": len(all_entries),
        "equities": len(equities),
        "forex": len(forex),
        "recently_added": len(recently_added),
        "recently_removed": recently_removed_count,
    }
