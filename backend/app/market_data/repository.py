"""Database access layer for market data models."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.models import (
    BackfillJob,
    DividendAnnouncement,
    MarketSymbol,
    OHLCVBar,
    WatchlistEntry,
)


class MarketSymbolRepository:
    """Repository for market symbol operations."""

    async def get_by_id(self, db: AsyncSession, symbol_id: UUID) -> MarketSymbol | None:
        result = await db.execute(
            select(MarketSymbol).where(MarketSymbol.id == symbol_id)
        )
        return result.scalar_one_or_none()

    async def get_by_symbol(
        self, db: AsyncSession, symbol: str, market: str
    ) -> MarketSymbol | None:
        result = await db.execute(
            select(MarketSymbol).where(
                MarketSymbol.symbol == symbol,
                MarketSymbol.market == market,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, market: str | None = None, status: str = "active"
    ) -> list[MarketSymbol]:
        stmt = select(MarketSymbol).where(MarketSymbol.status == status)
        if market:
            stmt = stmt.where(MarketSymbol.market == market)
        stmt = stmt.order_by(MarketSymbol.symbol)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, symbol: MarketSymbol) -> MarketSymbol:
        db.add(symbol)
        await db.flush()
        return symbol

    async def update(self, db: AsyncSession, symbol: MarketSymbol) -> MarketSymbol:
        await db.flush()
        return symbol

    async def upsert(self, db: AsyncSession, symbol: MarketSymbol) -> MarketSymbol:
        stmt = pg_insert(MarketSymbol).values(
            id=symbol.id,
            symbol=symbol.symbol,
            name=symbol.name,
            market=symbol.market,
            exchange=symbol.exchange,
            base_asset=symbol.base_asset,
            quote_asset=symbol.quote_asset,
            broker=symbol.broker,
            status=symbol.status,
            options_enabled=symbol.options_enabled,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_market_symbols_symbol_market_broker",
            set_={
                "name": stmt.excluded.name,
                "exchange": stmt.excluded.exchange,
                "base_asset": stmt.excluded.base_asset,
                "quote_asset": stmt.excluded.quote_asset,
                "status": stmt.excluded.status,
                "options_enabled": stmt.excluded.options_enabled,
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
        await db.flush()
        # Re-fetch the upserted row
        return await self.get_by_symbol(db, symbol.symbol, symbol.market)


class WatchlistRepository:
    """Repository for watchlist operations."""

    async def get_active(
        self, db: AsyncSession, market: str | None = None
    ) -> list[WatchlistEntry]:
        stmt = select(WatchlistEntry).where(WatchlistEntry.status == "active")
        if market:
            stmt = stmt.where(WatchlistEntry.market == market)
        stmt = stmt.order_by(WatchlistEntry.symbol)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbol(
        self, db: AsyncSession, symbol: str
    ) -> WatchlistEntry | None:
        result = await db.execute(
            select(WatchlistEntry).where(
                WatchlistEntry.symbol == symbol,
                WatchlistEntry.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def add(self, db: AsyncSession, entry: WatchlistEntry) -> WatchlistEntry:
        db.add(entry)
        await db.flush()
        return entry

    async def deactivate(self, db: AsyncSession, symbol: str) -> None:
        result = await db.execute(
            select(WatchlistEntry).where(
                WatchlistEntry.symbol == symbol,
                WatchlistEntry.status == "active",
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.status = "inactive"
            entry.removed_at = datetime.now(timezone.utc)
            await db.flush()

    async def get_paginated(
        self,
        db: AsyncSession,
        market: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WatchlistEntry], int]:
        stmt = select(WatchlistEntry)
        count_stmt = select(func.count()).select_from(WatchlistEntry)

        if market:
            stmt = stmt.where(WatchlistEntry.market == market)
            count_stmt = count_stmt.where(WatchlistEntry.market == market)
        if status:
            stmt = stmt.where(WatchlistEntry.status == status)
            count_stmt = count_stmt.where(WatchlistEntry.status == status)

        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(WatchlistEntry.symbol)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)

        return list(result.scalars().all()), total


class OHLCVBarRepository:
    """Repository for OHLCV bar operations."""

    async def get_bars(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[OHLCVBar]:
        stmt = select(OHLCVBar).where(
            OHLCVBar.symbol == symbol,
            OHLCVBar.timeframe == timeframe,
        )
        if start:
            stmt = stmt.where(OHLCVBar.ts >= start)
        if end:
            stmt = stmt.where(OHLCVBar.ts <= end)
        stmt = stmt.order_by(OHLCVBar.ts.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_close(
        self, db: AsyncSession, symbol: str, timeframe: str = "1m"
    ) -> Decimal | None:
        stmt = (
            select(OHLCVBar.close)
            .where(OHLCVBar.symbol == symbol, OHLCVBar.timeframe == timeframe)
            .order_by(OHLCVBar.ts.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return Decimal(str(row)) if row is not None else None

    async def upsert_bars(self, db: AsyncSession, bars: list[OHLCVBar]) -> int:
        if not bars:
            return 0

        values = [
            {
                "id": bar.id,
                "symbol": bar.symbol,
                "market": bar.market,
                "timeframe": bar.timeframe,
                "ts": bar.ts,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "source": bar.source,
                "is_aggregated": bar.is_aggregated,
            }
            for bar in bars
        ]

        stmt = pg_insert(OHLCVBar).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ohlcv_bars_symbol_timeframe_ts",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
                "is_aggregated": stmt.excluded.is_aggregated,
            },
        )
        await db.execute(stmt)
        await db.flush()
        return len(values)

    async def get_latest_timestamp(
        self, db: AsyncSession, symbol: str, timeframe: str
    ) -> datetime | None:
        stmt = (
            select(func.max(OHLCVBar.ts))
            .where(OHLCVBar.symbol == symbol, OHLCVBar.timeframe == timeframe)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class BackfillJobRepository:
    """Repository for backfill job operations."""

    async def create(self, db: AsyncSession, job: BackfillJob) -> BackfillJob:
        db.add(job)
        await db.flush()
        return job

    async def update(self, db: AsyncSession, job: BackfillJob) -> BackfillJob:
        await db.flush()
        return job

    async def get_pending(self, db: AsyncSession) -> list[BackfillJob]:
        result = await db.execute(
            select(BackfillJob)
            .where(BackfillJob.status == "pending")
            .order_by(BackfillJob.created_at)
        )
        return list(result.scalars().all())

    async def get_by_symbol(
        self, db: AsyncSession, symbol: str, timeframe: str
    ) -> BackfillJob | None:
        result = await db.execute(
            select(BackfillJob)
            .where(BackfillJob.symbol == symbol, BackfillJob.timeframe == timeframe)
            .order_by(BackfillJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, status: str | None = None
    ) -> list[BackfillJob]:
        stmt = select(BackfillJob)
        if status:
            stmt = stmt.where(BackfillJob.status == status)
        stmt = stmt.order_by(BackfillJob.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())


class DividendAnnouncementRepository:
    """Repository for dividend announcement operations."""

    async def upsert(
        self, db: AsyncSession, announcement: DividendAnnouncement
    ) -> DividendAnnouncement:
        stmt = pg_insert(DividendAnnouncement).values(
            id=announcement.id,
            symbol=announcement.symbol,
            corporate_action_id=announcement.corporate_action_id,
            ca_type=announcement.ca_type,
            declaration_date=announcement.declaration_date,
            ex_date=announcement.ex_date,
            record_date=announcement.record_date,
            payable_date=announcement.payable_date,
            cash_amount=announcement.cash_amount,
            stock_rate=announcement.stock_rate,
            status=announcement.status,
            source=announcement.source,
            fetched_at=announcement.fetched_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["corporate_action_id"],
            set_={
                "ca_type": stmt.excluded.ca_type,
                "declaration_date": stmt.excluded.declaration_date,
                "ex_date": stmt.excluded.ex_date,
                "record_date": stmt.excluded.record_date,
                "payable_date": stmt.excluded.payable_date,
                "cash_amount": stmt.excluded.cash_amount,
                "stock_rate": stmt.excluded.stock_rate,
                "status": stmt.excluded.status,
                "fetched_at": stmt.excluded.fetched_at,
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
        await db.flush()
        # Re-fetch
        result = await db.execute(
            select(DividendAnnouncement).where(
                DividendAnnouncement.corporate_action_id == announcement.corporate_action_id
            )
        )
        return result.scalar_one()

    async def get_upcoming(
        self, db: AsyncSession, symbol: str | None = None, days_ahead: int = 30
    ) -> list[DividendAnnouncement]:
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)
        stmt = select(DividendAnnouncement).where(
            DividendAnnouncement.ex_date >= today,
            DividendAnnouncement.ex_date <= cutoff,
        )
        if symbol:
            stmt = stmt.where(DividendAnnouncement.symbol == symbol)
        stmt = stmt.order_by(DividendAnnouncement.ex_date)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ex_date(
        self, db: AsyncSession, ex_date: date
    ) -> list[DividendAnnouncement]:
        result = await db.execute(
            select(DividendAnnouncement)
            .where(DividendAnnouncement.ex_date == ex_date)
            .order_by(DividendAnnouncement.symbol)
        )
        return list(result.scalars().all())

    async def get_by_payable_date(
        self, db: AsyncSession, payable_date: date
    ) -> list[DividendAnnouncement]:
        result = await db.execute(
            select(DividendAnnouncement)
            .where(DividendAnnouncement.payable_date == payable_date)
            .order_by(DividendAnnouncement.symbol)
        )
        return list(result.scalars().all())
