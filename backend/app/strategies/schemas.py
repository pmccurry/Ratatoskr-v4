"""Strategy module Pydantic schemas for API request/response."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class CreateStrategyRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    key: str
    name: str
    description: str = ""
    market: str
    config: dict

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: str) -> str:
        if v not in ("equities", "forex", "both"):
            raise ValueError("market must be one of: equities, forex, both")
        return v

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v or len(v) > 100:
            raise ValueError("key must be between 1 and 100 characters")
        return v


class UpdateStrategyConfigRequest(BaseModel):
    config: dict


class UpdateStrategyMetaRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = None
    description: str | None = None


class StrategyStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("enabled", "paused", "disabled"):
            raise ValueError("status must be one of: enabled, paused, disabled")
        return v


class PositionOverrideRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    position_id: UUID
    override_type: str
    value: dict
    reason: str | None = None

    @field_validator("override_type")
    @classmethod
    def validate_override_type(cls, v: str) -> str:
        if v not in ("stop_loss", "take_profit", "trailing_stop"):
            raise ValueError("override_type must be one of: stop_loss, take_profit, trailing_stop")
        return v


class StrategyResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: UUID
    key: str
    name: str
    description: str
    type: str
    status: str
    current_version: str
    market: str
    auto_pause_error_count: int
    last_evaluated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StrategyDetailResponse(StrategyResponse):
    config: dict


class StrategyEvaluationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: UUID
    strategy_id: UUID
    strategy_version: str
    evaluated_at: datetime
    symbols_evaluated: int
    signals_emitted: int
    exits_triggered: int
    errors: int
    duration_ms: int
    status: str
    skip_reason: str | None
    created_at: datetime


class StrategyValidationResponse(BaseModel):
    valid: bool
    errors: list[dict]
    warnings: list[dict]
