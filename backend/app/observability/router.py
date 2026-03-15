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


# --- Background Jobs ---


@router.get("/jobs", response_model=dict)
async def get_background_jobs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get status of background tasks and backfill jobs."""
    from datetime import datetime as dt, timezone

    jobs = []

    # Check background task runners
    task_checks = [
        ("strategy_runner", "app.strategies.startup", "get_runner"),
        ("safety_monitor", "app.strategies.startup", "get_safety_monitor"),
        ("signal_expiry", "app.signals.startup", "get_signal_service"),
        ("risk_evaluator", "app.risk.startup", "get_risk_service"),
        ("paper_trading_consumer", "app.paper_trading.startup", "get_paper_trading_service"),
        ("portfolio_mtm", "app.portfolio.startup", "get_portfolio_service"),
        ("event_writer", "app.observability.startup", "get_event_emitter"),
    ]

    for name, module_path, getter_name in task_checks:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            getter = getattr(mod, getter_name, None)
            service = getter() if getter else None
            jobs.append({
                "name": name,
                "status": "running" if service else "stopped",
                "lastRun": None,
                "nextRun": None,
                "durationMs": None,
            })
        except Exception:
            jobs.append({
                "name": name,
                "status": "error",
                "lastRun": None,
                "nextRun": None,
                "durationMs": None,
            })

    # Backfill job summary from backfill_jobs table
    try:
        from sqlalchemy import func, select, text
        from app.market_data.models import BackfillJob

        completed = (await db.execute(
            select(func.count()).select_from(BackfillJob).where(BackfillJob.status == "completed")
        )).scalar_one()
        failed = (await db.execute(
            select(func.count()).select_from(BackfillJob).where(BackfillJob.status == "failed")
        )).scalar_one()
        running = (await db.execute(
            select(func.count()).select_from(BackfillJob).where(BackfillJob.status == "running")
        )).scalar_one()
        total = (await db.execute(
            select(func.count()).select_from(BackfillJob)
        )).scalar_one()

        backfill_status = "running" if running > 0 else ("completed" if total > 0 else "scheduled")
        jobs.append({
            "name": "historical_backfill",
            "status": backfill_status,
            "lastRun": None,
            "nextRun": None,
            "durationMs": None,
            "progress": {
                "completed": completed,
                "failed": failed,
                "running": running,
                "total": total,
            },
        })
    except Exception:
        jobs.append({
            "name": "historical_backfill",
            "status": "unknown",
            "lastRun": None,
            "nextRun": None,
            "durationMs": None,
        })

    return {"data": jobs}


# --- Database Stats ---


@router.get("/database/stats", response_model=dict)
async def get_database_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get database table statistics and connection pool info."""
    from sqlalchemy import text

    tables = []
    try:
        result = await db.execute(text("""
            SELECT
                relname AS table_name,
                n_live_tup AS row_count,
                pg_total_relation_size(relid) AS size_bytes
            FROM pg_stat_user_tables
            ORDER BY pg_total_relation_size(relid) DESC
        """))
        for row in result.mappings():
            size_bytes = row["size_bytes"] or 0
            if size_bytes > 1_048_576:
                est_size = f"{size_bytes / 1_048_576:.1f} MB"
            elif size_bytes > 1024:
                est_size = f"{size_bytes / 1024:.1f} KB"
            else:
                est_size = f"{size_bytes} B"
            tables.append({
                "tableName": row["table_name"],
                "rowCount": row["row_count"] or 0,
                "estimatedSize": est_size,
            })
    except Exception:
        pass

    total_size = 0
    try:
        result = await db.execute(text("SELECT pg_database_size(current_database())"))
        total_size = result.scalar_one() or 0
    except Exception:
        pass

    return {"data": tables}
