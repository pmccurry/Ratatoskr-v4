"""Signal module configuration."""

from app.common.config import get_settings

_TIMEFRAME_EXPIRY_SECONDS: dict[str, int] = {
    "1m": 120,
    "5m": 600,
    "15m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


class SignalConfig:
    """Signal module configuration.

    Extracts signal-specific settings from the global Settings object.
    """

    def __init__(self):
        s = get_settings()
        self.dedup_window_bars = s.signal_dedup_window_bars
        self.default_expiry_seconds = s.signal_expiry_seconds
        self.expiry_check_interval = s.signal_expiry_check_interval_sec

    def get_expiry_duration(self, timeframe: str) -> int:
        """Get expiry duration in seconds based on strategy timeframe.

        1m → 120s, 5m → 600s, 15m → 1800s, 1h → 3600s, 4h → 14400s
        Falls back to default_expiry_seconds if timeframe unknown.
        """
        return _TIMEFRAME_EXPIRY_SECONDS.get(timeframe, self.default_expiry_seconds)


def get_signal_config() -> SignalConfig:
    """Create and return a SignalConfig instance."""
    return SignalConfig()
