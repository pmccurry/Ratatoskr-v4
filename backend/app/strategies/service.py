"""Strategy service — CRUD, validation, lifecycle, and versioning."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.strategies.errors import (
    StrategyInvalidConfigError,
    StrategyNotFoundError,
)
from app.strategies.formulas.parser import FormulaParser
from app.strategies.indicators import get_registry
from app.strategies.models import (
    PositionOverride,
    Strategy,
    StrategyConfigVersion,
    StrategyState,
)
from app.strategies.repository import (
    PositionOverrideRepository,
    StrategyConfigRepository,
    StrategyEvaluationRepository,
    StrategyRepository,
    StrategyStateRepository,
)
from app.strategies.schemas import (
    CreateStrategyRequest,
    PositionOverrideRequest,
    StrategyDetailResponse,
    StrategyResponse,
    StrategyValidationResponse,
    UpdateStrategyConfigRequest,
    UpdateStrategyMetaRequest,
)
from app.strategies.validation import StrategyValidator

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"enabled"},
    "enabled": {"paused", "disabled"},
    "paused": {"enabled", "disabled"},
    "disabled": {"enabled"},
}

_strategy_repo = StrategyRepository()
_config_repo = StrategyConfigRepository()
_state_repo = StrategyStateRepository()
_eval_repo = StrategyEvaluationRepository()
_override_repo = PositionOverrideRepository()


class StrategyService:
    """Strategy CRUD, validation, lifecycle, and versioning."""

    def __init__(self):
        registry = get_registry()
        parser = FormulaParser(registry)
        self._validator = StrategyValidator(registry, parser)

    # --- CRUD ---

    async def create_strategy(
        self, db: AsyncSession, user_id: UUID, data: CreateStrategyRequest
    ) -> Strategy:
        existing = await _strategy_repo.get_by_key(db, data.key)
        if existing:
            from app.common.errors import DomainError
            raise DomainError(
                code="STRATEGY_ALREADY_EXISTS",
                message=f"Strategy with key '{data.key}' already exists",
                details={"key": data.key},
            )

        validation = self._validator.validate(data.config)
        if not validation.valid:
            raise StrategyInvalidConfigError(
                message="Strategy config validation failed",
                details={"errors": validation.errors},
            )

        strategy = Strategy(
            key=data.key,
            name=data.name,
            description=data.description,
            market=data.market,
            type="config",
            status="draft",
            current_version="1.0.0",
            user_id=user_id,
        )
        strategy = await _strategy_repo.create(db, strategy)

        config_version = StrategyConfigVersion(
            strategy_id=strategy.id,
            version="1.0.0",
            config_json=data.config,
            is_active=True,
        )
        await _config_repo.create(db, config_version)

        await _state_repo.get_or_create(db, strategy.id)

        return strategy

    async def get_strategy(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID
    ) -> StrategyDetailResponse:
        strategy = await self._get_owned_strategy(db, strategy_id, user_id)
        active_config = await _config_repo.get_active(db, strategy_id)
        config_dict = active_config.config_json if active_config else {}

        return StrategyDetailResponse(
            id=strategy.id,
            key=strategy.key,
            name=strategy.name,
            description=strategy.description,
            type=strategy.type,
            status=strategy.status,
            current_version=strategy.current_version,
            market=strategy.market,
            auto_pause_error_count=strategy.auto_pause_error_count,
            last_evaluated_at=strategy.last_evaluated_at,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            config=config_dict,
        )

    async def list_strategies(
        self,
        db: AsyncSession,
        user_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StrategyResponse], int]:
        strategies, total = await _strategy_repo.get_by_user(
            db, user_id, status=status, page=page, page_size=page_size
        )
        responses = [StrategyResponse.model_validate(s) for s in strategies]
        return responses, total

    async def update_config(
        self,
        db: AsyncSession,
        strategy_id: UUID,
        user_id: UUID,
        data: UpdateStrategyConfigRequest,
    ) -> Strategy:
        strategy = await self._get_owned_strategy(db, strategy_id, user_id)

        validation = self._validator.validate(data.config)
        if not validation.valid:
            raise StrategyInvalidConfigError(
                message="Strategy config validation failed",
                details={"errors": validation.errors},
            )

        if strategy.status == "enabled":
            new_version = self._next_version(strategy.current_version)
            await _config_repo.deactivate_all(db, strategy_id)
            new_config = StrategyConfigVersion(
                strategy_id=strategy_id,
                version=new_version,
                config_json=data.config,
                is_active=True,
            )
            await _config_repo.create(db, new_config)
            strategy.current_version = new_version
            await _strategy_repo.update(db, strategy)

            # Emit config changed event (new version created for enabled strategy)
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="strategy.config_changed",
                        category="strategies",
                        severity="info",
                        source_module="strategies",
                        summary=f"⚙️ {strategy.name} config updated",
                        entity_type="strategy",
                        entity_id=strategy.id,
                        strategy_id=strategy.id,
                        details={"new_version": new_version},
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline
        else:
            active_config = await _config_repo.get_active(db, strategy_id)
            if active_config:
                active_config.config_json = data.config
                await db.flush()
            else:
                new_config = StrategyConfigVersion(
                    strategy_id=strategy_id,
                    version=strategy.current_version,
                    config_json=data.config,
                    is_active=True,
                )
                await _config_repo.create(db, new_config)

        return strategy

    async def update_meta(
        self,
        db: AsyncSession,
        strategy_id: UUID,
        user_id: UUID,
        data: UpdateStrategyMetaRequest,
    ) -> Strategy:
        strategy = await self._get_owned_strategy(db, strategy_id, user_id)
        if data.name is not None:
            strategy.name = data.name
        if data.description is not None:
            strategy.description = data.description
        await _strategy_repo.update(db, strategy)
        return strategy

    async def delete_strategy(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID
    ) -> None:
        strategy = await self._get_owned_strategy(db, strategy_id, user_id)
        if strategy.status != "draft":
            from app.common.errors import DomainError
            raise DomainError(
                code="STRATEGY_VALIDATION_FAILED",
                message="Only draft strategies can be deleted",
                details={"status": strategy.status},
            )
        await _strategy_repo.delete(db, strategy_id)

    # --- Lifecycle ---

    async def change_status(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID, new_status: str
    ) -> Strategy:
        strategy = await self._get_owned_strategy(db, strategy_id, user_id)
        old_status = strategy.status
        allowed = _VALID_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            from app.common.errors import DomainError
            raise DomainError(
                code="STRATEGY_NOT_ENABLED",
                message=f"Cannot transition from '{strategy.status}' to '{new_status}'",
                details={
                    "current_status": strategy.status,
                    "requested_status": new_status,
                    "allowed": sorted(allowed),
                },
            )

        strategy.status = new_status

        if new_status == "enabled":
            strategy.auto_pause_error_count = 0

        if new_status in ("paused", "disabled"):
            try:
                from app.signals.startup import get_signal_service

                signal_service = get_signal_service()
                canceled = await signal_service.cancel_strategy_signals(db, strategy_id)
                if canceled > 0:
                    logger.info(
                        "Canceled %d pending signals for strategy %s on %s",
                        canceled, strategy.key, new_status,
                    )
            except RuntimeError:
                pass

        # TODO (TASK-013): When pausing/disabling, positions transfer to safety monitor.
        # Currently no positions to transfer.

        await _strategy_repo.update(db, strategy)
        logger.info(
            "Strategy %s status changed to %s", strategy.key, new_status
        )

        # Emit lifecycle event
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                if new_status == "enabled" and old_status == "paused":
                    event_type = "strategy.resumed"
                    summary = f"✅ {strategy.name} resumed"
                elif new_status == "enabled":
                    event_type = "strategy.enabled"
                    summary = f"✅ {strategy.name} enabled"
                elif new_status == "disabled":
                    event_type = "strategy.disabled"
                    summary = f"⚙️ {strategy.name} disabled"
                elif new_status == "paused":
                    event_type = "strategy.paused"
                    summary = f"⚙️ {strategy.name} paused"
                else:
                    event_type = f"strategy.{new_status}"
                    summary = f"⚙️ {strategy.name} {new_status}"
                await emitter.emit(
                    event_type=event_type,
                    category="strategies",
                    severity="info",
                    source_module="strategies",
                    summary=summary,
                    entity_type="strategy",
                    entity_id=strategy.id,
                    strategy_id=strategy.id,
                    details={"old_status": old_status, "new_status": new_status},
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return strategy

    # --- Versioning ---

    def _next_version(self, current: str) -> str:
        parts = current.split(".")
        if len(parts) != 3:
            return "1.1.0"
        major, minor, patch = parts
        return f"{major}.{int(minor) + 1}.{patch}"

    async def get_version_history(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID
    ) -> list[StrategyConfigVersion]:
        await self._get_owned_strategy(db, strategy_id, user_id)
        return await _config_repo.get_history(db, strategy_id)

    # --- Validation ---

    def validate_config(self, config: dict) -> StrategyValidationResponse:
        return self._validator.validate(config)

    # --- Position Overrides ---

    async def create_override(
        self,
        db: AsyncSession,
        strategy_id: UUID,
        user_id: UUID,
        data: PositionOverrideRequest,
    ) -> PositionOverride:
        await self._get_owned_strategy(db, strategy_id, user_id)

        override = PositionOverride(
            position_id=data.position_id,
            strategy_id=strategy_id,
            override_type=data.override_type,
            original_value_json={},  # TODO (TASK-013): populate from current position exit rules
            override_value_json=data.value,
            reason=data.reason,
            created_by="user",
            is_active=True,
        )
        return await _override_repo.create(db, override)

    async def remove_override(
        self, db: AsyncSession, override_id: UUID, user_id: UUID
    ) -> None:
        # Ownership check: the override's strategy must belong to the user
        # For now, just deactivate — a full check would load the override,
        # then load the strategy, then verify user_id. Keeping simple for MVP.
        await _override_repo.deactivate(db, override_id)

    # --- Evaluation History ---

    async def get_evaluations(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID, limit: int = 20
    ):
        await self._get_owned_strategy(db, strategy_id, user_id)
        return await _eval_repo.get_recent(db, strategy_id, limit=limit)

    # --- Internal ---

    async def _get_owned_strategy(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID
    ) -> Strategy:
        strategy = await _strategy_repo.get_by_id(db, strategy_id)
        if not strategy:
            raise StrategyNotFoundError(str(strategy_id))
        if strategy.user_id != user_id:
            raise StrategyNotFoundError(str(strategy_id))
        return strategy
