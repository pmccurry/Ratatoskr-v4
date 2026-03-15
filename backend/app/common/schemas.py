"""Shared Pydantic schemas for API responses."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error detail within an error response."""

    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail


class PaginationParams(BaseModel):
    """Pagination query parameters with defaults and limits."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    """Pagination metadata included in paginated responses."""

    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    data: list[T]
    pagination: PaginationMeta


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
