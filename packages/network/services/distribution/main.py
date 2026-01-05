"""
Distribution Service for SceneMachine Network.

Handles StoryHeaven (short-form) and MovieHeaven (long-form) content distribution,
film festivals, and studio exports.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import get_settings
from ...shared.database import close_db, init_db
from .routes.exports import router as exports_router
from .routes.festivals import router as festivals_router
from .routes.movie_heaven import router as movie_heaven_router
from .routes.story_heaven import router as story_heaven_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} Distribution Service...")
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
        title=f"{settings.app_name} - Distribution Service",
        description="Content distribution for SceneMachine Network (StoryHeaven & MovieHeaven)",
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
    app.include_router(story_heaven_router)
    app.include_router(movie_heaven_router)
    app.include_router(festivals_router)
    app.include_router(exports_router)

    # Health check
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "distribution",
            "version": settings.app_version,
            "channels": ["story_heaven", "movie_heaven"],
        }

    # Service info
    @app.get("/")
    async def service_info() -> dict:
        """Service information."""
        return {
            "service": "distribution",
            "description": "Content distribution for SceneMachine Network",
            "channels": {
                "story_heaven": {
                    "name": "StoryHeaven",
                    "type": "short-form",
                    "max_duration": "10 minutes",
                    "formats": ["9:16", "1:1", "16:9"],
                },
                "movie_heaven": {
                    "name": "MovieHeaven",
                    "type": "long-form",
                    "min_duration": "10 minutes",
                    "formats": ["16:9", "2.35:1", "1.43:1"],
                    "monetization": ["free", "ppv", "rental", "subscription"],
                },
            },
            "features": {
                "story_heaven": [
                    "Trending feed",
                    "For You recommendations",
                    "Duets and responses",
                    "Sound/audio reuse",
                    "Hashtag discovery",
                    "Viral threshold tracking",
                ],
                "movie_heaven": [
                    "Pay-per-view purchases",
                    "Timed rentals",
                    "Subscription tiers (Basic/Premium/Ultimate)",
                    "Film festival circuit",
                    "Premiere scheduling",
                    "4K/HDR/Dolby Atmos support",
                    "Critic and audience ratings",
                ],
                "festivals": [
                    "Virtual film festivals",
                    "Submission management",
                    "Judge scoring",
                    "Prize distribution",
                    "Winner showcases",
                ],
            },
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
        port=8010,  # Distribution service port
        reload=settings.debug,
    )
