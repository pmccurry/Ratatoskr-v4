"""Risk module repository — all database access."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.risk.models import KillSwitch, RiskConfig, RiskConfigAudit, RiskDecision


class RiskDecisionRepository:
    async def create(self, db: AsyncSession, decision: RiskDecision) -> RiskDecision:
        db.add(decision)
        await db.flush()
        return decision

    async def get_by_id(self, db: AsyncSession, decision_id: UUID) -> RiskDecision | None:
        result = await db.execute(select(RiskDecision).where(RiskDecision.id == decision_id))
        return result.scalar_one_or_none()

    async def get_by_signal_id(self, db: AsyncSession, signal_id: UUID) -> RiskDecision | None:
        result = await db.execute(
            select(RiskDecision).where(RiskDecision.signal_id == signal_id)
        )
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        db: AsyncSession,
        status: str | None = None,
        reason_code: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RiskDecision], int]:
        query = select(RiskDecision)
        count_query = select(func.count()).select_from(RiskDecision)

        filters = []
        if status:
            filters.append(RiskDecision.status == status)
        if reason_code:
            filters.append(RiskDecision.reason_code == reason_code)
        if date_start:
            filters.append(RiskDecision.created_at >= date_start)
        if date_end:
            filters.append(RiskDecision.created_at <= date_end)

        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

        query = query.order_by(RiskDecision.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        decisions = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return decisions, total

    async def get_recent(self, db: AsyncSession, limit: int = 10) -> list[RiskDecision]:
        result = await db.execute(
            select(RiskDecision).order_by(RiskDecision.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


class KillSwitchRepository:
    async def get_global(self, db: AsyncSession) -> KillSwitch | None:
        result = await db.execute(
            select(KillSwitch).where(
                KillSwitch.scope == "global"
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_for_strategy(self, db: AsyncSession, strategy_id: UUID) -> KillSwitch | None:
        result = await db.execute(
            select(KillSwitch).where(
                KillSwitch.scope == "strategy",
                KillSwitch.strategy_id == strategy_id,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self, db: AsyncSession) -> list[KillSwitch]:
        result = await db.execute(
            select(KillSwitch).where(KillSwitch.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def upsert(self, db: AsyncSession, kill_switch: KillSwitch) -> KillSwitch:
        # Check if one already exists for this scope+strategy
        if kill_switch.scope == "global":
            existing = await self.get_global(db)
        else:
            existing = await self.get_for_strategy(db, kill_switch.strategy_id)

        if existing:
            existing.is_active = kill_switch.is_active
            existing.activated_by = kill_switch.activated_by
            existing.activated_at = kill_switch.activated_at
            existing.deactivated_at = kill_switch.deactivated_at
            existing.reason = kill_switch.reason
            await db.flush()
            return existing

        db.add(kill_switch)
        await db.flush()
        return kill_switch


class RiskConfigRepository:
    async def get_active(self, db: AsyncSession) -> RiskConfig | None:
        result = await db.execute(
            select(RiskConfig).order_by(RiskConfig.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_or_update(self, db: AsyncSession, config: RiskConfig) -> RiskConfig:
        existing = await self.get_active(db)
        if existing:
            existing.max_position_size_percent = config.max_position_size_percent
            existing.max_symbol_exposure_percent = config.max_symbol_exposure_percent
            existing.max_strategy_exposure_percent = config.max_strategy_exposure_percent
            existing.max_total_exposure_percent = config.max_total_exposure_percent
            existing.max_drawdown_percent = config.max_drawdown_percent
            existing.max_drawdown_catastrophic_percent = config.max_drawdown_catastrophic_percent
            existing.max_daily_loss_percent = config.max_daily_loss_percent
            existing.max_daily_loss_amount = config.max_daily_loss_amount
            existing.min_position_value = config.min_position_value
            existing.updated_by = config.updated_by
            await db.flush()
            return existing

        db.add(config)
        await db.flush()
        return config

    async def seed_defaults(self, db: AsyncSession) -> RiskConfig:
        """Seed default risk config if none exists."""
        existing = await self.get_active(db)
        if existing:
            return existing

        from app.risk.config import get_risk_module_config
        module_config = get_risk_module_config()

        config = RiskConfig(
            max_position_size_percent=module_config.default_max_position_size_percent,
            max_symbol_exposure_percent=module_config.default_max_symbol_exposure_percent,
            max_strategy_exposure_percent=module_config.default_max_strategy_exposure_percent,
            max_total_exposure_percent=module_config.default_max_total_exposure_percent,
            max_drawdown_percent=module_config.default_max_drawdown_percent,
            max_drawdown_catastrophic_percent=module_config.default_max_drawdown_catastrophic_percent,
            max_daily_loss_percent=module_config.default_max_daily_loss_percent,
            min_position_value=module_config.default_min_position_value,
            updated_by="system",
        )
        db.add(config)
        await db.flush()
        return config


class RiskConfigAuditRepository:
    async def create(self, db: AsyncSession, audit: RiskConfigAudit) -> RiskConfigAudit:
        db.add(audit)
        await db.flush()
        return audit

    async def get_history(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RiskConfigAudit], int]:
        query = select(RiskConfigAudit).order_by(RiskConfigAudit.changed_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        audits = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(RiskConfigAudit)
        )
        total = count_result.scalar_one()

        return audits, total
