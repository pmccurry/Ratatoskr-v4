"""Integration tests for signal lifecycle."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.signals.models import Signal


class TestSignalCreation:
    @pytest.mark.asyncio
    async def test_create_signal_pending(self, db, sample_strategy, admin_user):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now,
            expires_at=now + timedelta(seconds=300),
        )
        db.add(signal)
        await db.flush()

        assert signal.id is not None
        assert signal.status == "pending"

    @pytest.mark.asyncio
    async def test_signal_has_expires_at(self, db, sample_strategy, admin_user):
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=600)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="MSFT",
            market="equities",
            timeframe="5m",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now,
            expires_at=expires,
        )
        db.add(signal)
        await db.flush()

        assert signal.expires_at is not None
        assert signal.expires_at == expires

    @pytest.mark.asyncio
    async def test_signal_with_confidence(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            confidence=Decimal("0.85"),
            status="pending",
            ts=now,
        )
        db.add(signal)
        await db.flush()
        assert signal.confidence == Decimal("0.85")


class TestSignalTransitions:
    @pytest.mark.asyncio
    async def test_pending_to_risk_approved(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now,
        )
        db.add(signal)
        await db.flush()

        signal.status = "risk_approved"
        await db.flush()
        assert signal.status == "risk_approved"

    @pytest.mark.asyncio
    async def test_pending_to_risk_rejected(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now,
        )
        db.add(signal)
        await db.flush()

        signal.status = "risk_rejected"
        await db.flush()
        assert signal.status == "risk_rejected"

    @pytest.mark.asyncio
    async def test_pending_to_expired(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now,
            expires_at=now - timedelta(seconds=60),  # Already expired
        )
        db.add(signal)
        await db.flush()

        signal.status = "expired"
        await db.flush()
        assert signal.status == "expired"

    @pytest.mark.asyncio
    async def test_pending_to_canceled(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now,
        )
        db.add(signal)
        await db.flush()

        signal.status = "canceled"
        await db.flush()
        assert signal.status == "canceled"


class TestSignalQuery:
    @pytest.mark.asyncio
    async def test_query_by_strategy(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        for i in range(3):
            signal = Signal(
                strategy_id=sample_strategy.id,
                strategy_version="1.0.0",
                symbol=f"SYM{i}",
                market="equities",
                timeframe="1h",
                side="buy",
                signal_type="entry",
                source="strategy",
                status="pending",
                ts=now + timedelta(seconds=i),
            )
            db.add(signal)
        await db.flush()

        result = await db.execute(
            select(Signal).where(Signal.strategy_id == sample_strategy.id)
        )
        signals = result.scalars().all()
        assert len(signals) >= 3

    @pytest.mark.asyncio
    async def test_query_by_status(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        s1 = Signal(
            strategy_id=sample_strategy.id, strategy_version="1.0.0",
            symbol="AAPL", market="equities", timeframe="1h",
            side="buy", signal_type="entry", source="strategy",
            status="pending", ts=now,
        )
        s2 = Signal(
            strategy_id=sample_strategy.id, strategy_version="1.0.0",
            symbol="MSFT", market="equities", timeframe="1h",
            side="buy", signal_type="entry", source="strategy",
            status="risk_approved", ts=now,
        )
        db.add_all([s1, s2])
        await db.flush()

        result = await db.execute(
            select(Signal).where(Signal.status == "pending")
        )
        pending = result.scalars().all()
        assert any(s.symbol == "AAPL" for s in pending)


class TestSignalExpiry:
    @pytest.mark.asyncio
    async def test_expired_signal_identifiable(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="pending",
            ts=now - timedelta(minutes=10),
            expires_at=now - timedelta(minutes=5),
        )
        db.add(signal)
        await db.flush()

        # Query for expired pending signals
        result = await db.execute(
            select(Signal).where(
                Signal.status == "pending",
                Signal.expires_at < now,
            )
        )
        expired = result.scalars().all()
        assert any(s.id == signal.id for s in expired)

    @pytest.mark.asyncio
    async def test_processed_signal_not_in_expired_query(self, db, sample_strategy):
        now = datetime.now(timezone.utc)
        signal = Signal(
            strategy_id=sample_strategy.id,
            strategy_version="1.0.0",
            symbol="AAPL",
            market="equities",
            timeframe="1h",
            side="buy",
            signal_type="entry",
            source="strategy",
            status="risk_approved",
            ts=now - timedelta(minutes=10),
            expires_at=now - timedelta(minutes=5),
        )
        db.add(signal)
        await db.flush()

        result = await db.execute(
            select(Signal).where(
                Signal.status == "pending",
                Signal.expires_at < now,
            )
        )
        expired = result.scalars().all()
        assert not any(s.id == signal.id for s in expired)
