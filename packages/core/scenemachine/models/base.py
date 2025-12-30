"""Base classes for SQLAlchemy models."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class.

    All models should inherit from this class.
    """

    pass


class UUIDMixin:
    """Mixin that adds a UUID primary key to models."""

    id: Mapped[Any] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
