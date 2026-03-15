"""Root conftest — shared fixtures available to all test layers."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def make_bars(
    closes: list[float],
    *,
    opens: list[float] | None = None,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[float] | None = None,
) -> list[dict]:
    """Build bar dicts from close prices. Other fields derived if not provided."""
    bars = []
    for i, close in enumerate(closes):
        bars.append({
            "open": Decimal(str(opens[i] if opens else close)),
            "high": Decimal(str(highs[i] if highs else close * 1.01)),
            "low": Decimal(str(lows[i] if lows else close * 0.99)),
            "close": Decimal(str(close)),
            "volume": Decimal(str(volumes[i] if volumes else 1000000)),
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i),
        })
    return bars


def make_trending_bars(start: float, end: float, count: int) -> list[dict]:
    """Build a series of bars with a linear trend from start to end."""
    step = (end - start) / max(count - 1, 1)
    closes = [start + step * i for i in range(count)]
    return make_bars(closes)


def make_flat_bars(price: float, count: int) -> list[dict]:
    """Build a series of bars at a constant price."""
    return make_bars(
        [price] * count,
        opens=[price] * count,
        highs=[price] * count,
        lows=[price] * count,
    )
