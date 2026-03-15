"""Pydantic schemas for formula validation endpoint."""

from pydantic import BaseModel


class FormulaValidationRequest(BaseModel):
    """Request body for formula validation."""

    expression: str


class FormulaValidationResponse(BaseModel):
    """Response for formula validation."""

    valid: bool
    errors: list[str]
