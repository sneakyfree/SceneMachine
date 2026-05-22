#!/usr/bin/env python3
"""
SQLite Compatibility Layer for Testing.

This module provides utilities to make PostgreSQL-specific model definitions
work with SQLite for testing purposes. It patches ARRAY columns to use JSON.
"""

import contextlib
import json
from typing import Any

from sqlalchemy import JSON, TypeDecorator, event
from sqlalchemy.engine import Engine


class JSONEncodedList(TypeDecorator):
    """SQLite-compatible replacement for PostgreSQL ARRAY.

    Stores list data as JSON text in SQLite.
    """
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: list[Any] | None, dialect) -> str | None:
        """Convert Python list to JSON string for storage."""
        if value is None:
            return None
        return value if isinstance(value, list) else []

    def process_result_value(self, value: str | None, dialect) -> list[Any] | None:
        """Convert stored JSON string back to Python list."""
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return []


def patch_models_for_sqlite():
    """
    Patch SQLAlchemy models to use JSON instead of PostgreSQL ARRAY.

    This must be called BEFORE importing models if you want to use SQLite.
    """
    from sqlalchemy import Column

    # Store original ARRAY for reference

    # Create a patched Column that replaces ARRAY with JSON

    class PatchedColumn(Column):
        """Column that auto-converts ARRAY to JSON."""
        pass

    # We'll use a different approach - patch at the Base metadata level
    return JSONEncodedList


def create_sqlite_compatible_tables(engine, base):
    """
    Create tables in SQLite by modifying the metadata to use JSON instead of ARRAY.

    Args:
        engine: SQLAlchemy engine (async or sync)
        base: SQLAlchemy declarative base (Base)
    """
    from sqlalchemy import JSON, Column, MetaData, Table

    # Create a new metadata that will hold modified table definitions
    new_metadata = MetaData()

    for table_name, table in base.metadata.tables.items():
        new_columns = []
        for column in table.columns:
            # Check if this column uses ARRAY type
            col_type = column.type

            # Handle ARRAY columns
            if hasattr(col_type, '__class__') and col_type.__class__.__name__ == 'ARRAY':
                # Replace with JSON
                new_col = Column(
                    column.name,
                    JSON,
                    nullable=column.nullable,
                    default=column.default.arg if column.default is not None else None,
                    primary_key=column.primary_key,
                )
            else:
                # Copy the column as-is
                new_col = column._copy()

            new_columns.append(new_col)

        # Create new table with modified columns
        # Note: This is a simplified approach - we keep original constraints
        Table(
            table_name,
            new_metadata,
            *new_columns,
            extend_existing=True,
        )

    return new_metadata


def get_sqlite_compatible_metadata(base):
    """
    Get a modified metadata object that's compatible with SQLite.

    Replaces ARRAY types with JSON types in all table definitions.
    """
    from sqlalchemy import (
        JSON,
        Column,
        ForeignKey,
        MetaData,
        String,
        Table,
    )

    new_metadata = MetaData()

    for table_name, table in base.metadata.tables.items():
        new_columns = []

        for column in table.columns:
            col_type = column.type
            col_type_name = col_type.__class__.__name__

            # Determine the new type
            if col_type_name == 'ARRAY':
                # Replace ARRAY with JSON
                new_type = JSON()
            elif col_type_name == 'JSONB':
                # Replace JSONB with JSON
                new_type = JSON()
            elif col_type_name == 'UUID':
                # Replace PostgreSQL UUID with String(36)
                new_type = String(36)
            else:
                # Keep original type
                new_type = col_type

            # Build foreign keys list
            fks = []
            for fk in column.foreign_keys:
                fks.append(ForeignKey(fk.target_fullname, ondelete=fk.ondelete))

            # Create new column
            new_col = Column(
                column.name,
                new_type,
                *fks,
                nullable=column.nullable,
                primary_key=column.primary_key,
                autoincrement=column.autoincrement if hasattr(column, 'autoincrement') else False,
            )

            # Copy default if present
            if column.default is not None and hasattr(column.default, 'arg'):
                new_col.default = column.default

            new_columns.append(new_col)

        # Create new table
        Table(table_name, new_metadata, *new_columns)

    return new_metadata


async def create_all_tables_sqlite(engine, base):
    """
    Create all tables with SQLite-compatible types.

    This is the main function to use for creating test databases.
    """
    from sqlalchemy import (
        text,
    )

    async with engine.begin() as conn:
        # Get all table names from the base metadata
        for table_name, table in base.metadata.tables.items():
            # Build CREATE TABLE statement manually for SQLite compatibility
            columns = []
            foreign_keys = []

            for column in table.columns:
                col_type = column.type
                col_type_name = col_type.__class__.__name__

                # Map PostgreSQL types to SQLite types
                if col_type_name == 'ARRAY' or col_type_name == 'JSONB':
                    sql_type = "TEXT"  # Store as JSON text
                elif col_type_name == 'UUID':
                    sql_type = "VARCHAR(36)"
                elif col_type_name in ('String', 'VARCHAR'):
                    length = getattr(col_type, 'length', None)
                    sql_type = f"VARCHAR({length})" if length else "TEXT"
                elif col_type_name == 'Integer':
                    sql_type = "INTEGER"
                elif col_type_name == 'Float':
                    sql_type = "REAL"
                elif col_type_name == 'Boolean':
                    sql_type = "INTEGER"  # SQLite has no native boolean
                elif col_type_name == 'Text':
                    sql_type = "TEXT"
                elif col_type_name == 'DateTime':
                    sql_type = "TIMESTAMP"
                elif col_type_name == 'Enum':
                    sql_type = "VARCHAR(50)"
                elif col_type_name == 'JSON':
                    sql_type = "TEXT"
                else:
                    sql_type = "TEXT"  # Default fallback

                # Build column definition
                col_def = f'"{column.name}" {sql_type}'

                if column.primary_key:
                    col_def += " PRIMARY KEY"

                # Handle server_default (for created_at, updated_at)
                if column.server_default is not None:
                    # Check if it's a func.now() or similar
                    default_text = str(column.server_default.arg)
                    if 'now()' in default_text.lower() or 'current_timestamp' in default_text.lower():
                        col_def += " DEFAULT CURRENT_TIMESTAMP"
                    elif 'uuid' in default_text.lower():
                        # Skip UUID generation - handled by Python
                        pass
                    else:
                        # Try to use the default as-is
                        col_def += f" DEFAULT {default_text}"
                elif column.default is not None:
                    # Handle Python-side defaults (won't be used for new rows)
                    # We add a NULL default for non-required fields
                    pass

                if not column.nullable and not column.primary_key:
                    # For timestamp columns with server_default, we still make them NOT NULL
                    # but we already added DEFAULT so this should work
                    col_def += " NOT NULL"

                # Handle foreign keys
                for fk in column.foreign_keys:
                    target = fk.target_fullname
                    target_table, target_col = target.rsplit('.', 1)
                    ondelete = f" ON DELETE {fk.ondelete}" if fk.ondelete else ""
                    foreign_keys.append(
                        f'FOREIGN KEY ("{column.name}") REFERENCES "{target_table}"("{target_col}"){ondelete}'
                    )

                columns.append(col_def)

            # Combine columns and foreign keys
            all_defs = columns + foreign_keys

            # Create table
            create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(all_defs)})'

            try:
                await conn.execute(text(create_sql))
            except Exception as e:
                print(f"Error creating table {table_name}: {e}")
                print(f"SQL: {create_sql}")
                raise


def enable_sqlite_foreign_keys(engine):
    """Enable foreign key support in SQLite."""
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def serialize_for_sqlite(value, is_sqlite: bool = True):
    """
    Serialize a value for SQLite storage.

    For SQLite, lists and dicts are serialized to JSON strings.
    For PostgreSQL, values are passed through unchanged.
    """
    if not is_sqlite:
        return value

    if value is None:
        return None
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, dict):
        return json.dumps(value)
    return value


def deserialize_from_sqlite(value, is_sqlite: bool = True):
    """
    Deserialize a value from SQLite storage.

    For SQLite, JSON strings are parsed back to lists/dicts.
    For PostgreSQL, values are passed through unchanged.
    """
    if not is_sqlite:
        return value

    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


class SQLiteTestDatabase:
    """
    A test database manager that handles SQLite compatibility.

    Usage:
        db = SQLiteTestDatabase("sqlite+aiosqlite:///test.db")
        await db.create_tables()
        async with db.session() as session:
            # Use session...
    """

    def __init__(self, database_url: str):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._tables_created = False

    async def create_tables(self):
        """Create all tables with SQLite-compatible types."""
        if self._tables_created:
            return

        from scenemachine.models.base import Base

        await create_all_tables_sqlite(self.engine, Base)
        self._tables_created = True

    async def drop_tables(self):
        """Drop all tables."""
        from sqlalchemy import text

        from scenemachine.models.base import Base

        async with self.engine.begin() as conn:
            # Get all table names in reverse order for foreign key safety
            tables = list(Base.metadata.tables.keys())
            for table_name in reversed(tables):
                with contextlib.suppress(Exception):
                    await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

        self._tables_created = False

    def session(self):
        """Get a new async session."""
        return self.session_factory()

    async def close(self):
        """Close the database connection."""
        await self.engine.dispose()
