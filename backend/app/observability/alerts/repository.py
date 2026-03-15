"""Alert rule and instance repositories."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.models import AlertInstance, AlertRule


class AlertRuleRepository:
    async def get_all(self, db: AsyncSession) -> list[AlertRule]:
        result = await db.execute(
            select(AlertRule).order_by(AlertRule.severity.asc(), AlertRule.name.asc())
        )
        return list(result.scalars().all())

    async def get_enabled(self, db: AsyncSession) -> list[AlertRule]:
        result = await db.execute(
            select(AlertRule).where(AlertRule.enabled == True).order_by(AlertRule.name.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, rule_id: UUID) -> AlertRule | None:
        result = await db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> AlertRule | None:
        result = await db.execute(
            select(AlertRule).where(AlertRule.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, rule: AlertRule) -> AlertRule:
        db.add(rule)
        await db.flush()
        return rule

    async def update(self, db: AsyncSession, rule: AlertRule) -> AlertRule:
        await db.flush()
        return rule


class AlertInstanceRepository:
    async def create(
        self, db: AsyncSession, instance: AlertInstance
    ) -> AlertInstance:
        db.add(instance)
        await db.flush()
        return instance

    async def get_active(self, db: AsyncSession) -> list[AlertInstance]:
        result = await db.execute(
            select(AlertInstance)
            .where(AlertInstance.status == "active")
            .order_by(AlertInstance.triggered_at.desc())
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        db: AsyncSession,
        status: str | None = None,
        severity: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AlertInstance], int]:
        query = select(AlertInstance)
        count_query = select(func.count()).select_from(AlertInstance)

        filters = []
        if status:
            filters.append(AlertInstance.status == status)
        if severity:
            filters.append(AlertInstance.severity == severity)
        if start:
            filters.append(AlertInstance.triggered_at >= start)
        if end:
            filters.append(AlertInstance.triggered_at <= end)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(AlertInstance.triggered_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        instances = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return instances, total

    async def get_by_id(
        self, db: AsyncSession, instance_id: UUID
    ) -> AlertInstance | None:
        result = await db.execute(
            select(AlertInstance).where(AlertInstance.id == instance_id)
        )
        return result.scalar_one_or_none()

    async def acknowledge(
        self, db: AsyncSession, instance_id: UUID, by: str
    ) -> AlertInstance | None:
        instance = await self.get_by_id(db, instance_id)
        if instance:
            instance.status = "acknowledged"
            instance.acknowledged_at = datetime.now(timezone.utc)
            instance.acknowledged_by = by
            await db.flush()
        return instance

    async def resolve(
        self, db: AsyncSession, instance_id: UUID
    ) -> AlertInstance | None:
        instance = await self.get_by_id(db, instance_id)
        if instance:
            instance.status = "resolved"
            instance.resolved_at = datetime.now(timezone.utc)
            await db.flush()
        return instance

    async def get_active_for_rule(
        self, db: AsyncSession, rule_id: UUID
    ) -> AlertInstance | None:
        result = await db.execute(
            select(AlertInstance).where(
                AlertInstance.rule_id == rule_id,
                AlertInstance.status == "active",
            ).order_by(AlertInstance.triggered_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()
