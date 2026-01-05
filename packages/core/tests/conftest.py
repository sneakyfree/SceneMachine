"""Pytest configuration and shared fixtures."""

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from scenemachine.models.base import Base
from scenemachine.models import Project, ProjectState
from tests.sqlite_compat import create_all_tables_sqlite


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine() -> AsyncGenerator[Any, None]:
    """Create a test database engine with SQLite compatibility."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Use SQLite-compatible table creation to handle ARRAY types
    await create_all_tables_sqlite(engine, Base)

    yield engine

    # Clean up - drop all tables
    async with engine.begin() as conn:
        tables = list(Base.metadata.tables.keys())
        for table_name in reversed(tables):
            try:
                await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
            except Exception:
                pass

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest_asyncio.fixture
async def sample_project(db_session: AsyncSession) -> Project:
    """Create a sample project for testing."""
    project = Project(
        name="Sample Test Project",
        description="A sample project for testing",
        state=ProjectState.SCREENPLAY_PARSED,
        settings={
            "visual_style": "cinematic",
            "aspect_ratio": "16:9",
        },
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project
