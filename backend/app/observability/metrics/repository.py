"""Metric datapoint repository."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.models import MetricDatapoint


class MetricDatapointRepository:
    async def create(
        self, db: AsyncSession, datapoint: MetricDatapoint
    ) -> MetricDatapoint:
        db.add(datapoint)
        await db.flush()
        return datapoint

    async def create_batch(
        self, db: AsyncSession, datapoints: list[MetricDatapoint]
    ) -> int:
        db.add_all(datapoints)
        await db.flush()
        return len(datapoints)

    async def get_timeseries(
        self,
        db: AsyncSession,
        metric_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
        labels: dict | None = None,
        resolution: str = "1m",
    ) -> list[MetricDatapoint]:
        """Get time series for a metric."""
        query = select(MetricDatapoint).where(
            MetricDatapoint.metric_name == metric_name
        )
        if start:
            query = query.where(MetricDatapoint.ts >= start)
        if end:
            query = query.where(MetricDatapoint.ts <= end)

        query = query.order_by(MetricDatapoint.ts.asc())

        # For MVP: return raw datapoints (no aggregation by resolution)
        # Future: add time-bucket aggregation
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_latest(
        self,
        db: AsyncSession,
        metric_name: str,
        labels: dict | None = None,
    ) -> MetricDatapoint | None:
        query = (
            select(MetricDatapoint)
            .where(MetricDatapoint.metric_name == metric_name)
            .order_by(MetricDatapoint.ts.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_metric_names(self, db: AsyncSession) -> list[str]:
        result = await db.execute(
            select(MetricDatapoint.metric_name).distinct()
            .order_by(MetricDatapoint.metric_name)
        )
        return [row[0] for row in result.all()]

    async def cleanup_old(
        self, db: AsyncSession, retention_days: int
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        result = await db.execute(
            delete(MetricDatapoint).where(MetricDatapoint.ts < cutoff)
        )
        return result.rowcount
