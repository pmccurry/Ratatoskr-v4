"""Signal module startup — expiry checker and service lifecycle."""

import logging

from app.signals.config import get_signal_config
from app.signals.dedup import SignalDeduplicator
from app.signals.expiry import SignalExpiryChecker
from app.signals.service import SignalService

logger = logging.getLogger(__name__)

_expiry_checker: SignalExpiryChecker | None = None
_signal_service: SignalService | None = None


async def start_signals() -> None:
    """Initialize and start the signal module."""
    global _expiry_checker, _signal_service

    config = get_signal_config()
    deduplicator = SignalDeduplicator(config)

    _signal_service = SignalService(config, deduplicator)

    _expiry_checker = SignalExpiryChecker(config)
    await _expiry_checker.start()

    logger.info("Signal module started (service + expiry checker)")


async def stop_signals() -> None:
    """Stop the expiry checker."""
    global _expiry_checker

    if _expiry_checker:
        await _expiry_checker.stop()

    logger.info("Signal module stopped")


def get_signal_service() -> SignalService:
    """Get the signal service singleton for inter-module use."""
    if _signal_service is None:
        raise RuntimeError("Signal service not initialized — call start_signals() first")
    return _signal_service
