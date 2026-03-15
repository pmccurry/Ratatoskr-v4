"""Observability module Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    event_type: str
    category: str
    severity: str
    source_module: str
    entity_type: str | None
    entity_id: UUID | None
    strategy_id: UUID | None
    symbol: str | None
    summary: str
    details_json: dict | None
    ts: datetime
    created_at: datetime


class MetricDatapointResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    metric_name: str
    metric_type: str
    value: Decimal
    labels_json: dict | None
    ts: datetime


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    name: str
    description: str
    category: str
    condition_type: str
    condition_config: dict
    severity: str
    enabled: bool
    cooldown_seconds: int
    notification_channels: list
    created_at: datetime


class AlertInstanceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    rule_id: UUID
    severity: str
    summary: str
    details_json: dict | None
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    notifications_sent: list | None


class UpdateAlertRuleRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    enabled: bool | None = None
    cooldown_seconds: int | None = None
    severity: str | None = None


class SystemHealthResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    overall_status: str
    uptime_seconds: int
    modules: dict
    pipeline: dict


class PipelineStatusResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    market_data: dict
    strategies: dict
    signals: dict
    risk: dict
    paper_trading: dict
    portfolio: dict
