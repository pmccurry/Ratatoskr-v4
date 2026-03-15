"""In-memory cache for option chain snapshots."""

import time


class OptionChainCache:
    """In-memory cache for option chain snapshots.

    TTL-based. If a cached chain is older than ttl_sec,
    it's considered stale and will be re-fetched.
    """

    def __init__(self, ttl_sec: int = 60):
        self._ttl_sec = ttl_sec
        self._cache: dict[str, tuple[float, dict]] = {}

    def get(self, underlying_symbol: str) -> dict | None:
        """Get cached chain if fresh, None if stale/missing."""
        entry = self._cache.get(underlying_symbol)
        if entry is None:
            return None
        cached_at, chain = entry
        if time.monotonic() - cached_at > self._ttl_sec:
            del self._cache[underlying_symbol]
            return None
        return chain

    def set(self, underlying_symbol: str, chain: dict) -> None:
        """Cache a chain snapshot."""
        self._cache[underlying_symbol] = (time.monotonic(), chain)

    def clear(self, underlying_symbol: str | None = None) -> None:
        """Clear one or all cached chains."""
        if underlying_symbol is None:
            self._cache.clear()
        else:
            self._cache.pop(underlying_symbol, None)
