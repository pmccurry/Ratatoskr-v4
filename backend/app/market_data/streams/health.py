"""Connection health tracking and monitoring."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.config import MarketDataConfig
from app.market_data.repository import BackfillJobRepository, OHLCVBarRepository, WatchlistRepository

if TYPE_CHECKING:
    from app.market_data.streams.manager import WebSocketManager

logger = logging.getLogger(__name__)

_bar_repo = OHLCVBarRepository()
_watchlist_repo = WatchlistRepository()
_backfill_repo = BackfillJobRepository()


@dataclass
class ConnectionHealth:
    """Per-broker connection health state."""

    broker: str
    status: str = "disconnected"  # connected | disconnected | reconnecting
    connected_since: datetime | None = None
    last_message_at: datetime | None = None
    subscribed_symbols: int = 0
    reconnect_attempts: int = 0
    last_disconnect_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "broker": self.broker,
            "status": self.status,
            "connectedSince": self.connected_since.isoformat() if self.connected_since else None,
            "lastMessageAt": self.last_message_at.isoformat() if self.last_message_at else None,
            "subscribedSymbols": self.subscribed_symbols,
            "reconnectAttempts": self.reconnect_attempts,
            "lastDisconnectAt": self.last_disconnect_at.isoformat() if self.last_disconnect_at else None,
        }


class HealthMonitor:
    """Monitors market data health.

    Runs as a periodic background task checking:
    - Connection status per broker
    - Data freshness per symbol (is the latest bar recent enough?)
    - Queue depth (is the bar processing queue backing up?)
    """

    def __init__(
        self,
        ws_manager: WebSocketManager,
        bar_queue: asyncio.Queue,
        config: MarketDataConfig,
    ):
        self._ws_manager = ws_manager
        self._bar_queue = bar_queue
        self._config = config
        self._task: asyncio.Task | None = None
        self._stale_symbols: list[str] = []
        self._running = False

    async def start(self) -> None:
        """Start the health check loop."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("Health monitor started (interval=%ds)", self._config.health_check_interval)

    async def stop(self) -> None:
        """Stop the health check loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def get_health_status(self, db: AsyncSession) -> dict:
        """Return complete health report."""
        connections = self._ws_manager.get_health()
        stale = await self._check_stale_symbols(db)
        queue_depth = self._bar_queue.qsize()
        queue_capacity = self._config.ws_bar_queue_max_size
        queue_pct = (queue_depth / queue_capacity * 100) if queue_capacity > 0 else 0

        # Queue status
        if queue_pct >= self._config.queue_critical_percent:
            queue_status = "critical"
        elif queue_pct >= self._config.queue_warn_percent:
            queue_status = "warning"
        else:
            queue_status = "healthy"

        # Backfill status
        pending_jobs = await _backfill_repo.get_all(db, status="pending")
        running_jobs = await _backfill_repo.get_all(db, status="running")
        failed_jobs = await _backfill_repo.get_all(db, status="failed")

        # Overall status
        all_disconnected = all(
            h.get("status") == "disconnected" for h in connections.values()
        ) if connections else True
        any_disconnected = any(
            h.get("status") != "connected" for h in connections.values()
        ) if connections else True

        if all_disconnected or queue_status == "critical":
            overall = "unhealthy"
        elif any_disconnected or stale or queue_status == "warning":
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "overall_status": overall,
            "connections": connections,
            "stale_symbols": stale,
            "write_pipeline": {
                "queue_depth": queue_depth,
                "queue_capacity": queue_capacity,
                "queue_utilization_percent": round(queue_pct, 1),
                "status": queue_status,
            },
            "backfill": {
                "pending_jobs": len(pending_jobs),
                "running_jobs": len(running_jobs),
                "failed_jobs": len(failed_jobs),
            },
        }

    async def _check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            try:
                await asyncio.sleep(self._config.health_check_interval)
            except asyncio.CancelledError:
                break

    async def _check_stale_symbols(self, db: AsyncSession) -> list[str]:
        """Find symbols where the latest bar is older than the stale threshold.

        Only check during approximate market hours for equities.
        Forex is 24/5 so always check (except weekends).
        """
        now = datetime.now(timezone.utc)
        stale = []

        watchlist = await _watchlist_repo.get_active(db)
        for entry in watchlist:
            # Skip weekend checks for forex
            if entry.market == "forex" and now.weekday() >= 5:
                continue

            # Skip non-market-hours for equities (rough check: UTC 13:30-20:00 is US market)
            if entry.market == "equities":
                if now.weekday() >= 5:
                    continue
                if now.hour < 13 or now.hour >= 21:
                    continue

            latest_ts = await _bar_repo.get_latest_timestamp(db, entry.symbol, "1m")
            if latest_ts is None:
                stale.append(entry.symbol)
                continue

            age_sec = (now - latest_ts).total_seconds()
            if age_sec > self._config.stale_threshold:
                stale.append(entry.symbol)

        return stale
