"""
SQLAlchemy Base Classes and Mixins

Provides common functionality for all database models.
"""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, MetaData, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class JSONType(TypeDecorator):
    """
    A JSON type that uses JSONB on PostgreSQL and JSON on SQLite/others.
    This allows models to be database-agnostic.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class ArrayType(TypeDecorator):
    """
    An ARRAY type that uses native ARRAY on PostgreSQL and JSON on SQLite/others.
    This allows models to be database-agnostic for array columns.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, item_type=None) -> None:
        super().__init__()
        self.item_type = item_type

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # Use native ARRAY on PostgreSQL
            if self.item_type:
                return dialect.type_descriptor(ARRAY(self.item_type))
            return dialect.type_descriptor(ARRAY(Text))
        # Use JSON for SQLite/others
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite, store as JSON array
        return value  # JSON type handles serialization

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite, parse JSON array
        if isinstance(value, str):
            return json.loads(value)
        return value


class UUIDType(TypeDecorator):
    """
    A UUID type that uses native UUID on PostgreSQL and String on SQLite/others.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        from uuid import UUID

        return UUID(value) if isinstance(value, str) else value


# Naming convention for constraints (helps with migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base with custom metadata."""

    metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        result: dict[str, Any] = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result


class UUIDMixin:
    """Mixin for UUID primary keys."""

    id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

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
