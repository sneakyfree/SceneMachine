"""FastAPI dependency injection functions."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import Settings, get_settings
from scenemachine.database import get_db_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session.

    Yields an async database session and ensures it's properly closed
    after the request completes.
    """
    db_manager = get_db_manager()
    async with db_manager.session() as session:
        yield session


async def get_current_settings() -> Settings:
    """Dependency to get current application settings."""
    return get_settings()


# Type aliases for cleaner dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_current_settings)]
