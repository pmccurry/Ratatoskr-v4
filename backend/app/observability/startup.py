"""Observability module startup and shutdown."""

import logging

from app.observability.config import ObservabilityConfig
from app.observability.events.emitter import EventEmitter
from app.observability.metrics.collector import MetricsCollector
from app.observability.alerts.engine import AlertEngine
from app.observability.logging.config import configure_logging

logger = logging.getLogger(__name__)

_event_emitter: EventEmitter | None = None
_metrics_collector: MetricsCollector | None = None
_alert_engine: AlertEngine | None = None


async def start_observability() -> None:
    """Initialize observability module.

    1. Load config and configure logging
    2. Create EventEmitter and start batch writer
    3. Create MetricsCollector and start collection loop
    4. Create AlertEngine and start evaluation loop
    5. Seed built-in alert rules
    """
    global _event_emitter, _metrics_collector, _alert_engine

    config = ObservabilityConfig()

    # Configure application logging first
    configure_logging(config)

    # Start event emitter (batch writer background task)
    _event_emitter = EventEmitter(config)
    await _event_emitter.start()

    # Start metrics collector
    _metrics_collector = MetricsCollector(config)
    await _metrics_collector.start()

    # Start alert engine
    _alert_engine = AlertEngine(config)
    await _alert_engine.start()

    # Seed built-in alert rules
    try:
        from app.common.database import get_session_factory
        from app.observability.alerts.seed import seed_alert_rules

        factory = get_session_factory()
        async with factory() as db:
            await seed_alert_rules(db)
            await db.commit()
    except Exception as e:
        logger.error("Failed to seed alert rules: %s", e)

    logger.info("Observability module started")


async def stop_observability() -> None:
    """Stop all background tasks (emitter, collector, alert engine)."""
    global _event_emitter, _metrics_collector, _alert_engine

    if _alert_engine:
        await _alert_engine.stop()
        _alert_engine = None

    if _metrics_collector:
        await _metrics_collector.stop()
        _metrics_collector = None

    if _event_emitter:
        await _event_emitter.stop()
        _event_emitter = None

    logger.info("Observability module stopped")


def get_event_emitter() -> EventEmitter | None:
    """Get the event emitter for other modules to use."""
    return _event_emitter
