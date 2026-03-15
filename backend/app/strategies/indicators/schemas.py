"""Pydantic schemas for the indicator API endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class IndicatorParamSchema(BaseModel):
    """Schema for an indicator parameter definition."""

    name: str
    type: str
    default: Any
    min: float | None = Field(None, alias="min")
    max: float | None = Field(None, alias="max")
    options: list[str] | None = None

    model_config = {"populate_by_name": True}


class IndicatorDefinitionSchema(BaseModel):
    """Schema for an indicator definition (catalog entry)."""

    key: str
    name: str
    category: str
    params: list[IndicatorParamSchema]
    outputs: list[str]
    description: str

    model_config = {"populate_by_name": True}
