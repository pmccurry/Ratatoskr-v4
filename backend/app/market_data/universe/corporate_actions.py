"""Corporate actions fetcher — dividends and splits from Alpaca."""

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.adapters.alpaca import AlpacaAdapter
from app.market_data.config import get_market_data_config
from app.market_data.models import DividendAnnouncement
from app.market_data.repository import DividendAnnouncementRepository
from app.market_data.universe.watchlist import get_watchlist_symbols

logger = logging.getLogger(__name__)

_dividend_repo = DividendAnnouncementRepository()


async def fetch_corporate_actions(
    db: AsyncSession,
    symbols: list[str] | None = None,
    lookforward_days: int | None = None,
) -> dict:
    """Fetch and store corporate actions (dividends).

    1. Determine date range: today through lookforward_days ahead
    2. Call alpaca_adapter.fetch_dividends() for watchlist symbols
    3. Upsert results into dividend_announcements table
    4. Return: {"dividends_found": N, "new": N, "updated": N}
    """
    cfg = get_market_data_config()
    if lookforward_days is None:
        lookforward_days = cfg.corporate_actions_lookforward_days

    if symbols is None:
        symbols = await get_watchlist_symbols(db, market="equities")

    if not symbols:
        logger.info("No equity symbols on watchlist, skipping corporate actions fetch")
        return {"dividends_found": 0, "new": 0, "updated": 0}

    adapter = AlpacaAdapter()

    start_date = date.today()
    end_date = start_date + timedelta(days=lookforward_days)

    dividends = await adapter.fetch_dividends(symbols, start_date, end_date)
    logger.info("Fetched %d dividend announcements from Alpaca", len(dividends))

    new_count = 0
    updated_count = 0

    for div in dividends:
        # Parse date strings if they're strings
        for field in ("declaration_date", "ex_date", "record_date", "payable_date"):
            val = div.get(field)
            if isinstance(val, str):
                div[field] = date.fromisoformat(val)

        announcement = DividendAnnouncement(
            id=uuid4(),
            symbol=div["symbol"],
            corporate_action_id=div["corporate_action_id"],
            ca_type=div.get("ca_type", "cash"),
            declaration_date=div["declaration_date"],
            ex_date=div["ex_date"],
            record_date=div["record_date"],
            payable_date=div["payable_date"],
            cash_amount=div.get("cash_amount", 0),
            stock_rate=div.get("stock_rate"),
            status=div.get("status", "announced"),
            source="alpaca",
            fetched_at=datetime.now(timezone.utc),
        )

        # Check if it already exists
        from sqlalchemy import select
        from app.market_data.models import DividendAnnouncement as DA
        existing = await db.execute(
            select(DA).where(DA.corporate_action_id == div["corporate_action_id"])
        )
        if existing.scalar_one_or_none():
            updated_count += 1
        else:
            new_count += 1

        await _dividend_repo.upsert(db, announcement)

    result = {
        "dividends_found": len(dividends),
        "new": new_count,
        "updated": updated_count,
    }
    logger.info("Corporate actions processed: %s", result)
    return result
