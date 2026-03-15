"""Observability module configuration."""

from app.common.config import get_settings


class ObservabilityConfig:
    def __init__(self):
        s = get_settings()
        self.event_queue_max_size = s.event_queue_max_size
        self.event_batch_write_size = s.event_batch_write_size
        self.event_batch_write_interval = s.event_batch_write_interval_sec
        self.event_retention_days = s.event_retention_days
        self.metrics_collection_interval = s.metrics_collection_interval_sec
        self.metrics_retention_days = s.metrics_retention_days
        self.alert_evaluation_interval = s.alert_evaluation_interval_sec
        self.alert_email_enabled = s.alert_email_enabled
        self.alert_email_recipients = s.alert_email_recipients
        self.alert_email_min_severity = s.alert_email_min_severity
        self.alert_webhook_enabled = s.alert_webhook_enabled
        self.alert_webhook_url = s.alert_webhook_url
        self.alert_webhook_min_severity = s.alert_webhook_min_severity
        self.log_level = s.log_level
        self.log_format = s.log_format
