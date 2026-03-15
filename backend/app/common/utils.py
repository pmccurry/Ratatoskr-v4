"""Shared utility functions."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC datetime, timezone-aware."""
    return datetime.now(UTC)
