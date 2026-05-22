"""Pytest configuration for IPC handler tests.

This module sets up the database manager properly for IPC handler tests,
which use the global db_manager singleton.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scenemachine.database import get_db_manager, reset_db_manager
from scenemachine.models.base import Base
from tests.sqlite_compat import create_all_tables_sqlite


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a database session that works with IPC handlers.

    This fixture:
    1. Resets any existing db_manager
    2. Creates a new in-memory SQLite database
    3. Initializes the global db_manager with it
    4. Yields a session from that db_manager
    5. Cleans up on teardown
    """
    # Reset any existing db_manager
    reset_db_manager()

    # Create in-memory SQLite engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create tables with SQLite compatibility
    await create_all_tables_sqlite(engine, Base)

    # Get the db_manager and configure it
    db_manager = get_db_manager()
    db_manager._engine = engine
    db_manager._session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create a session for fixture data creation
    # Use session factory directly to avoid context manager's rollback
    session = db_manager._session_factory()
    try:
        yield session
    finally:
        await session.close()
        # Cleanup
        await engine.dispose()
        reset_db_manager()
