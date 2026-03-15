"""Alert notification dispatcher."""

import logging
from datetime import timezone

from app.observability.config import ObservabilityConfig
from app.observability.models import AlertInstance, AlertRule

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"warning": 0, "error": 1, "critical": 2}


class NotificationDispatcher:
    """Sends alert notifications through configured channels."""

    def __init__(self, config: ObservabilityConfig):
        self._config = config

    async def dispatch(
        self, alert: AlertInstance, rule: AlertRule
    ) -> list[str]:
        """Send notifications on all configured channels."""
        channels_sent = []

        notification_channels = rule.notification_channels or ["dashboard"]

        for channel in notification_channels:
            try:
                if channel == "dashboard":
                    if await self._send_dashboard(alert):
                        channels_sent.append("dashboard")
                elif channel == "email":
                    if await self._send_email(alert, rule):
                        channels_sent.append("email")
                elif channel == "webhook":
                    if await self._send_webhook(alert, rule):
                        channels_sent.append("webhook")
            except Exception as e:
                logger.error("Notification error (%s): %s", channel, e)

        return channels_sent

    async def _send_dashboard(self, alert: AlertInstance) -> bool:
        """Dashboard notifications are implicit (stored in DB)."""
        return True

    async def _send_email(self, alert: AlertInstance, rule: AlertRule) -> bool:
        """Send email notification (logged for MVP)."""
        if not self._config.alert_email_enabled:
            return False

        min_severity = _SEVERITY_ORDER.get(
            self._config.alert_email_min_severity, 1
        )
        alert_severity = _SEVERITY_ORDER.get(alert.severity, 0)
        if alert_severity < min_severity:
            return False

        recipients = self._config.alert_email_recipients
        logger.info(
            "EMAIL NOTIFICATION (would send): to=%s subject='[%s] %s' body='%s'",
            recipients, alert.severity.upper(), alert.summary,
            alert.details_json,
        )
        return True

    async def _send_webhook(self, alert: AlertInstance, rule: AlertRule) -> bool:
        """Send webhook notification via httpx POST."""
        if not self._config.alert_webhook_enabled:
            return False

        min_severity = _SEVERITY_ORDER.get(
            self._config.alert_webhook_min_severity, 1
        )
        alert_severity = _SEVERITY_ORDER.get(alert.severity, 0)
        if alert_severity < min_severity:
            return False

        url = self._config.alert_webhook_url
        if not url:
            return False

        payload = {
            "severity": alert.severity,
            "alert_name": rule.name,
            "summary": alert.summary,
            "details": alert.details_json,
            "triggered_at": alert.triggered_at.isoformat()
            if alert.triggered_at
            else None,
        }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                if response.status_code < 300:
                    logger.info("Webhook sent to %s (status=%d)", url, response.status_code)
                    return True
                else:
                    logger.warning(
                        "Webhook failed: %s (status=%d)", url, response.status_code
                    )
                    return False
        except Exception as e:
            logger.error("Webhook error: %s", e)
            return False
