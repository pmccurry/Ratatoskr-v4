"""Risk module API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.common.database import get_db
from app.risk.schemas import (
    DrawdownResponse,
    ExposureResponse,
    KillSwitchRequest,
    KillSwitchStatusResponse,
    RiskConfigAuditResponse,
    RiskConfigResponse,
    RiskDecisionResponse,
    RiskOverviewResponse,
    UpdateRiskConfigRequest,
)
from app.risk.startup import get_risk_service

router = APIRouter(
    prefix="/risk",
    tags=["Risk"],
)


# --- Risk Decisions ---


@router.get("/decisions", response_model=dict)
async def list_decisions(
    status: str | None = Query(None),
    reason_code: str | None = Query(None, alias="reasonCode"),
    date_start: datetime | None = Query(None, alias="dateStart"),
    date_end: datetime | None = Query(None, alias="dateEnd"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List risk decisions with filters."""
    service = get_risk_service()
    decisions, total = await service.list_decisions(
        db, status=status, reason_code=reason_code,
        date_start=date_start, date_end=date_end,
        page=page, page_size=page_size,
    )
    return {
        "data": [
            RiskDecisionResponse.model_validate(d).model_dump(by_alias=True)
            for d in decisions
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/decisions/{decision_id}", response_model=dict)
async def get_decision(
    decision_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a risk decision by ID."""
    service = get_risk_service()
    decision = await service.get_decision(db, decision_id)
    return {"data": RiskDecisionResponse.model_validate(decision).model_dump(by_alias=True)}


# --- Risk Overview ---


@router.get("/overview", response_model=dict)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get complete risk overview for dashboard."""
    service = get_risk_service()
    overview = await service.get_overview(db)
    return {"data": RiskOverviewResponse(**overview).model_dump(by_alias=True)}


# --- Kill Switch ---


@router.post("/kill-switch/activate", response_model=dict)
async def activate_kill_switch(
    request: KillSwitchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Activate global or strategy kill switch."""
    service = get_risk_service()
    ks = await service.activate_kill_switch(
        db, scope=request.scope, strategy_id=request.strategy_id,
        activated_by=user.email, reason=request.reason,
    )
    return {"data": {"id": str(ks.id), "scope": ks.scope, "is_active": ks.is_active}}


@router.post("/kill-switch/deactivate", response_model=dict)
async def deactivate_kill_switch(
    request: KillSwitchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Deactivate global or strategy kill switch."""
    service = get_risk_service()
    ks = await service.deactivate_kill_switch(
        db, scope=request.scope, strategy_id=request.strategy_id,
    )
    return {"data": {"id": str(ks.id), "scope": ks.scope, "is_active": ks.is_active}}


@router.get("/kill-switch/status", response_model=dict)
async def get_kill_switch_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current kill switch state."""
    service = get_risk_service()
    status = await service.get_kill_switch_status(db)
    return {"data": KillSwitchStatusResponse(**status).model_dump(by_alias=True)}


# --- Risk Configuration ---


@router.get("/config", response_model=dict)
async def get_risk_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current risk configuration."""
    service = get_risk_service()
    config = await service.get_risk_config(db)
    return {"data": RiskConfigResponse.model_validate(config).model_dump(by_alias=True)}


@router.put("/config", response_model=dict)
async def update_risk_config(
    request: UpdateRiskConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Update risk configuration (admin only)."""
    service = get_risk_service()
    updates = request.model_dump(exclude_none=True)
    config = await service.update_risk_config(db, updates, changed_by=user.email)
    return {"data": RiskConfigResponse.model_validate(config).model_dump(by_alias=True)}


@router.get("/config/audit", response_model=dict)
async def get_config_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get risk config change history."""
    service = get_risk_service()
    audits, total = await service.get_config_audit(db, page=page, page_size=page_size)
    return {
        "data": [
            RiskConfigAuditResponse.model_validate(a).model_dump(by_alias=True)
            for a in audits
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


# --- Exposure ---


@router.get("/exposure", response_model=dict)
async def get_exposure(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current exposure breakdown."""
    service = get_risk_service()
    exposure = await service.get_exposure(db)
    return {
        "data": ExposureResponse(
            total_exposure_percent=exposure["total_percent"],
            total_exposure_value=exposure["total_value"],
            by_symbol=[
                {"symbol": k, "value": str(v)}
                for k, v in exposure["by_symbol"].items()
            ],
            by_strategy=[
                {"strategy_id": k, "value": str(v)}
                for k, v in exposure["by_strategy"].items()
            ],
        ).model_dump(by_alias=True)
    }


# --- Drawdown ---


@router.get("/drawdown", response_model=dict)
async def get_drawdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current drawdown state with threshold status."""
    service = get_risk_service()
    drawdown = await service.get_drawdown(db)
    return {"data": DrawdownResponse(**drawdown).model_dump(by_alias=True)}


@router.post("/drawdown/reset-peak", response_model=dict)
async def reset_peak_equity(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Reset peak equity (admin only)."""
    service = get_risk_service()
    await service.reset_peak_equity(db, admin_user=user.email)
    return {"data": {"status": "peak_equity_reset"}}
