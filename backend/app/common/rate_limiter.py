"""In-memory rate limiter for brute force protection."""

from collections import defaultdict
from time import time

from fastapi import HTTPException, Request


class RateLimiter:
    """Simple sliding window rate limiter.

    No Redis dependency — uses in-memory dict per DECISION-004.
    Suitable for single-instance deployments.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time()
        window_start = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


def _get_limiters():
    """Lazy-init limiters from config (called once on first use)."""
    from app.common.config import get_settings
    s = get_settings()
    return {
        "login": RateLimiter(s.auth_login_rate_limit, s.auth_login_rate_window_sec),
        "refresh": RateLimiter(s.auth_refresh_rate_limit, s.auth_refresh_rate_window_sec),
        "password": RateLimiter(s.auth_password_change_rate_limit, s.auth_password_change_rate_window_sec),
    }


_limiters: dict[str, RateLimiter] | None = None


def _get(name: str) -> RateLimiter:
    global _limiters
    if _limiters is None:
        _limiters = _get_limiters()
    return _limiters[name]


async def check_login_rate(request: Request):
    """Rate limit dependency for login endpoint."""
    client_ip = request.client.host if request.client else "unknown"
    if not _get("login").is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many login attempts. Try again later.",
                }
            },
        )


async def check_refresh_rate(request: Request):
    """Rate limit dependency for token refresh endpoint."""
    client_ip = request.client.host if request.client else "unknown"
    if not _get("refresh").is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many refresh attempts. Try again later.",
                }
            },
        )


async def check_password_rate(request: Request):
    """Rate limit dependency for password change endpoint."""
    client_ip = request.client.host if request.client else "unknown"
    if not _get("password").is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many password change attempts. Try again later.",
                }
            },
        )
