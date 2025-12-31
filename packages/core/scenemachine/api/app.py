"""FastAPI application factory and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from scenemachine.api.middleware import (
    RateLimitConfig,
    RateLimitMiddleware,
    SecurityHeadersConfig,
    SecurityHeadersMiddleware,
    RequestValidationConfig,
    RequestValidationMiddleware,
)
from scenemachine.api.routes import (
    analytics,
    archive,
    assembly,
    characters,
    generation,
    health,
    movie_plan,
    projects,
    scenes,
    screenplay,
    settings,
    sharing,
    ws,
)
from scenemachine.config import Settings, get_settings
from scenemachine.database import get_db_manager

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests for tracing."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        """Add request ID header and process request."""
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown."""
    settings = get_settings()
    logger.info(f"Starting SceneMachine API v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize()
    logger.info("Database initialized")

    yield

    # Cleanup
    await db_manager.close()
    logger.info("SceneMachine API shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (useful for testing)

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="SceneMachine API",
        description="Screenplay-to-Movie Generation Platform",
        version=settings.version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Store settings in app state
    app.state.settings = settings

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Add security middleware (order matters - first added is last executed)
    # Request validation (size limits, blocked agents)
    app.add_middleware(
        RequestValidationMiddleware,
        config=RequestValidationConfig(
            max_body_size=100 * 1024 * 1024,  # 100MB for video uploads
        ),
    )

    # Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        config=SecurityHeadersConfig(
            hsts_enabled=not settings.debug,
        ),
    )

    # Rate limiting (only in production)
    if not settings.debug:
        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(
                requests_per_second=20,
                requests_per_minute=200,
                requests_per_hour=2000,
                burst_size=50,
                custom_limits={
                    "/api/v1/generation": (30, 60),  # 30 per minute for generation
                    "/api/v1/projects": (60, 60),  # 60 per minute for projects
                },
            ),
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(f"Unhandled exception [request_id={request_id}]: {exc}")

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else None,
                "code": "INTERNAL_ERROR",
                "request_id": request_id,
            },
        )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(
        projects.router,
        prefix="/api/v1/projects",
        tags=["Projects"],
    )
    app.include_router(
        screenplay.router,
        prefix="/api/v1",
        tags=["Screenplays"],
    )
    app.include_router(
        movie_plan.router,
        prefix="/api/v1",
        tags=["Movie Plans"],
    )
    app.include_router(
        characters.router,
        prefix="/api/v1",
        tags=["Characters"],
    )
    app.include_router(
        scenes.router,
        prefix="/api/v1",
        tags=["Scenes"],
    )
    app.include_router(
        generation.router,
        prefix="/api/v1",
        tags=["Generation"],
    )
    app.include_router(
        assembly.router,
        prefix="/api/v1",
        tags=["Assembly"],
    )
    app.include_router(
        ws.router,
        tags=["WebSocket"],
    )
    app.include_router(
        analytics.router,
        prefix="/api/v1/analytics",
        tags=["Analytics"],
    )
    app.include_router(
        sharing.router,
        prefix="/api/v1/sharing",
        tags=["Sharing"],
    )
    app.include_router(
        archive.router,
        prefix="/api/v1/archive",
        tags=["Archive"],
    )
    app.include_router(
        settings.router,
        prefix="/api/v1/settings",
        tags=["Settings"],
    )

    return app


# Default application instance
app = create_app()
