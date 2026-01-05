"""Database connection and session management."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from scenemachine.config import get_settings
from scenemachine.models.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions.

    Provides async database session management with connection pooling.
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        """Initialize database manager.

        Args:
            database_url: Database connection URL. If not provided,
                         uses settings.database_url.
        """
        settings = get_settings()
        self._database_url = database_url or settings.database_url
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine, creating it if necessary."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    async def initialize(self) -> None:
        """Initialize the database connection.

        Creates the engine and session factory. Should be called once
        at application startup.
        """
        settings = get_settings()

        # Convert sync URL to async if needed
        url = self._database_url
        if url.startswith("sqlite:///"):
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        logger.info(f"Initializing database connection: {url.split('@')[-1]}")

        self._engine = create_async_engine(
            url,
            echo=settings.database_echo,
            pool_pre_ping=True,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        # Create tables if they don't exist (for SQLite/development)
        if settings.is_development:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")

    async def close(self) -> None:
        """Close database connections.

        Should be called at application shutdown.
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session context manager.

        Yields a session and handles commit/rollback automatically.

        Example:
            async with db_manager.session() as session:
                result = await session.execute(query)
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Creates a new instance if one doesn't exist.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def reset_db_manager() -> None:
    """Reset the global database manager.

    Useful for testing or reconfiguration.
    """
    global _db_manager
    _db_manager = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper for getting a database session.

    Use with FastAPI Depends() for automatic session management.

    Example:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    db_manager = get_db_manager()
    async with db_manager.session() as session:
        yield session
