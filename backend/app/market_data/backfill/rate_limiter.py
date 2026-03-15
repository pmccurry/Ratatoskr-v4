"""Reusable async rate limiter for broker API calls."""

import asyncio
import time


class RateLimiter:
    """Enforces a maximum number of requests per minute.

    Uses a sliding window approach. acquire() blocks until
    a request slot is available.
    """

    def __init__(self, max_requests_per_minute: int):
        self._max_rpm = max_requests_per_minute
        self._window_sec = 60.0
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        async with self._lock:
            now = time.monotonic()
            # Remove timestamps older than the window
            cutoff = now - self._window_sec
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self._max_rpm:
                # Wait until the oldest request in the window expires
                wait_time = self._timestamps[0] - cutoff
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                # Clean up again after sleeping
                now = time.monotonic()
                cutoff = now - self._window_sec
                self._timestamps = [t for t in self._timestamps if t > cutoff]

            self._timestamps.append(time.monotonic())


class NoOpRateLimiter(RateLimiter):
    """A no-op rate limiter for testing."""

    def __init__(self):
        super().__init__(max_requests_per_minute=999999)

    async def acquire(self) -> None:
        pass
