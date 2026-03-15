"""Observability domain errors."""

from app.common.errors import DomainError


class EventNotFoundError(DomainError):
    def __init__(self, event_id: str = ""):
        super().__init__(
            code="OBSERVABILITY_EVENT_NOT_FOUND",
            message=f"Event not found: {event_id}" if event_id else "Event not found",
        )


class AlertRuleNotFoundError(DomainError):
    def __init__(self, rule_id: str = ""):
        super().__init__(
            code="OBSERVABILITY_ALERT_RULE_NOT_FOUND",
            message=f"Alert rule not found: {rule_id}" if rule_id else "Alert rule not found",
        )


class AlertInstanceNotFoundError(DomainError):
    def __init__(self, alert_id: str = ""):
        super().__init__(
            code="OBSERVABILITY_ALERT_NOT_FOUND",
            message=f"Alert not found: {alert_id}" if alert_id else "Alert not found",
        )
