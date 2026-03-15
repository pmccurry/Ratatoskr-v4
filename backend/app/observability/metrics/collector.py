"""System metrics collector."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.config import ObservabilityConfig
from app.observability.models import MetricDatapoint

logger = logging.getLogger(__name__)

_START_TIME = time.time()


class MetricsCollector:
    """Periodically collects system metrics from all modules."""

    def __init__(self, config: ObservabilityConfig):
        self._config = config
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the collection loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Metrics collector started (interval=%ds)",
            self._config.metrics_collection_interval,
        )

    async def stop(self) -> None:
        """Stop the collection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Metrics collector stopped")

    async def _run_loop(self) -> None:
        from app.common.database import get_session_factory

        factory = get_session_factory()
        while self._running:
            try:
                async with factory() as db:
                    count = await self.collect_cycle(db)
                    await db.commit()
                    if count > 0:
                        logger.debug("Collected %d metric datapoints", count)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Metrics collection error: %s", e)

            try:
                await asyncio.sleep(self._config.metrics_collection_interval)
            except asyncio.CancelledError:
                break

    async def collect_cycle(self, db: AsyncSession) -> int:
        """Run one collection cycle."""
        now = datetime.now(timezone.utc)
        datapoints: list[MetricDatapoint] = []

        # System uptime
        uptime = Decimal(str(int(time.time() - _START_TIME)))
        datapoints.append(MetricDatapoint(
            metric_name="system.uptime_seconds",
            metric_type="gauge",
            value=uptime,
            ts=now,
        ))

        # Event queue depth
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                datapoints.append(MetricDatapoint(
                    metric_name="system.event_queue_depth",
                    metric_type="gauge",
                    value=Decimal(str(emitter.queue_depth)),
                    ts=now,
                ))
                capacity = emitter.queue_capacity
                if capacity > 0:
                    pct = Decimal(str(emitter.queue_depth)) / Decimal(str(capacity)) * 100
                    datapoints.append(MetricDatapoint(
                        metric_name="system.event_queue_percent",
                        metric_type="gauge",
                        value=pct,
                        ts=now,
                    ))
        except Exception:
            pass

        # Portfolio metrics
        try:
            from app.portfolio.startup import get_portfolio_service
            service = get_portfolio_service()
            if service:
                from sqlalchemy import select, func as sa_func
                from app.portfolio.models import Position
                # Count open positions
                result = await db.execute(
                    select(sa_func.count()).select_from(Position)
                    .where(Position.status == "open")
                )
                open_count = result.scalar_one()
                datapoints.append(MetricDatapoint(
                    metric_name="portfolio.open_positions_count",
                    metric_type="gauge",
                    value=Decimal(str(open_count)),
                    ts=now,
                ))
        except Exception:
            pass

        # Strategy metrics
        try:
            from sqlalchemy import select, func as sa_func
            from app.strategies.models import Strategy
            enabled_result = await db.execute(
                select(sa_func.count()).select_from(Strategy)
                .where(Strategy.status == "enabled")
            )
            enabled_count = enabled_result.scalar_one()
            datapoints.append(MetricDatapoint(
                metric_name="strategies.enabled_count",
                metric_type="gauge",
                value=Decimal(str(enabled_count)),
                ts=now,
            ))
        except Exception:
            pass

        # Signal metrics
        try:
            from sqlalchemy import select, func as sa_func
            from app.signals.models import Signal
            pending_result = await db.execute(
                select(sa_func.count()).select_from(Signal)
                .where(Signal.status == "pending")
            )
            pending_count = pending_result.scalar_one()
            datapoints.append(MetricDatapoint(
                metric_name="signals.pending_count",
                metric_type="gauge",
                value=Decimal(str(pending_count)),
                ts=now,
            ))
        except Exception:
            pass

        # Paper trading metrics
        try:
            from sqlalchemy import select, func as sa_func
            from app.paper_trading.models import PaperOrder, PaperFill
            order_result = await db.execute(
                select(sa_func.count()).select_from(PaperOrder)
            )
            fill_result = await db.execute(
                select(sa_func.count()).select_from(PaperFill)
            )
            datapoints.append(MetricDatapoint(
                metric_name="paper_trading.total_orders",
                metric_type="counter",
                value=Decimal(str(order_result.scalar_one())),
                ts=now,
            ))
            datapoints.append(MetricDatapoint(
                metric_name="paper_trading.total_fills",
                metric_type="counter",
                value=Decimal(str(fill_result.scalar_one())),
                ts=now,
            ))
        except Exception:
            pass

        # Write all datapoints
        if datapoints:
            from app.observability.metrics.repository import MetricDatapointRepository
            repo = MetricDatapointRepository()
            await repo.create_batch(db, datapoints)

        return len(datapoints)

    async def record(
        self,
        db: AsyncSession,
        metric_name: str,
        metric_type: str,
        value: Decimal,
        labels: dict | None = None,
    ) -> None:
        """Record a single metric datapoint."""
        from app.observability.metrics.repository import MetricDatapointRepository
        repo = MetricDatapointRepository()
        dp = MetricDatapoint(
            metric_name=metric_name,
            metric_type=metric_type,
            value=value,
            labels_json=labels,
            ts=datetime.now(timezone.utc),
        )
        await repo.create(db, dp)

    async def cleanup_expired_metrics(self, db: AsyncSession) -> int:
        """Delete metric datapoints older than METRICS_RETENTION_DAYS."""
        from app.observability.metrics.repository import MetricDatapointRepository
        repo = MetricDatapointRepository()
        return await repo.cleanup_old(db, self._config.metrics_retention_days)
