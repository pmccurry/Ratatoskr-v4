"""Alert evaluation engine."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.alerts.repository import (
    AlertInstanceRepository,
    AlertRuleRepository,
)
from app.observability.config import ObservabilityConfig
from app.observability.models import AlertInstance

logger = logging.getLogger(__name__)

_rule_repo = AlertRuleRepository()
_instance_repo = AlertInstanceRepository()


class AlertEngine:
    """Evaluates alert rules against events and metrics."""

    def __init__(self, config: ObservabilityConfig):
        self._config = config
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Alert engine started (interval=%ds)",
            self._config.alert_evaluation_interval,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Alert engine stopped")

    async def _run_loop(self) -> None:
        from app.common.database import get_session_factory

        factory = get_session_factory()
        while self._running:
            try:
                async with factory() as db:
                    triggered = await self.evaluate_cycle(db)
                    await db.commit()
                    if triggered > 0:
                        logger.info("Alert evaluation: %d new alerts", triggered)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Alert evaluation error: %s", e)

            try:
                await asyncio.sleep(self._config.alert_evaluation_interval)
            except asyncio.CancelledError:
                break

    async def evaluate_cycle(self, db: AsyncSession) -> int:
        """Run one evaluation cycle."""
        rules = await _rule_repo.get_enabled(db)
        triggered = 0

        for rule in rules:
            try:
                condition_met = await self._evaluate_condition(
                    db, rule.condition_type, rule.condition_config
                )

                active_instance = await _instance_repo.get_active_for_rule(
                    db, rule.id
                )

                if condition_met:
                    if active_instance:
                        # Check cooldown
                        cooldown_elapsed = (
                            datetime.now(timezone.utc) - active_instance.triggered_at
                        ).total_seconds()
                        if cooldown_elapsed < rule.cooldown_seconds:
                            continue

                    # Create new alert instance
                    now = datetime.now(timezone.utc)
                    instance = AlertInstance(
                        rule_id=rule.id,
                        severity=rule.severity,
                        summary=f"🚨 {rule.name}",
                        details_json={
                            "description": rule.description,
                            "condition_type": rule.condition_type,
                            "condition_config": rule.condition_config,
                        },
                        status="active",
                        triggered_at=now,
                    )
                    await _instance_repo.create(db, instance)

                    # Dispatch notifications
                    try:
                        from app.observability.alerts.notifications import (
                            NotificationDispatcher,
                        )
                        dispatcher = NotificationDispatcher(self._config)
                        channels = await dispatcher.dispatch(instance, rule)
                        instance.notifications_sent = channels
                    except Exception as e:
                        logger.error("Notification dispatch error: %s", e)

                    triggered += 1

                elif active_instance and not condition_met:
                    # Auto-resolve
                    await _instance_repo.resolve(db, active_instance.id)

            except Exception as e:
                logger.error("Error evaluating rule %s: %s", rule.name, e)

        return triggered

    async def _evaluate_condition(
        self, db: AsyncSession, condition_type: str, config: dict
    ) -> bool:
        if condition_type == "event_match":
            return await self._evaluate_event_match(db, config)
        elif condition_type == "metric_threshold":
            return await self._evaluate_metric_threshold(db, config)
        elif condition_type == "absence":
            return await self._evaluate_absence(db, config)
        return False

    async def _evaluate_event_match(self, db: AsyncSession, config: dict) -> bool:
        """Check if a matching event occurred recently."""
        from app.observability.models import AuditEvent
        from sqlalchemy import select, func

        event_type = config.get("event_type")
        window_seconds = config.get("window_seconds", 300)
        min_count = config.get("min_count", 1)

        if not event_type:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        result = await db.execute(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.event_type == event_type,
                AuditEvent.ts >= cutoff,
            )
        )
        count = result.scalar_one()
        return count >= min_count

    async def _evaluate_metric_threshold(
        self, db: AsyncSession, config: dict
    ) -> bool:
        """Check if a metric exceeds threshold for duration."""
        from app.observability.metrics.repository import MetricDatapointRepository

        metric_name = config.get("metric_name")
        threshold = config.get("threshold")
        operator = config.get("operator", "gt")  # gt | lt | gte | lte
        duration_seconds = config.get("duration_seconds", 60)

        if not metric_name or threshold is None:
            return False

        from decimal import Decimal
        threshold_val = Decimal(str(threshold))

        repo = MetricDatapointRepository()
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds)

        from sqlalchemy import select
        from app.observability.models import MetricDatapoint
        result = await db.execute(
            select(MetricDatapoint)
            .where(
                MetricDatapoint.metric_name == metric_name,
                MetricDatapoint.ts >= cutoff,
            )
            .order_by(MetricDatapoint.ts.desc())
        )
        datapoints = list(result.scalars().all())

        if not datapoints:
            return False

        # Check if ALL recent datapoints exceed threshold
        for dp in datapoints:
            if operator == "gt" and dp.value <= threshold_val:
                return False
            elif operator == "lt" and dp.value >= threshold_val:
                return False
            elif operator == "gte" and dp.value < threshold_val:
                return False
            elif operator == "lte" and dp.value > threshold_val:
                return False

        return True

    async def _evaluate_absence(self, db: AsyncSession, config: dict) -> bool:
        """Check if an expected event is missing."""
        from app.observability.models import AuditEvent
        from sqlalchemy import select, func

        event_type = config.get("event_type")
        window_seconds = config.get("window_seconds", 300)

        if not event_type:
            return False

        # For WebSocket heartbeat absence, suppress outside market hours
        # and when no symbols are subscribed
        if event_type == "market_data.websocket.heartbeat":
            if not self._is_us_market_hours():
                return False
            try:
                from app.market_data.startup import get_ws_manager
                ws_mgr = get_ws_manager()
                if ws_mgr:
                    health = ws_mgr.get_health()
                    total_symbols = sum(
                        h.get("subscribedSymbols", 0) for h in health.values()
                    )
                    if total_symbols == 0:
                        return False
            except Exception:
                pass  # If we can't check, proceed with normal evaluation

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        result = await db.execute(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.event_type == event_type,
                AuditEvent.ts >= cutoff,
            )
        )
        count = result.scalar_one()
        return count == 0

    @staticmethod
    def _is_us_market_hours() -> bool:
        """Check if US equity market is currently open (Mon-Fri 9:30 AM - 4:00 PM ET)."""
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
        now_et = datetime.now(ZoneInfo("America/New_York"))
        if now_et.weekday() >= 5:  # Saturday/Sunday
            return False
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now_et <= market_close
