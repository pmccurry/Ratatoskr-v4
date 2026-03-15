"""Observability module SQLAlchemy models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base_model import Base, BaseModel


class AuditEvent(Base):
    """Immutable audit event — no updated_at."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    source_module: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    strategy_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_events_ts", "ts"),
        Index("ix_audit_events_event_type_ts", "event_type", "ts"),
        Index("ix_audit_events_category_ts", "category", "ts"),
        Index("ix_audit_events_severity_ts", "severity", "ts"),
        Index(
            "ix_audit_events_strategy_ts", "strategy_id", "ts",
            postgresql_where="strategy_id IS NOT NULL",
        ),
        Index(
            "ix_audit_events_symbol_ts", "symbol", "ts",
            postgresql_where="symbol IS NOT NULL",
        ),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
    )


class MetricDatapoint(BaseModel):
    __tablename__ = "metric_datapoints"

    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    labels_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_metric_datapoints_name_ts", "metric_name", "ts"),
        Index("ix_metric_datapoints_ts", "ts"),
    )


class AlertRule(BaseModel):
    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(30), nullable=False)
    condition_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    notification_channels: Mapped[list] = mapped_column(JSON, nullable=False)


class AlertInstance(BaseModel):
    __tablename__ = "alert_instances"

    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notifications_sent: Mapped[list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_alert_instances_status_triggered", "status", "triggered_at"),
        Index("ix_alert_instances_rule_triggered", "rule_id", "triggered_at"),
        Index("ix_alert_instances_severity_status", "severity", "status"),
    )
