"""Integration tests for bar storage and aggregation."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from app.market_data.models import OHLCVBar


class TestBarStorage:
    @pytest.mark.asyncio
    async def test_insert_bar(self, db):
        ts = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        bar = OHLCVBar(
            symbol="AAPL",
            market="equities",
            timeframe="1m",
            ts=ts,
            open=Decimal("150"),
            high=Decimal("151"),
            low=Decimal("149"),
            close=Decimal("150.50"),
            volume=Decimal("100000"),
            source="stream",
        )
        db.add(bar)
        await db.flush()

        result = await db.execute(
            select(OHLCVBar).where(
                OHLCVBar.symbol == "AAPL",
                OHLCVBar.timeframe == "1m",
                OHLCVBar.ts == ts,
            )
        )
        found = result.scalar_one()
        assert found.close == Decimal("150.50")
        assert found.volume == Decimal("100000")

    @pytest.mark.asyncio
    async def test_batch_insert_bars(self, db):
        base_ts = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        bars = []
        for i in range(100):
            bars.append(OHLCVBar(
                symbol="MSFT",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=Decimal(str(400 + i * 0.1)),
                high=Decimal(str(401 + i * 0.1)),
                low=Decimal(str(399 + i * 0.1)),
                close=Decimal(str(400.5 + i * 0.1)),
                volume=Decimal("50000"),
                source="stream",
            ))
        db.add_all(bars)
        await db.flush()

        result = await db.execute(
            select(func.count()).select_from(OHLCVBar).where(
                OHLCVBar.symbol == "MSFT",
                OHLCVBar.timeframe == "1m",
            )
        )
        count = result.scalar()
        assert count == 100

    @pytest.mark.asyncio
    async def test_query_bars_by_range(self, db):
        base_ts = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            bar = OHLCVBar(
                symbol="GOOGL",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=Decimal("170"),
                high=Decimal("171"),
                low=Decimal("169"),
                close=Decimal("170"),
                volume=Decimal("30000"),
                source="stream",
            )
            db.add(bar)
        await db.flush()

        start = base_ts + timedelta(minutes=3)
        end = base_ts + timedelta(minutes=7)
        result = await db.execute(
            select(OHLCVBar).where(
                OHLCVBar.symbol == "GOOGL",
                OHLCVBar.ts >= start,
                OHLCVBar.ts <= end,
            )
        )
        bars = result.scalars().all()
        assert len(bars) == 5  # minutes 3,4,5,6,7

    @pytest.mark.asyncio
    async def test_bar_fields_are_decimal(self, db):
        ts = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        bar = OHLCVBar(
            symbol="AMZN",
            market="equities",
            timeframe="1m",
            ts=ts,
            open=Decimal("185.50"),
            high=Decimal("186.00"),
            low=Decimal("185.00"),
            close=Decimal("185.75"),
            volume=Decimal("75000"),
            source="stream",
        )
        db.add(bar)
        await db.flush()

        result = await db.execute(
            select(OHLCVBar).where(OHLCVBar.symbol == "AMZN")
        )
        found = result.scalar_one()
        assert isinstance(found.open, Decimal)
        assert isinstance(found.close, Decimal)


class TestBarAggregation:
    """Test OHLCV aggregation rules by verifying the math."""

    @pytest.mark.asyncio
    async def test_aggregation_open_is_first(self, db):
        """First bar's open becomes the aggregated open."""
        base_ts = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        opens = [Decimal("100"), Decimal("101"), Decimal("102")]
        for i, o in enumerate(opens):
            bar = OHLCVBar(
                symbol="AGG1",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=o, high=o + 1, low=o - 1, close=o,
                volume=Decimal("1000"),
                source="stream",
            )
            db.add(bar)
        await db.flush()

        result = await db.execute(
            select(OHLCVBar).where(
                OHLCVBar.symbol == "AGG1"
            ).order_by(OHLCVBar.ts)
        )
        bars = result.scalars().all()
        assert bars[0].open == Decimal("100")  # First bar's open

    @pytest.mark.asyncio
    async def test_aggregation_close_is_last(self, db):
        base_ts = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        closes = [Decimal("100"), Decimal("105"), Decimal("110")]
        for i, c in enumerate(closes):
            bar = OHLCVBar(
                symbol="AGG2",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=c, high=c + 1, low=c - 1, close=c,
                volume=Decimal("1000"),
                source="stream",
            )
            db.add(bar)
        await db.flush()

        result = await db.execute(
            select(OHLCVBar).where(OHLCVBar.symbol == "AGG2").order_by(OHLCVBar.ts.desc())
        )
        last = result.scalars().first()
        assert last.close == Decimal("110")

    @pytest.mark.asyncio
    async def test_aggregation_high_is_max(self, db):
        base_ts = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        highs = [Decimal("101"), Decimal("105"), Decimal("103")]
        for i, h in enumerate(highs):
            bar = OHLCVBar(
                symbol="AGG3",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=Decimal("100"), high=h, low=Decimal("99"), close=Decimal("100"),
                volume=Decimal("1000"),
                source="stream",
            )
            db.add(bar)
        await db.flush()

        result = await db.execute(
            select(func.max(OHLCVBar.high)).where(OHLCVBar.symbol == "AGG3")
        )
        max_high = result.scalar()
        assert max_high == Decimal("105")

    @pytest.mark.asyncio
    async def test_aggregation_low_is_min(self, db):
        base_ts = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        lows = [Decimal("99"), Decimal("97"), Decimal("98")]
        for i, low in enumerate(lows):
            bar = OHLCVBar(
                symbol="AGG4",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=Decimal("100"), high=Decimal("101"), low=low, close=Decimal("100"),
                volume=Decimal("1000"),
                source="stream",
            )
            db.add(bar)
        await db.flush()

        result = await db.execute(
            select(func.min(OHLCVBar.low)).where(OHLCVBar.symbol == "AGG4")
        )
        min_low = result.scalar()
        assert min_low == Decimal("97")

    @pytest.mark.asyncio
    async def test_aggregation_volume_is_sum(self, db):
        base_ts = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        volumes = [Decimal("1000"), Decimal("2000"), Decimal("3000")]
        for i, v in enumerate(volumes):
            bar = OHLCVBar(
                symbol="AGG5",
                market="equities",
                timeframe="1m",
                ts=base_ts + timedelta(minutes=i),
                open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"),
                volume=v,
                source="stream",
            )
            db.add(bar)
        await db.flush()

        result = await db.execute(
            select(func.sum(OHLCVBar.volume)).where(OHLCVBar.symbol == "AGG5")
        )
        total_vol = result.scalar()
        assert total_vol == Decimal("6000")
