"""Base Pydantic schemas and common patterns."""

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration.

    All schemas should inherit from this class for consistent behavior.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1


class ErrorDetail(BaseSchema):
    """Detailed error information."""

    field: Optional[str] = None
    message: str
    code: str


class ErrorResponse(BaseSchema):
    """Standard error response format."""

    error: str
    detail: Optional[str] = None
    code: str
    errors: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None


class SuccessResponse(BaseSchema):
    """Standard success response for operations without specific return data."""

    success: bool = True
    message: Optional[str] = None


class HealthResponse(BaseSchema):
    """Health check response."""

    status: str
    version: str
    environment: str


class ReadinessResponse(BaseSchema):
    """Readiness check response with component status."""

    ready: bool
    checks: dict[str, str]
