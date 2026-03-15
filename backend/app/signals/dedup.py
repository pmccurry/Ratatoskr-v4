"""Signal deduplication logic."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.signals.config import SignalConfig
from app.signals.repository import SignalRepository

logger = logging.getLogger(__name__)

_TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


class SignalDeduplicator:
    """Checks whether a signal is a duplicate of an existing pending/approved signal.

    Dedup rules:
    - Only applies to source="strategy" with signal_type in ("entry", "scale_in")
    - Exit signals are NEVER deduplicated
    - Manual, safety, and system signals are NEVER deduplicated
    - A signal is duplicate if an existing pending/approved signal matches:
      same strategy_id, symbol, side, signal_type, within dedup window
    """

    def __init__(self, config: SignalConfig):
        self._config = config
        self._repo = SignalRepository()

    async def is_duplicate(
        self,
        db: AsyncSession,
        strategy_id: UUID,
        symbol: str,
        side: str,
        signal_type: str,
        source: str,
        timeframe: str,
        ts: datetime,
    ) -> tuple[bool, UUID | None]:
        """Check if a signal is a duplicate.

        Returns (is_duplicate: bool, existing_signal_id: UUID | None)
        """
        if source != "strategy":
            return False, None

        if signal_type in ("exit", "scale_out"):
            return False, None

        if self._config.dedup_window_bars <= 0:
            return False, None

        window_start = self._get_window_start(ts, timeframe, self._config.dedup_window_bars)

        existing = await self._repo.find_duplicate(
            db, strategy_id, symbol, side, signal_type, window_start
        )

        if existing is not None:
            logger.info(
                "Signal deduplicated: %s %s from strategy %s "
                "(duplicate of signal %s from %s)",
                side.upper(), symbol, strategy_id, existing.id, existing.ts,
            )
            return True, existing.id

        return False, None

    def _get_window_start(
        self, ts: datetime, timeframe: str, window_bars: int
    ) -> datetime:
        """Calculate the dedup window start timestamp."""
        minutes = _TIMEFRAME_MINUTES.get(timeframe, 1)
        return ts - timedelta(minutes=minutes * window_bars)
