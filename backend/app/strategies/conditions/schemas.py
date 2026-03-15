"""Pydantic schemas for conditions used in strategy config validation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator


class OperandSchema(BaseModel):
    """Left or right side of a condition."""

    type: str  # "indicator" | "formula" | "value" | "range"
    indicator: str | None = None
    params: dict | None = None
    output: str | None = None
    expression: str | None = None
    value: Decimal | None = None
    min: Decimal | None = Field(None, alias="min")
    max: Decimal | None = Field(None, alias="max")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _validate_operand(self):
        if self.type == "indicator" and not self.indicator:
            raise ValueError("indicator type requires 'indicator' field")
        if self.type == "formula" and not self.expression:
            raise ValueError("formula type requires 'expression' field")
        if self.type == "value" and self.value is None:
            raise ValueError("value type requires 'value' field")
        if self.type == "range":
            if self.min is None or self.max is None:
                raise ValueError("range type requires 'min' and 'max' fields")
        return self


_ALLOWED_OPERATORS = {
    "greater_than",
    "less_than",
    "greater_than_or_equal",
    "less_than_or_equal",
    "equal",
    "crosses_above",
    "crosses_below",
    "between",
    "outside",
}


class ConditionSchema(BaseModel):
    """A single condition."""

    left: OperandSchema
    operator: str
    right: OperandSchema

    @model_validator(mode="after")
    def _validate_operator(self):
        if self.operator not in _ALLOWED_OPERATORS:
            raise ValueError(
                f"Invalid operator '{self.operator}'. Allowed: {sorted(_ALLOWED_OPERATORS)}"
            )
        return self


class ConditionGroupSchema(BaseModel):
    """A group of conditions with AND/OR logic."""

    logic: str  # "and" | "or"
    conditions: list[ConditionSchema | ConditionGroupSchema]

    @model_validator(mode="after")
    def _validate_logic(self):
        if self.logic not in ("and", "or"):
            raise ValueError("logic must be 'and' or 'or'")
        return self
