"""Observability module API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.common.database import get_db
from app.observability.schemas import (
    AlertInstanceResponse,
    AlertRuleResponse,
    AuditEventResponse,
    MetricDatapointResponse,
    PipelineStatusResponse,
    SystemHealthResponse,
    UpdateAlertRuleRequest,
)
from app.observability.service import ObservabilityService

router = APIRouter(
    prefix="/observability",
    tags=["Observability"],
)

_service = ObservabilityService()


# --- Events / Activity Feed ---


@router.get("/events", response_model=dict)
async def list_events(
    category: str | None = Query(None),
    severity: str | None = Query(None),
    event_type: str | None = Query(None, alias="eventType"),
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    symbol: str | None = Query(None),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get events with filters (paginated)."""
    events, total = await _service.get_events(
        db,
        category=category,
        severity=severity,
        event_type=event_type,
        strategy_id=strategy_id,
        symbol=symbol,
        start=date_start,
        end=date_end,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [
            AuditEventResponse.model_validate(e).model_dump(by_alias=True)
            for e in events
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/events/recent", response_model=dict)
async def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
    severity_gte: str | None = Query(None, alias="severityGte"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get last N events (activity feed)."""
    events = await _service.get_recent_events(
        db, limit=limit, category=category, severity_gte=severity_gte,
    )
    return {
        "data": [
            AuditEventResponse.model_validate(e).model_dump(by_alias=True)
            for e in events
        ],
    }


@router.get("/events/{event_id}", response_model=dict)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get event detail."""
    event = await _service.get_event(db, event_id)
    return {
        "data": AuditEventResponse.model_validate(event).model_dump(by_alias=True)
    }


# --- System Health ---


@router.get("/health", response_model=dict)
async def get_system_health(
    user: User = Depends(get_current_user),
):
    """Get overall system health."""
    health = await _service.get_system_health()
    return {
        "data": SystemHealthResponse(**health).model_dump(by_alias=True)
    }


@router.get("/health/pipeline", response_model=dict)
async def get_pipeline_status(
    user: User = Depends(get_current_user),
):
    """Get per-module pipeline status."""
    status = await _service.get_pipeline_status()
    return {
        "data": PipelineStatusResponse(**status).model_dump(by_alias=True)
    }


# --- Metrics ---


@router.get("/metrics", response_model=dict)
async def list_metrics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List available metric names."""
    names = await _service.list_metrics(db)
    return {"data": names}


@router.get("/metrics/{metric_name:path}", response_model=dict)
async def get_metric_timeseries(
    metric_name: str,
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    resolution: str = Query("1m"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get metric time series."""
    datapoints = await _service.get_metric_timeseries(
        db, metric_name, start=date_start, end=date_end, resolution=resolution,
    )
    return {
        "data": [
            MetricDatapointResponse.model_validate(dp).model_dump(by_alias=True)
            for dp in datapoints
        ],
    }


# --- Alerts ---


@router.get("/alerts", response_model=dict)
async def list_alerts(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get alert instances (filtered)."""
    alerts, total = await _service.get_alerts(
        db,
        status=status,
        severity=severity,
        start=date_start,
        end=date_end,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [
            AlertInstanceResponse.model_validate(a).model_dump(by_alias=True)
            for a in alerts
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/alerts/active", response_model=dict)
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get active alerts only."""
    alerts = await _service.get_active_alerts(db)
    return {
        "data": [
            AlertInstanceResponse.model_validate(a).model_dump(by_alias=True)
            for a in alerts
        ],
    }


@router.post("/alerts/{alert_id}/ack", response_model=dict)
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Acknowledge an alert."""
    instance = await _service.acknowledge_alert(db, alert_id, by=str(user.id))
    await db.commit()
    return {
        "data": AlertInstanceResponse.model_validate(instance).model_dump(by_alias=True)
    }


# --- Alert Rules ---


@router.get("/alert-rules", response_model=dict)
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List alert rules."""
    rules = await _service.get_alert_rules(db)
    return {
        "data": [
            AlertRuleResponse.model_validate(r).model_dump(by_alias=True)
            for r in rules
        ],
    }


@router.put("/alert-rules/{rule_id}", response_model=dict)
async def update_alert_rule(
    rule_id: UUID,
    body: UpdateAlertRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Update a rule (admin only)."""
    updates = body.model_dump(exclude_none=True)
    rule = await _service.update_alert_rule(db, rule_id, updates)
    await db.commit()
    return {
        "data": AlertRuleResponse.model_validate(rule).model_dump(by_alias=True)
    }
