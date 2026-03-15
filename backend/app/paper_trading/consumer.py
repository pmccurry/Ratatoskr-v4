"""Order consumer — background task that processes risk-approved signals."""

import asyncio
import logging

from app.common.database import get_session_factory

logger = logging.getLogger(__name__)


class OrderConsumer:
    """Background task that periodically consumes risk-approved signals.

    Runs frequently (every 2 seconds) to minimize latency between
    risk approval and order execution.
    """

    def __init__(self, service: object):
        self._service = service
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the consumer loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Order consumer started (interval=2s)")

    async def stop(self) -> None:
        """Stop the consumer loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Order consumer stopped")

    async def _run_loop(self) -> None:
        """Periodically call service.process_approved_signals()."""
        factory = get_session_factory()
        while self._running:
            try:
                async with factory() as db:
                    result = await self._service.process_approved_signals(db)
                    await db.commit()
                    if result["processed"] > 0:
                        logger.info(
                            "Order consumer cycle: processed=%d filled=%d rejected=%d",
                            result["processed"],
                            result["filled"],
                            result["rejected"],
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Order consumer error: %s", e)

            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
