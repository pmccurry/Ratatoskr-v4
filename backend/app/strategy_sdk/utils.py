"""Utility helpers for the Strategy SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


_ET = ZoneInfo("America/New_York")
_UTC = timezone.utc


class TimeUtils:
    """Time-related helpers for strategies."""

    def hour_et(self, bar: dict) -> int:
        """Get the hour (0-23) in US/Eastern time for a bar."""
        ts = bar.get("timestamp")
        if ts is None:
            return -1
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_UTC)
        return ts.astimezone(_ET).hour

    def minute_et(self, bar: dict) -> int:
        """Get the minute (0-59) in US/Eastern time for a bar."""
        ts = bar.get("timestamp")
        if ts is None:
            return -1
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_UTC)
        return ts.astimezone(_ET).minute

    def date_et(self, bar: dict):
        """Get the date in US/Eastern time for a bar."""
        ts = bar.get("timestamp")
        if ts is None:
            return None
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_UTC)
        return ts.astimezone(_ET).date()

    def weekday(self, bar: dict) -> int:
        """Get weekday (0=Monday, 6=Sunday) in ET."""
        d = self.date_et(bar)
        return d.weekday() if d else -1

    def is_between_hours(self, bar: dict, start_hour: int, end_hour: int) -> bool:
        """Check if bar falls within a time window (ET hours)."""
        hour = self.hour_et(bar)
        return start_hour <= hour < end_hour


class PipUtils:
    """Pip calculation helpers for forex."""

    JPY_PAIRS = {
        "USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY",
        "NZD_JPY", "CAD_JPY", "CHF_JPY",
    }

    def pip_value(self, symbol: str) -> float:
        """Get the pip value for a symbol (0.0001 for most, 0.01 for JPY)."""
        if symbol in self.JPY_PAIRS or symbol.endswith("_JPY"):
            return 0.01
        return 0.0001

    def to_pips(self, price_diff: float, symbol: str) -> float:
        """Convert a price difference to pips."""
        return abs(price_diff) / self.pip_value(symbol)

    def from_pips(self, pip_count: float, symbol: str) -> float:
        """Convert pips to a price difference."""
        return pip_count * self.pip_value(symbol)

    def candle_body_pct(self, bar: dict) -> float:
        """Calculate candle body as percentage of total range."""
        high = float(bar["high"])
        low = float(bar["low"])
        if high == low:
            return 0.0
        body = abs(float(bar["close"]) - float(bar["open"]))
        return body / (high - low)

    def candle_direction(self, bar: dict) -> str:
        """Return 'bullish', 'bearish', or 'neutral'."""
        if bar["close"] > bar["open"]:
            return "bullish"
        elif bar["close"] < bar["open"]:
            return "bearish"
        return "neutral"
