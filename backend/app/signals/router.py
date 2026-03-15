"""Signal module API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.signals.schemas import SignalQueryParams, SignalResponse, SignalStatsResponse
from app.signals.startup import get_signal_service

router = APIRouter(
    prefix="/signals",
    tags=["Signals"],
)


@router.get("", response_model=dict)
async def list_signals(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    symbol: str | None = Query(None),
    status: str | None = Query(None),
    signal_type: str | None = Query(None, alias="signalType"),
    source: str | None = Query(None),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List signals with filters, enforcing user ownership."""
    service = get_signal_service()
    signals, total = await service.list_signals(
        db,
        user_id=user.id,
        strategy_id=strategy_id,
        symbol=symbol,
        status=status,
        signal_type=signal_type,
        source=source,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [SignalResponse.model_validate(s).model_dump(by_alias=True) for s in signals],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/recent", response_model=list[dict])
async def get_recent_signals(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get recent signals across all of user's strategies."""
    service = get_signal_service()
    signals = await service.get_recent(db, user_id=user.id, limit=limit)
    return {
        "data": [SignalResponse.model_validate(s).model_dump(by_alias=True) for s in signals],
    }


@router.get("/stats", response_model=dict)
async def get_signal_stats(
    strategy_id: UUID | None = Query(None, alias="strategyId"),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get signal analytics summary."""
    service = get_signal_service()
    stats = await service.get_stats(
        db, user_id=user.id, strategy_id=strategy_id,
        date_start=date_start, date_end=date_end,
    )
    return {"data": SignalStatsResponse(**stats).model_dump(by_alias=True)}


@router.get("/{signal_id}", response_model=dict)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a signal by ID."""
    service = get_signal_service()
    signal = await service.get_signal(db, signal_id, user.id)
    return {"data": SignalResponse.model_validate(signal).model_dump(by_alias=True)}


@router.post("/{signal_id}/cancel", response_model=dict)
async def cancel_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel a pending signal."""
    service = get_signal_service()
    signal = await service.cancel_signal(db, signal_id, user.id)
    return {"data": SignalResponse.model_validate(signal).model_dump(by_alias=True)}


@router.get("/{signal_id}/trace", response_model=dict)
async def get_signal_trace(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the full audit event chain for a signal.

    Returns all events related to this signal in chronological order,
    including: signal creation, risk evaluation, order creation, fill,
    and position updates.
    """
    from sqlalchemy import or_, select

    from app.observability.models import AuditEvent
    from app.paper_trading.models import PaperFill, PaperOrder
    from app.risk.models import RiskDecision
    from app.signals.models import Signal

    # Verify signal exists and belongs to user
    service = get_signal_service()
    signal = await service.get_signal(db, signal_id, user.id)

    # Collect related entity IDs
    entity_ids = [signal_id]

    # Find risk decision for this signal
    risk_result = await db.execute(
        select(RiskDecision.id).where(RiskDecision.signal_id == signal_id)
    )
    risk_id = risk_result.scalar_one_or_none()
    if risk_id:
        entity_ids.append(risk_id)

    # Find order for this signal
    order_result = await db.execute(
        select(PaperOrder.id).where(PaperOrder.signal_id == signal_id)
    )
    order_id = order_result.scalar_one_or_none()
    if order_id:
        entity_ids.append(order_id)

        # Find fills for the order
        fill_result = await db.execute(
            select(PaperFill.id).where(PaperFill.order_id == order_id)
        )
        fill_ids = [row[0] for row in fill_result.all()]
        entity_ids.extend(fill_ids)

    # Query audit events matching any of these entity IDs
    events_query = (
        select(AuditEvent)
        .where(AuditEvent.entity_id.in_(entity_ids))
        .order_by(AuditEvent.ts.asc())
    )
    events_result = await db.execute(events_query)
    events = list(events_result.scalars().all())

    # Calculate duration
    duration = None
    if len(events) >= 2:
        elapsed = (events[-1].ts - events[0].ts).total_seconds()
        duration = f"{elapsed:.1f}s"

    return {
        "data": {
            "signalId": str(signal_id),
            "events": [
                {
                    "timestamp": e.ts.isoformat(),
                    "eventType": e.event_type,
                    "category": e.category,
                    "severity": e.severity,
                    "summary": e.summary,
                    "payload": e.details_json or {},
                }
                for e in events
            ],
            "finalStatus": signal.status,
            "duration": duration,
        },
    }
