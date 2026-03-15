"""Risk evaluation background task — consumes pending signals."""

import asyncio
import logging

from app.risk.config import get_risk_module_config
from app.risk.service import RiskService

logger = logging.getLogger(__name__)


class RiskEvaluator:
    """Background task that periodically evaluates pending signals."""

    def __init__(self, service: RiskService):
        self._service = service
        self._config = get_risk_module_config()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Risk evaluator started (interval=%ds)",
            self._config.evaluation_timeout,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Risk evaluator stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                from app.common.database import get_session_factory

                factory = get_session_factory()
                async with factory() as db:
                    try:
                        result = await self._service.evaluate_pending_signals(db)
                        await db.commit()
                        if result["evaluated"] > 0:
                            logger.info(
                                "Risk evaluation cycle: %d evaluated "
                                "(%d approved, %d rejected, %d modified)",
                                result["evaluated"], result["approved"],
                                result["rejected"], result["modified"],
                            )
                    except Exception:
                        await db.rollback()
                        raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Risk evaluation cycle error: %s", e)

            try:
                await asyncio.sleep(self._config.evaluation_timeout)
            except asyncio.CancelledError:
                break
