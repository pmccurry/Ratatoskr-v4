"""Signal expiry background job — marks stale pending signals as expired."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.signals.config import SignalConfig
from app.signals.repository import SignalRepository

logger = logging.getLogger(__name__)


class SignalExpiryChecker:
    """Background job that marks stale pending signals as expired.

    Runs every SIGNAL_EXPIRY_CHECK_INTERVAL_SEC.
    """

    def __init__(self, config: SignalConfig):
        self._config = config
        self._repo = SignalRepository()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Signal expiry checker started (interval=%ds)",
            self._config.expiry_check_interval,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Signal expiry checker stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                from app.common.database import get_session_factory

                factory = get_session_factory()
                async with factory() as db:
                    try:
                        count = await self.run_check(db)
                        await db.commit()
                        if count > 0:
                            logger.info("Expired %d stale signals", count)
                    except Exception:
                        await db.rollback()
                        raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Signal expiry check error: %s", e)

            try:
                await asyncio.sleep(self._config.expiry_check_interval)
            except asyncio.CancelledError:
                break

    async def run_check(self, db: AsyncSession) -> int:
        """Run one expiry check cycle. Returns count of expired signals."""
        return await self._repo.expire_stale(db)
