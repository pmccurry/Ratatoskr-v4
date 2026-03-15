"""Strategy module repository layer — all database access."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.strategies.models import (
    PositionOverride,
    Strategy,
    StrategyConfigVersion,
    StrategyEvaluation,
    StrategyState,
)


class StrategyRepository:
    async def create(self, db: AsyncSession, strategy: Strategy) -> Strategy:
        db.add(strategy)
        await db.flush()
        return strategy

    async def get_by_id(self, db: AsyncSession, strategy_id: UUID) -> Strategy | None:
        result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
        return result.scalar_one_or_none()

    async def get_by_key(self, db: AsyncSession, key: str) -> Strategy | None:
        result = await db.execute(select(Strategy).where(Strategy.key == key))
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Strategy], int]:
        query = select(Strategy).where(Strategy.user_id == user_id)
        count_query = select(func.count()).select_from(Strategy).where(Strategy.user_id == user_id)

        if status:
            query = query.where(Strategy.status == status)
            count_query = count_query.where(Strategy.status == status)

        query = query.order_by(Strategy.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        strategies = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        return strategies, total

    async def get_enabled(self, db: AsyncSession) -> list[Strategy]:
        result = await db.execute(
            select(Strategy).where(Strategy.status == "enabled")
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, strategy: Strategy) -> Strategy:
        await db.flush()
        return strategy

    async def delete(self, db: AsyncSession, strategy_id: UUID) -> None:
        strategy = await self.get_by_id(db, strategy_id)
        if strategy:
            await db.delete(strategy)
            await db.flush()


class StrategyConfigRepository:
    async def create(
        self, db: AsyncSession, config: StrategyConfigVersion
    ) -> StrategyConfigVersion:
        db.add(config)
        await db.flush()
        return config

    async def get_active(
        self, db: AsyncSession, strategy_id: UUID
    ) -> StrategyConfigVersion | None:
        result = await db.execute(
            select(StrategyConfigVersion).where(
                StrategyConfigVersion.strategy_id == strategy_id,
                StrategyConfigVersion.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_version(
        self, db: AsyncSession, strategy_id: UUID, version: str
    ) -> StrategyConfigVersion | None:
        result = await db.execute(
            select(StrategyConfigVersion).where(
                StrategyConfigVersion.strategy_id == strategy_id,
                StrategyConfigVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_history(
        self, db: AsyncSession, strategy_id: UUID
    ) -> list[StrategyConfigVersion]:
        result = await db.execute(
            select(StrategyConfigVersion)
            .where(StrategyConfigVersion.strategy_id == strategy_id)
            .order_by(StrategyConfigVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_all(self, db: AsyncSession, strategy_id: UUID) -> None:
        await db.execute(
            update(StrategyConfigVersion)
            .where(StrategyConfigVersion.strategy_id == strategy_id)
            .values(is_active=False)
        )
        await db.flush()


class StrategyStateRepository:
    async def get_or_create(
        self, db: AsyncSession, strategy_id: UUID
    ) -> StrategyState:
        result = await db.execute(
            select(StrategyState).where(StrategyState.strategy_id == strategy_id)
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = StrategyState(strategy_id=strategy_id, state_json={})
            db.add(state)
            await db.flush()
        return state

    async def update(self, db: AsyncSession, state: StrategyState) -> StrategyState:
        await db.flush()
        return state


class StrategyEvaluationRepository:
    async def create(
        self, db: AsyncSession, evaluation: StrategyEvaluation
    ) -> StrategyEvaluation:
        db.add(evaluation)
        await db.flush()
        return evaluation

    async def get_recent(
        self, db: AsyncSession, strategy_id: UUID, limit: int = 20
    ) -> list[StrategyEvaluation]:
        result = await db.execute(
            select(StrategyEvaluation)
            .where(StrategyEvaluation.strategy_id == strategy_id)
            .order_by(StrategyEvaluation.evaluated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_error_count(self, db: AsyncSession, strategy_id: UUID) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(StrategyEvaluation)
            .where(
                StrategyEvaluation.strategy_id == strategy_id,
                StrategyEvaluation.status == "error",
            )
        )
        return result.scalar_one()


class PositionOverrideRepository:
    async def create(
        self, db: AsyncSession, override: PositionOverride
    ) -> PositionOverride:
        db.add(override)
        await db.flush()
        return override

    async def get_active_for_position(
        self, db: AsyncSession, position_id: UUID
    ) -> list[PositionOverride]:
        result = await db.execute(
            select(PositionOverride).where(
                PositionOverride.position_id == position_id,
                PositionOverride.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def deactivate(self, db: AsyncSession, override_id: UUID) -> None:
        await db.execute(
            update(PositionOverride)
            .where(PositionOverride.id == override_id)
            .values(is_active=False)
        )
        await db.flush()

    async def get_by_strategy(
        self, db: AsyncSession, strategy_id: UUID
    ) -> list[PositionOverride]:
        result = await db.execute(
            select(PositionOverride).where(
                PositionOverride.strategy_id == strategy_id
            )
        )
        return list(result.scalars().all())
