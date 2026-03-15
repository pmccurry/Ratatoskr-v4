"""Built-in alert rules seeder."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.alerts.repository import AlertRuleRepository
from app.observability.models import AlertRule

logger = logging.getLogger(__name__)

_rule_repo = AlertRuleRepository()

BUILTIN_RULES = [
    # Critical
    {
        "name": "Global kill switch activated",
        "description": "The global kill switch has been activated, blocking all new entries.",
        "category": "risk",
        "condition_type": "event_match",
        "condition_config": {"event_type": "risk.kill_switch.activated", "window_seconds": 300},
        "severity": "critical",
        "cooldown_seconds": 3600,
        "notification_channels": ["dashboard", "email", "webhook"],
    },
    {
        "name": "Safety monitor consecutive failures",
        "description": "Safety monitor has failed 3+ consecutive times.",
        "category": "system",
        "condition_type": "event_match",
        "condition_config": {"event_type": "strategy.safety_monitor.failure", "window_seconds": 300, "min_count": 3},
        "severity": "critical",
        "cooldown_seconds": 1800,
        "notification_channels": ["dashboard", "email", "webhook"],
    },
    {
        "name": "Catastrophic drawdown",
        "description": "Portfolio drawdown has reached catastrophic levels.",
        "category": "risk",
        "condition_type": "event_match",
        "condition_config": {"event_type": "risk.drawdown.catastrophic", "window_seconds": 600},
        "severity": "critical",
        "cooldown_seconds": 3600,
        "notification_channels": ["dashboard", "email", "webhook"],
    },
    {
        "name": "WebSocket disconnected during market hours",
        "description": "Market data WebSocket has been disconnected for >5 minutes during market hours.",
        "category": "system",
        "condition_type": "absence",
        "condition_config": {"event_type": "market_data.websocket.heartbeat", "window_seconds": 300},
        "severity": "critical",
        "cooldown_seconds": 600,
        "notification_channels": ["dashboard", "email", "webhook"],
    },
    # Error
    {
        "name": "Strategy auto-paused",
        "description": "A strategy has been automatically paused due to errors.",
        "category": "trading",
        "condition_type": "event_match",
        "condition_config": {"event_type": "strategy.auto_paused", "window_seconds": 300},
        "severity": "error",
        "cooldown_seconds": 600,
        "notification_channels": ["dashboard", "email"],
    },
    {
        "name": "Broker API failure with fallback",
        "description": "Broker API call failed, falling back to simulation.",
        "category": "system",
        "condition_type": "event_match",
        "condition_config": {"event_type": "paper_trading.broker.fallback", "window_seconds": 300},
        "severity": "error",
        "cooldown_seconds": 600,
        "notification_channels": ["dashboard", "email"],
    },
    {
        "name": "Daily loss limit breached",
        "description": "Daily loss limit has been breached.",
        "category": "risk",
        "condition_type": "event_match",
        "condition_config": {"event_type": "risk.daily_loss.breached", "window_seconds": 86400},
        "severity": "error",
        "cooldown_seconds": 86400,
        "notification_channels": ["dashboard", "email"],
    },
    {
        "name": "Drawdown limit breached",
        "description": "Portfolio drawdown limit has been breached.",
        "category": "risk",
        "condition_type": "event_match",
        "condition_config": {"event_type": "risk.drawdown.breached", "window_seconds": 86400},
        "severity": "error",
        "cooldown_seconds": 86400,
        "notification_channels": ["dashboard", "email"],
    },
    {
        "name": "Queue backpressure critical",
        "description": "Event queue is >80% full.",
        "category": "system",
        "condition_type": "metric_threshold",
        "condition_config": {"metric_name": "system.event_queue_percent", "threshold": 80, "operator": "gt", "duration_seconds": 120},
        "severity": "error",
        "cooldown_seconds": 300,
        "notification_channels": ["dashboard", "email"],
    },
    # Warning
    {
        "name": "Symbols stale",
        "description": "More than 5 symbols have stale data for >2 minutes.",
        "category": "system",
        "condition_type": "metric_threshold",
        "condition_config": {"metric_name": "market_data.stale_symbols_count", "threshold": 5, "operator": "gt", "duration_seconds": 120},
        "severity": "warning",
        "cooldown_seconds": 300,
        "notification_channels": ["dashboard"],
    },
    {
        "name": "Drawdown approaching limit",
        "description": "Portfolio drawdown is >70% of the configured limit.",
        "category": "risk",
        "condition_type": "metric_threshold",
        "condition_config": {"metric_name": "risk.drawdown_percent_of_limit", "threshold": 70, "operator": "gt", "duration_seconds": 60},
        "severity": "warning",
        "cooldown_seconds": 600,
        "notification_channels": ["dashboard"],
    },
    {
        "name": "Daily loss approaching limit",
        "description": "Daily loss is >70% of the configured limit.",
        "category": "risk",
        "condition_type": "metric_threshold",
        "condition_config": {"metric_name": "risk.daily_loss_percent_of_limit", "threshold": 70, "operator": "gt", "duration_seconds": 60},
        "severity": "warning",
        "cooldown_seconds": 600,
        "notification_channels": ["dashboard"],
    },
    {
        "name": "Signal expired",
        "description": "A signal has expired without being processed.",
        "category": "trading",
        "condition_type": "event_match",
        "condition_config": {"event_type": "signal.expired", "window_seconds": 300},
        "severity": "warning",
        "cooldown_seconds": 300,
        "notification_channels": ["dashboard"],
    },
    {
        "name": "Queue elevated",
        "description": "Event queue is >20% full.",
        "category": "system",
        "condition_type": "metric_threshold",
        "condition_config": {"metric_name": "system.event_queue_percent", "threshold": 20, "operator": "gt", "duration_seconds": 120},
        "severity": "warning",
        "cooldown_seconds": 600,
        "notification_channels": ["dashboard"],
    },
    {
        "name": "Forex pool at capacity",
        "description": "All forex pool accounts are occupied for a currency pair.",
        "category": "trading",
        "condition_type": "event_match",
        "condition_config": {"event_type": "paper_trading.forex_pool.full", "window_seconds": 300},
        "severity": "warning",
        "cooldown_seconds": 300,
        "notification_channels": ["dashboard"],
    },
]


async def seed_alert_rules(db: AsyncSession) -> int:
    """Create built-in alert rules if they don't exist."""
    created = 0

    for rule_data in BUILTIN_RULES:
        existing = await _rule_repo.get_by_name(db, rule_data["name"])
        if existing:
            continue

        rule = AlertRule(**rule_data)
        await _rule_repo.create(db, rule)
        created += 1

    if created > 0:
        logger.info("Seeded %d built-in alert rules", created)

    return created
