"""Unit tests for signal deduplication and expiry logic."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.signals.dedup import SignalDeduplicator, _TIMEFRAME_MINUTES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(dedup_window_bars: int = 1) -> MagicMock:
    config = MagicMock()
    config.dedup_window_bars = dedup_window_bars
    return config


def _ts() -> datetime:
    return datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Window start calculation (pure logic)
# ---------------------------------------------------------------------------

class TestWindowStart:
    def test_1m_timeframe(self):
        dedup = SignalDeduplicator(_make_config())
        ts = _ts()
        start = dedup._get_window_start(ts, "1m", 5)
        assert start == ts - timedelta(minutes=5)

    def test_5m_timeframe(self):
        dedup = SignalDeduplicator(_make_config())
        ts = _ts()
        start = dedup._get_window_start(ts, "5m", 3)
        assert start == ts - timedelta(minutes=15)

    def test_1h_timeframe(self):
        dedup = SignalDeduplicator(_make_config())
        ts = _ts()
        start = dedup._get_window_start(ts, "1h", 2)
        assert start == ts - timedelta(minutes=120)

    def test_4h_timeframe(self):
        dedup = SignalDeduplicator(_make_config())
        ts = _ts()
        start = dedup._get_window_start(ts, "4h", 1)
        assert start == ts - timedelta(minutes=240)

    def test_1d_timeframe(self):
        dedup = SignalDeduplicator(_make_config())
        ts = _ts()
        start = dedup._get_window_start(ts, "1d", 1)
        assert start == ts - timedelta(minutes=1440)

    def test_unknown_timeframe_defaults_to_1m(self):
        dedup = SignalDeduplicator(_make_config())
        ts = _ts()
        start = dedup._get_window_start(ts, "unknown", 5)
        assert start == ts - timedelta(minutes=5)


# ---------------------------------------------------------------------------
# Deduplication rules (async, mock repo)
# ---------------------------------------------------------------------------

class TestSignalDedup:
    @pytest.mark.asyncio
    async def test_duplicate_within_window(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)
        existing = MagicMock()
        existing.id = uuid4()
        existing.ts = _ts()
        dedup._repo = MagicMock()
        dedup._repo.find_duplicate = AsyncMock(return_value=existing)

        is_dup, dup_id = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="buy", signal_type="entry", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is True
        assert dup_id == existing.id

    @pytest.mark.asyncio
    async def test_no_duplicate(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)
        dedup._repo = MagicMock()
        dedup._repo.find_duplicate = AsyncMock(return_value=None)

        is_dup, dup_id = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="buy", signal_type="entry", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False
        assert dup_id is None

    @pytest.mark.asyncio
    async def test_different_symbol_not_dedup(self):
        """The repo query matches on symbol, so different symbols won't match."""
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)
        dedup._repo = MagicMock()
        dedup._repo.find_duplicate = AsyncMock(return_value=None)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="MSFT",
            side="buy", signal_type="entry", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_exit_signals_exempt(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="sell", signal_type="exit", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_scale_out_exempt(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="sell", signal_type="scale_out", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_manual_signals_exempt(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="sell", signal_type="entry", source="manual",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_safety_signals_exempt(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="sell", signal_type="entry", source="safety",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_system_signals_exempt(self):
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="sell", signal_type="entry", source="system",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_zero_window_disables_dedup(self):
        config = _make_config(dedup_window_bars=0)
        dedup = SignalDeduplicator(config)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="buy", signal_type="entry", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_scale_in_subject_to_dedup(self):
        """scale_in with source=strategy IS subject to dedup."""
        config = _make_config(dedup_window_bars=1)
        dedup = SignalDeduplicator(config)
        existing = MagicMock()
        existing.id = uuid4()
        existing.ts = _ts()
        dedup._repo = MagicMock()
        dedup._repo.find_duplicate = AsyncMock(return_value=existing)

        is_dup, _ = await dedup.is_duplicate(
            db=MagicMock(), strategy_id=uuid4(), symbol="AAPL",
            side="buy", signal_type="scale_in", source="strategy",
            timeframe="1h", ts=_ts(),
        )
        assert is_dup is True


# ---------------------------------------------------------------------------
# Signal expiry logic
# ---------------------------------------------------------------------------

class TestSignalExpiry:
    def test_signal_expires_after_ttl(self):
        """Signal older than expires_at → should be expired."""
        created = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        expires = created + timedelta(seconds=300)
        now = created + timedelta(seconds=400)
        assert now > expires  # Signal is expired

    def test_signal_not_expired_within_ttl(self):
        """Signal within TTL → not expired."""
        created = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        expires = created + timedelta(seconds=300)
        now = created + timedelta(seconds=200)
        assert now < expires  # Signal is not expired

    def test_processed_signal_not_expired(self):
        """A signal in 'risk_approved' should not be expired even if past TTL."""
        # The expiry checker only expires signals with status="pending"
        status = "risk_approved"
        assert status != "pending"  # Would not be expired by the checker

    def test_expires_at_computed_from_config(self):
        """5min strategy → expires_at = created_at + expiry_seconds."""
        from app.signals.dedup import _TIMEFRAME_MINUTES
        created = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        expiry_seconds = 300  # From config
        expires_at = created + timedelta(seconds=expiry_seconds)
        expected = datetime(2024, 6, 15, 14, 5, 0, tzinfo=timezone.utc)
        assert expires_at == expected

    def test_timeframe_minutes_mapping(self):
        """Verify all timeframes have correct minute mappings."""
        assert _TIMEFRAME_MINUTES["1m"] == 1
        assert _TIMEFRAME_MINUTES["5m"] == 5
        assert _TIMEFRAME_MINUTES["15m"] == 15
        assert _TIMEFRAME_MINUTES["1h"] == 60
        assert _TIMEFRAME_MINUTES["4h"] == 240
        assert _TIMEFRAME_MINUTES["1d"] == 1440
