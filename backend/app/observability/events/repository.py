"""Audit event repository."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.models import AuditEvent


class AuditEventRepository:
    async def create_batch(
        self, db: AsyncSession, events: list[AuditEvent]
    ) -> int:
        """Write a batch of events."""
        db.add_all(events)
        await db.flush()
        return len(events)

    async def get_by_id(
        self, db: AsyncSession, event_id: UUID
    ) -> AuditEvent | None:
        result = await db.execute(
            select(AuditEvent).where(AuditEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        db: AsyncSession,
        category: str | None = None,
        severity: str | None = None,
        event_type: str | None = None,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditEvent], int]:
        query = select(AuditEvent)
        count_query = select(func.count()).select_from(AuditEvent)

        filters = []
        if category:
            filters.append(AuditEvent.category == category)
        if severity:
            filters.append(AuditEvent.severity == severity)
        if event_type:
            filters.append(AuditEvent.event_type == event_type)
        if strategy_id:
            filters.append(AuditEvent.strategy_id == strategy_id)
        if symbol:
            filters.append(AuditEvent.symbol == symbol)
        if start:
            filters.append(AuditEvent.ts >= start)
        if end:
            filters.append(AuditEvent.ts <= end)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(AuditEvent.ts.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        events = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return events, total

    async def get_recent(
        self,
        db: AsyncSession,
        limit: int = 50,
        category: str | None = None,
        severity_gte: str | None = None,
    ) -> list[AuditEvent]:
        """Get recent events, optionally filtered."""
        query = select(AuditEvent)

        if category:
            query = query.where(AuditEvent.category == category)
        if severity_gte:
            severity_order = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}
            min_level = severity_order.get(severity_gte, 0)
            allowed = [s for s, l in severity_order.items() if l >= min_level]
            query = query.where(AuditEvent.severity.in_(allowed))

        query = query.order_by(AuditEvent.ts.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def cleanup_old(
        self, db: AsyncSession, retention_days: int
    ) -> int:
        """Delete events older than retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        result = await db.execute(
            delete(AuditEvent).where(AuditEvent.ts < cutoff)
        )
        return result.rowcount
