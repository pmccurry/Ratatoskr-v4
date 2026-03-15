"""Universe filter — narrows available symbols to a tradable watchlist."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.adapters.alpaca import AlpacaAdapter
from app.market_data.adapters.oanda import OandaAdapter
from app.market_data.config import get_market_data_config
from app.market_data.models import MarketSymbol, WatchlistEntry
from app.market_data.repository import MarketSymbolRepository, WatchlistRepository

logger = logging.getLogger(__name__)

_symbol_repo = MarketSymbolRepository()
_watchlist_repo = WatchlistRepository()


async def run_equities_filter(db: AsyncSession) -> int:
    """Run the equities universe filter.

    1. Fetch all symbols from Alpaca
    2. Filter by exchange
    3. Upsert into market_symbols
    4. Fetch latest daily bars to get volume/price
    5. Filter by volume and price
    6. Update watchlist
    """
    cfg = get_market_data_config()
    adapter = AlpacaAdapter()

    # Step 1: Fetch available symbols
    all_symbols = await adapter.list_available_symbols()
    logger.info("Equities filter: %d total tradable symbols from Alpaca", len(all_symbols))

    # Step 2: Filter by exchange
    allowed_exchanges = [e.strip() for e in cfg.equities_exchanges.split(",")]
    exchange_filtered = [
        s for s in all_symbols
        if s.get("exchange") in allowed_exchanges
    ]
    logger.info("Equities filter: %d symbols after exchange filter (%s)", len(exchange_filtered), allowed_exchanges)

    # Step 3: Upsert into market_symbols
    for sym_data in exchange_filtered:
        ms = MarketSymbol(
            id=uuid4(),
            symbol=sym_data["symbol"],
            name=sym_data["name"],
            market="equities",
            exchange=sym_data.get("exchange"),
            base_asset=None,
            quote_asset="USD",
            broker="alpaca",
            status="active",
            options_enabled=sym_data.get("options_enabled", False),
        )
        await _symbol_repo.upsert(db, ms)

    # Step 4: Fetch latest daily bars for volume/price filtering
    symbol_names = [s["symbol"] for s in exchange_filtered]
    bar_data = await adapter.fetch_latest_bars_batch(symbol_names, timeframe="1Day", limit=1)

    # Step 5: Filter by volume and price
    min_volume = cfg.equities_min_volume
    min_price = Decimal(str(cfg.equities_min_price))
    passing_symbols = []

    for sym_data in exchange_filtered:
        sym = sym_data["symbol"]
        bar = bar_data.get(sym)
        if not bar:
            continue
        volume = bar.get("volume", Decimal("0"))
        price = bar.get("close", Decimal("0"))
        if volume >= min_volume and price >= min_price:
            passing_symbols.append({
                **sym_data,
                "filter_metadata": {
                    "avg_volume": float(volume),
                    "last_price": float(price),
                },
            })

    logger.info(
        "Equities filter: %d symbols after volume/price filter (min_vol=%d, min_price=%s)",
        len(passing_symbols), min_volume, min_price,
    )

    # Step 6: Update watchlist
    active_count = await _update_watchlist(db, passing_symbols, market="equities", broker="alpaca")
    return active_count


async def run_forex_filter(db: AsyncSession) -> int:
    """Run the forex universe filter using configured pairs list."""
    cfg = get_market_data_config()
    adapter = OandaAdapter()

    # Fetch all instruments from OANDA
    all_instruments = await adapter.list_available_symbols()

    # Get configured forex pairs from settings
    from app.common.config import get_settings
    settings = get_settings()
    forex_pairs_setting = getattr(settings, "universe_filter_forex_pairs", "")
    if forex_pairs_setting:
        configured_pairs = {p.strip() for p in forex_pairs_setting.split(",") if p.strip()}
    else:
        # If no pairs configured, use all available instruments
        configured_pairs = {inst["symbol"] for inst in all_instruments}

    # Filter to configured pairs
    matching = [inst for inst in all_instruments if inst["symbol"] in configured_pairs]
    logger.info("Forex filter: %d pairs matching config out of %d available", len(matching), len(all_instruments))

    # Upsert into market_symbols
    for sym_data in matching:
        ms = MarketSymbol(
            id=uuid4(),
            symbol=sym_data["symbol"],
            name=sym_data["name"],
            market="forex",
            exchange=None,
            base_asset=sym_data.get("base_asset"),
            quote_asset=sym_data.get("quote_asset"),
            broker="oanda",
            status="active",
            options_enabled=False,
        )
        await _symbol_repo.upsert(db, ms)

    # Build passing list with empty filter metadata (forex is config-driven, not filtered)
    passing_symbols = [
        {**inst, "filter_metadata": {"source": "config"}}
        for inst in matching
    ]

    active_count = await _update_watchlist(db, passing_symbols, market="forex", broker="oanda")
    return active_count


async def run_universe_filter(db: AsyncSession) -> dict:
    """Run universe filter for all markets."""
    equities_count = await run_equities_filter(db)
    forex_count = await run_forex_filter(db)

    result = {
        "equities": equities_count,
        "forex": forex_count,
        "total": equities_count + forex_count,
    }
    logger.info("Universe filter complete: %s", result)
    return result


async def _update_watchlist(
    db: AsyncSession,
    passing_symbols: list[dict],
    market: str,
    broker: str,
) -> int:
    """Update watchlist: add new symbols, deactivate removed ones."""
    # Get current active watchlist for this market
    current_entries = await _watchlist_repo.get_active(db, market=market)
    current_symbols = {e.symbol for e in current_entries}
    new_symbols = {s["symbol"] for s in passing_symbols}

    # Deactivate removed symbols
    removed = current_symbols - new_symbols
    for sym in removed:
        await _watchlist_repo.deactivate(db, sym)
        logger.info("Watchlist: deactivated %s (%s)", sym, market)

    # Add new symbols
    added = new_symbols - current_symbols
    passing_by_symbol = {s["symbol"]: s for s in passing_symbols}
    for sym in added:
        sym_data = passing_by_symbol[sym]
        entry = WatchlistEntry(
            id=uuid4(),
            symbol=sym,
            market=market,
            broker=broker,
            status="active",
            added_at=datetime.now(timezone.utc),
            filter_metadata_json=sym_data.get("filter_metadata"),
        )
        await _watchlist_repo.add(db, entry)

    logger.info(
        "Watchlist %s: %d added, %d removed, %d total active",
        market, len(added), len(removed), len(new_symbols),
    )
    return len(new_symbols)
