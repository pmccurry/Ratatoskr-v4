"""Non-blocking event emission service."""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.observability.config import ObservabilityConfig

logger = logging.getLogger(__name__)

# Severity ordering for overflow decisions
_SEVERITY_ORDER = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}


class EventEmitter:
    """Non-blocking event emission service.

    Modules call emit() which puts the event on an async queue.
    A background batch writer drains the queue and writes to the database.
    """

    def __init__(self, config: ObservabilityConfig):
        self._queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.event_queue_max_size
        )
        self._config = config
        self._running = False
        self._task: asyncio.Task | None = None
        self._dropped_count = 0

    async def emit(
        self,
        event_type: str,
        category: str,
        severity: str,
        source_module: str,
        summary: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        details: dict | None = None,
        ts: datetime | None = None,
    ) -> None:
        """Emit an event (non-blocking).

        If queue is full: drop debug/info events, NEVER drop warning+.
        """
        event_data = {
            "event_type": event_type,
            "category": category,
            "severity": severity,
            "source_module": source_module,
            "summary": summary,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "details_json": details,
            "ts": ts or datetime.now(timezone.utc),
        }

        try:
            self._queue.put_nowait(event_data)
        except asyncio.QueueFull:
            if self._handle_overflow(severity):
                # Event dropped
                self._dropped_count += 1
                if self._dropped_count % 100 == 1:
                    logger.warning(
                        "Event queue full — dropped %d events (latest: %s)",
                        self._dropped_count, event_type,
                    )
                return
            # Warning+ events: block briefly to ensure delivery
            try:
                await asyncio.wait_for(
                    self._queue.put(event_data), timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Failed to enqueue critical event %s after timeout",
                    event_type,
                )

    async def start(self) -> None:
        """Start the batch writer background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._batch_writer())
        logger.info("Event emitter started (queue_max=%d, batch_size=%d)",
                     self._config.event_queue_max_size,
                     self._config.event_batch_write_size)

    async def stop(self) -> None:
        """Flush remaining events and stop."""
        self._running = False
        if self._task:
            # Drain remaining events
            await self._flush_remaining()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Event emitter stopped (dropped_total=%d)", self._dropped_count)

    async def _batch_writer(self) -> None:
        """Background task: drain queue, write in batches."""
        from app.common.database import get_session_factory

        factory = get_session_factory()
        batch: list[dict] = []

        while self._running:
            try:
                # Wait for first item or interval
                try:
                    item = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self._config.event_batch_write_interval,
                    )
                    batch.append(item)
                except asyncio.TimeoutError:
                    pass

                # Drain up to batch_size
                while len(batch) < self._config.event_batch_write_size:
                    try:
                        item = self._queue.get_nowait()
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break

                # Write batch if non-empty
                if batch:
                    try:
                        async with factory() as db:
                            from app.observability.events.repository import AuditEventRepository
                            repo = AuditEventRepository()
                            from app.observability.models import AuditEvent
                            events = [AuditEvent(**data) for data in batch]
                            await repo.create_batch(db, events)
                            await db.commit()
                    except Exception as e:
                        logger.error("Failed to write %d events: %s", len(batch), e)
                    batch = []

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Batch writer error: %s", e)
                batch = []

    async def _flush_remaining(self) -> None:
        """Flush any remaining events in the queue."""
        from app.common.database import get_session_factory

        remaining: list[dict] = []
        while not self._queue.empty():
            try:
                remaining.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if remaining:
            try:
                factory = get_session_factory()
                async with factory() as db:
                    from app.observability.events.repository import AuditEventRepository
                    from app.observability.models import AuditEvent
                    repo = AuditEventRepository()
                    events = [AuditEvent(**data) for data in remaining]
                    await repo.create_batch(db, events)
                    await db.commit()
                    logger.info("Flushed %d remaining events", len(remaining))
            except Exception as e:
                logger.error("Failed to flush %d events: %s", len(remaining), e)

    def _handle_overflow(self, severity: str) -> bool:
        """Handle queue overflow.

        Returns True if event should be dropped.
        Drop order: debug first, then info. Never drop warning+.
        """
        sev_level = _SEVERITY_ORDER.get(severity, 0)
        # Never drop warning (2) or above
        return sev_level < 2

    @property
    def queue_depth(self) -> int:
        """Current queue depth."""
        return self._queue.qsize()

    @property
    def queue_capacity(self) -> int:
        """Max queue size."""
        return self._config.event_queue_max_size

    @property
    def dropped_count(self) -> int:
        """Total events dropped due to overflow."""
        return self._dropped_count

    async def cleanup_expired_events(self, db) -> int:
        """Delete events older than EVENT_RETENTION_DAYS."""
        from app.observability.events.repository import AuditEventRepository
        repo = AuditEventRepository()
        return await repo.cleanup_old(db, self._config.event_retention_days)
