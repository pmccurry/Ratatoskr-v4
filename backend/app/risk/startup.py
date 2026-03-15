"""Risk module startup — service lifecycle and singleton."""

import logging

from app.risk.checks import get_risk_checks
from app.risk.evaluator import RiskEvaluator
from app.risk.service import RiskService

logger = logging.getLogger(__name__)

_risk_service: RiskService | None = None
_risk_evaluator: RiskEvaluator | None = None


async def start_risk() -> None:
    """Initialize and start the risk module."""
    global _risk_service, _risk_evaluator

    # Seed risk config defaults if none exist
    from app.common.database import get_session_factory

    factory = get_session_factory()
    async with factory() as db:
        try:
            from app.risk.repository import RiskConfigRepository
            await RiskConfigRepository().seed_defaults(db)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    checks = get_risk_checks()
    _risk_service = RiskService(checks)

    _risk_evaluator = RiskEvaluator(_risk_service)
    await _risk_evaluator.start()

    logger.info("Risk module started (service + evaluator)")


async def stop_risk() -> None:
    """Stop the risk evaluator."""
    global _risk_evaluator

    if _risk_evaluator:
        await _risk_evaluator.stop()

    logger.info("Risk module stopped")


def get_risk_service() -> RiskService:
    """Get the risk service singleton for inter-module use."""
    if _risk_service is None:
        raise RuntimeError("Risk service not initialized — call start_risk() first")
    return _risk_service
