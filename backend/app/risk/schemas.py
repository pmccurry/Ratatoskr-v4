"""Risk module Pydantic schemas for API request/response."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RiskDecisionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: UUID
    signal_id: UUID
    status: str
    checks_passed: list[str]
    failed_check: str | None
    reason_code: str
    reason_text: str
    modifications_json: dict | None
    portfolio_state_snapshot: dict
    ts: datetime
    created_at: datetime


class KillSwitchStatusResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    global_active: bool
    strategies: list[dict]


class RiskConfigResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: UUID
    max_position_size_percent: Decimal
    max_symbol_exposure_percent: Decimal
    max_strategy_exposure_percent: Decimal
    max_total_exposure_percent: Decimal
    max_drawdown_percent: Decimal
    max_drawdown_catastrophic_percent: Decimal
    max_daily_loss_percent: Decimal
    max_daily_loss_amount: Decimal | None
    min_position_value: Decimal
    updated_by: str | None
    updated_at: datetime


class UpdateRiskConfigRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    max_position_size_percent: Decimal | None = None
    max_symbol_exposure_percent: Decimal | None = None
    max_strategy_exposure_percent: Decimal | None = None
    max_total_exposure_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    max_drawdown_catastrophic_percent: Decimal | None = None
    max_daily_loss_percent: Decimal | None = None
    max_daily_loss_amount: Decimal | None = None
    min_position_value: Decimal | None = None


class KillSwitchRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    scope: str  # global | strategy
    strategy_id: UUID | None = None
    reason: str | None = None


class RiskOverviewResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    kill_switch: KillSwitchStatusResponse
    drawdown: dict
    daily_loss: dict
    total_exposure: dict
    symbol_exposure: list[dict]
    strategy_exposure: list[dict]
    recent_decisions: list[dict]


class RiskConfigAuditResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: UUID
    field_changed: str
    old_value: str
    new_value: str
    changed_by: str
    changed_at: datetime


class ExposureResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    total_exposure_percent: Decimal
    total_exposure_value: Decimal
    by_symbol: list[dict]
    by_strategy: list[dict]


class DrawdownResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    peak_equity: Decimal
    current_equity: Decimal
    drawdown_percent: Decimal
    threshold_status: str
    max_drawdown_percent: Decimal
    catastrophic_percent: Decimal
