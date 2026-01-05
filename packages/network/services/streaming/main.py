"""
Streaming Service for SceneMachine Network.

Handles video playback, progress tracking, and view counting.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import get_settings
from ...shared.database import close_db, init_db
from .routes.stream import router as stream_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} Streaming Service...")
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")

    # Initialize database
    await init_db()
    print("Database initialized")

    yield

    # Shutdown
    await close_db()
    print("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} - Streaming Service",
        description="Video playback and streaming for SceneMachine Network",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(stream_router)

    # Health check
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "streaming",
            "version": settings.app_version,
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.debug,
    )
