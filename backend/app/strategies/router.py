"""Strategy module API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.strategies.formulas.schemas import FormulaValidationRequest, FormulaValidationResponse
from app.strategies.indicators import get_registry
from app.strategies.indicators.schemas import IndicatorDefinitionSchema, IndicatorParamSchema
from app.strategies.schemas import (
    CreateStrategyRequest,
    PositionOverrideRequest,
    StrategyEvaluationResponse,
    StrategyResponse,
    UpdateStrategyConfigRequest,
    UpdateStrategyMetaRequest,
)
from app.strategies.service import StrategyService

router = APIRouter(
    prefix="/strategies",
    tags=["Strategies"],
)

_service = StrategyService()


# --- Indicator catalog (from TASK-008) ---


@router.get("/indicators")
async def list_indicators(
    _current_user: User = Depends(get_current_user),
):
    """List all available indicators for the strategy builder."""
    reg = get_registry()
    definitions = reg.list_all()
    return {
        "data": [
            IndicatorDefinitionSchema(
                key=d.key,
                name=d.name,
                category=d.category,
                params=[
                    IndicatorParamSchema(
                        name=p.name,
                        type=p.type,
                        default=p.default,
                        min=p.min,
                        max=p.max,
                        options=p.options,
                    )
                    for p in d.params
                ],
                outputs=d.outputs,
                description=d.description,
            ).model_dump(by_alias=True)
            for d in definitions
        ]
    }


# --- Formula validation (from TASK-008) ---


@router.post("/formulas/validate")
async def validate_formula(
    body: FormulaValidationRequest,
    _current_user: User = Depends(get_current_user),
):
    """Validate a formula expression without evaluating it."""
    from app.strategies.formulas.parser import FormulaParser

    reg = get_registry()
    parser = FormulaParser(reg)
    errors = parser.validate(body.expression)

    return {
        "data": FormulaValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
        ).model_dump(by_alias=True)
    }


# --- Strategy CRUD ---


@router.post("", status_code=201)
async def create_strategy(
    body: CreateStrategyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new strategy (starts as draft)."""
    strategy = await _service.create_strategy(db, current_user.id, body)
    return {"data": StrategyResponse.model_validate(strategy).model_dump(by_alias=True)}


@router.get("")
async def list_strategies(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's strategies with pagination."""
    strategies, total = await _service.list_strategies(
        db, current_user.id, status=status, page=page, page_size=page_size
    )
    return {
        "data": [s.model_dump(by_alias=True) for s in strategies],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get strategy detail with active config."""
    detail = await _service.get_strategy(db, strategy_id, current_user.id)
    return {"data": detail.model_dump(by_alias=True)}


@router.put("/{strategy_id}/config")
async def update_strategy_config(
    strategy_id: UUID,
    body: UpdateStrategyConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update strategy config. Creates new version if enabled."""
    strategy = await _service.update_config(db, strategy_id, current_user.id, body)
    return {"data": StrategyResponse.model_validate(strategy).model_dump(by_alias=True)}


@router.put("/{strategy_id}/meta")
async def update_strategy_meta(
    strategy_id: UUID,
    body: UpdateStrategyMetaRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update strategy name/description."""
    strategy = await _service.update_meta(db, strategy_id, current_user.id, body)
    return {"data": StrategyResponse.model_validate(strategy).model_dump(by_alias=True)}


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a draft strategy."""
    await _service.delete_strategy(db, strategy_id, current_user.id)


@router.post("/{strategy_id}/validate")
async def validate_strategy_config(
    strategy_id: UUID,
    body: UpdateStrategyConfigRequest,
    _current_user: User = Depends(get_current_user),
):
    """Validate config without saving."""
    result = _service.validate_config(body.config)
    return {"data": result.model_dump(by_alias=True)}


# --- Lifecycle ---


@router.post("/{strategy_id}/enable")
async def enable_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable strategy."""
    strategy = await _service.change_status(db, strategy_id, current_user.id, "enabled")
    return {"data": StrategyResponse.model_validate(strategy).model_dump(by_alias=True)}


@router.post("/{strategy_id}/pause")
async def pause_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause strategy."""
    strategy = await _service.change_status(db, strategy_id, current_user.id, "paused")
    return {"data": StrategyResponse.model_validate(strategy).model_dump(by_alias=True)}


@router.post("/{strategy_id}/disable")
async def disable_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable strategy."""
    strategy = await _service.change_status(db, strategy_id, current_user.id, "disabled")
    return {"data": StrategyResponse.model_validate(strategy).model_dump(by_alias=True)}


# --- Versioning ---


@router.get("/{strategy_id}/versions")
async def get_version_history(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get config version history."""
    versions = await _service.get_version_history(db, strategy_id, current_user.id)
    return {
        "data": [
            {
                "id": str(v.id),
                "version": v.version,
                "isActive": v.is_active,
                "config": v.config_json,
                "createdAt": v.created_at.isoformat(),
            }
            for v in versions
        ]
    }


# --- Evaluation History ---


@router.get("/{strategy_id}/evaluations")
async def get_evaluations(
    strategy_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent evaluation logs."""
    evals = await _service.get_evaluations(db, strategy_id, current_user.id, limit=limit)
    return {
        "data": [
            StrategyEvaluationResponse.model_validate(e).model_dump(by_alias=True)
            for e in evals
        ]
    }


# --- Position Overrides ---


@router.post("/{strategy_id}/overrides", status_code=201)
async def create_override(
    strategy_id: UUID,
    body: PositionOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a position-level exit rule override."""
    override = await _service.create_override(db, strategy_id, current_user.id, body)
    return {
        "data": {
            "id": str(override.id),
            "positionId": str(override.position_id),
            "strategyId": str(override.strategy_id),
            "overrideType": override.override_type,
            "overrideValue": override.override_value_json,
            "reason": override.reason,
            "isActive": override.is_active,
            "createdAt": override.created_at.isoformat(),
        }
    }


@router.delete("/overrides/{override_id}", status_code=204)
async def remove_override(
    override_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a position override."""
    await _service.remove_override(db, override_id, current_user.id)
