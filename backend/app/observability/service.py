"""Observability service — main interface for queries and management."""

import logging
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.alerts.repository import (
    AlertInstanceRepository,
    AlertRuleRepository,
)
from app.observability.errors import (
    AlertInstanceNotFoundError,
    AlertRuleNotFoundError,
    EventNotFoundError,
)
from app.observability.events.repository import AuditEventRepository
from app.observability.metrics.repository import MetricDatapointRepository
from app.observability.models import AlertInstance, AlertRule, AuditEvent

logger = logging.getLogger(__name__)

_event_repo = AuditEventRepository()
_metric_repo = MetricDatapointRepository()
_rule_repo = AlertRuleRepository()
_instance_repo = AlertInstanceRepository()

_START_TIME = time.time()


class ObservabilityService:
    """Main service for observability queries and management."""

    # --- Events ---

    async def get_events(
        self, db: AsyncSession, **filters
    ) -> tuple[list[AuditEvent], int]:
        return await _event_repo.get_filtered(db, **filters)

    async def get_recent_events(
        self, db: AsyncSession, limit: int = 50, **filters
    ) -> list[AuditEvent]:
        return await _event_repo.get_recent(db, limit=limit, **filters)

    async def get_event(
        self, db: AsyncSession, event_id: UUID
    ) -> AuditEvent:
        event = await _event_repo.get_by_id(db, event_id)
        if not event:
            raise EventNotFoundError(str(event_id))
        return event

    # --- System Health ---

    async def get_system_health(self) -> dict:
        uptime = int(time.time() - _START_TIME)

        modules = {}
        pipeline = {}

        # Check each module's availability
        module_checks = [
            ("market_data", "app.market_data.startup", "get_market_data_service"),
            ("strategies", "app.strategies.startup", "get_strategy_service"),
            ("signals", "app.signals.startup", "get_signal_service"),
            ("risk", "app.risk.startup", "get_risk_service"),
            ("paper_trading", "app.paper_trading.startup", "get_paper_trading_service"),
            ("portfolio", "app.portfolio.startup", "get_portfolio_service"),
        ]

        for name, module_path, getter_name in module_checks:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                getter = getattr(mod, getter_name, None)
                if getter:
                    service = getter()
                    modules[name] = {
                        "status": "running" if service else "stopped",
                    }
                else:
                    modules[name] = {"status": "unknown"}
            except Exception:
                modules[name] = {"status": "error"}

            pipeline[name] = modules.get(name, {}).get("status", "unknown")

        # Determine overall status
        statuses = [m.get("status") for m in modules.values()]
        if all(s == "running" for s in statuses):
            overall = "healthy"
        elif any(s == "error" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "overall_status": overall,
            "uptime_seconds": uptime,
            "modules": modules,
            "pipeline": pipeline,
        }

    async def get_pipeline_status(self) -> dict:
        health = await self.get_system_health()
        return {
            "market_data": health["modules"].get("market_data", {}),
            "strategies": health["modules"].get("strategies", {}),
            "signals": health["modules"].get("signals", {}),
            "risk": health["modules"].get("risk", {}),
            "paper_trading": health["modules"].get("paper_trading", {}),
            "portfolio": health["modules"].get("portfolio", {}),
        }

    # --- Metrics ---

    async def list_metrics(self, db: AsyncSession) -> list[str]:
        return await _metric_repo.list_metric_names(db)

    async def get_metric_timeseries(
        self, db: AsyncSession, metric_name: str, **filters
    ) -> list:
        return await _metric_repo.get_timeseries(db, metric_name, **filters)

    # --- Alerts ---

    async def get_alerts(
        self, db: AsyncSession, **filters
    ) -> tuple[list[AlertInstance], int]:
        return await _instance_repo.get_filtered(db, **filters)

    async def get_active_alerts(
        self, db: AsyncSession
    ) -> list[AlertInstance]:
        return await _instance_repo.get_active(db)

    async def acknowledge_alert(
        self, db: AsyncSession, alert_id: UUID, by: str
    ) -> AlertInstance:
        instance = await _instance_repo.acknowledge(db, alert_id, by)
        if not instance:
            raise AlertInstanceNotFoundError(str(alert_id))
        return instance

    async def get_alert_rules(
        self, db: AsyncSession
    ) -> list[AlertRule]:
        return await _rule_repo.get_all(db)

    async def update_alert_rule(
        self, db: AsyncSession, rule_id: UUID, updates: dict
    ) -> AlertRule:
        rule = await _rule_repo.get_by_id(db, rule_id)
        if not rule:
            raise AlertRuleNotFoundError(str(rule_id))

        if "enabled" in updates and updates["enabled"] is not None:
            rule.enabled = updates["enabled"]
        if "cooldown_seconds" in updates and updates["cooldown_seconds"] is not None:
            rule.cooldown_seconds = updates["cooldown_seconds"]
        if "severity" in updates and updates["severity"] is not None:
            rule.severity = updates["severity"]

        return await _rule_repo.update(db, rule)
