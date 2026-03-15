"""Aggregation engine — builds higher-timeframe bars from 1-minute bars.

All aggregations are computed directly from 1m bars (not cascading).
This prevents compounding rounding errors across aggregation levels
(DECISION-013).
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.models import OHLCVBar
from app.market_data.repository import OHLCVBarRepository

logger = logging.getLogger(__name__)

_bar_repo = OHLCVBarRepository()

# Number of 1m bars in each higher timeframe
_TIMEFRAME_MINUTES = {
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


class AggregationEngine:
    """Aggregates 1m bars into higher timeframes.

    Supported aggregations:
      1m -> 5m, 15m, 1h, 4h, 1d

    All aggregations are computed directly from 1m bars (not cascading).
    """

    async def aggregate_window(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        window_start: datetime,
    ) -> OHLCVBar | None:
        """Aggregate a specific timeframe window from 1m bars.

        1. Determine window boundaries for the given timeframe
        2. Fetch all 1m bars within the window
        3. Compute OHLCV from the 1m bars
        4. Upsert the aggregated bar
        """
        minutes = _TIMEFRAME_MINUTES.get(timeframe)
        if not minutes:
            return None

        window_end = self._compute_window_end(window_start, timeframe)

        # Fetch 1m bars within the window
        bars = await _bar_repo.get_bars(
            db, symbol, "1m", limit=minutes, start=window_start, end=window_end
        )

        if not bars:
            return None

        # Sort by timestamp ascending
        bars.sort(key=lambda b: b.ts)

        # Compute aggregated values
        agg_open = bars[0].open
        agg_high = max(b.high for b in bars)
        agg_low = min(b.low for b in bars)
        agg_close = bars[-1].close
        agg_volume = sum(b.volume for b in bars)

        # Determine market from first bar
        market = bars[0].market

        agg_bar = OHLCVBar(
            id=uuid4(),
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            ts=window_start,
            open=agg_open,
            high=agg_high,
            low=agg_low,
            close=agg_close,
            volume=agg_volume,
            source="aggregation",
            is_aggregated=True,
        )

        await _bar_repo.upsert_bars(db, [agg_bar])
        logger.debug(
            "Aggregated %s %s bar at %s from %d 1m bars",
            symbol, timeframe, window_start, len(bars),
        )
        return agg_bar

    def _compute_window_end(self, window_start: datetime, timeframe: str) -> datetime:
        """Compute window end from start and timeframe."""
        from datetime import timedelta

        minutes = _TIMEFRAME_MINUTES[timeframe]
        return window_start + timedelta(minutes=minutes)

    def get_window_start(self, ts: datetime, timeframe: str) -> datetime:
        """Calculate the window start for a timestamp and timeframe.

        Examples:
          ts=10:37, timeframe=5m  -> 10:35
          ts=10:37, timeframe=15m -> 10:30
          ts=10:37, timeframe=1h  -> 10:00
          ts=10:37, timeframe=4h  -> 08:00 (aligned to midnight)
          ts=10:37, timeframe=1d  -> 00:00
        """
        minutes = _TIMEFRAME_MINUTES.get(timeframe, 1)

        if timeframe == "1d":
            return ts.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total minutes since midnight
        total_minutes = ts.hour * 60 + ts.minute
        window_minutes = (total_minutes // minutes) * minutes
        window_hour = window_minutes // 60
        window_minute = window_minutes % 60

        return ts.replace(hour=window_hour, minute=window_minute, second=0, microsecond=0)

    def is_window_complete(self, ts: datetime, timeframe: str) -> bool:
        """Check if the bar at ts completes a higher-timeframe window.

        A 5m window completes at minutes :04, :09, :14, :19, etc.
        (the LAST 1m bar of the window).

        Examples:
          ts=10:04, timeframe=5m  -> True (bar at :04 is last of :00-:04)
          ts=10:03, timeframe=5m  -> False
          ts=10:59, timeframe=1h  -> True
          ts=10:58, timeframe=1h  -> False
        """
        minutes = _TIMEFRAME_MINUTES.get(timeframe, 1)

        if timeframe == "1d":
            # Daily bar completes at 23:59
            return ts.hour == 23 and ts.minute == 59

        # The last bar of a window is at window_start + (minutes - 1) minutes
        total_minutes = ts.hour * 60 + ts.minute
        return (total_minutes + 1) % minutes == 0

    def get_required_timeframes(self) -> list[str]:
        """Return the list of timeframes to aggregate."""
        return ["5m", "15m", "1h", "4h", "1d"]
