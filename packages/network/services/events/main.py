"""
Events Service for SceneMachine Network.

Handles CoreCast competitions, badge system, and Performers Association.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import get_settings
from ...shared.database import close_db, init_db
from .routes.badges import router as badges_router
from .routes.corecast import router as corecast_router
from .routes.performers_association import router as performers_association_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} Events Service...")
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
        title=f"{settings.app_name} - Events Service",
        description="CoreCast competitions, badges, and Performers Association for SceneMachine Network",
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
    app.include_router(corecast_router)
    app.include_router(badges_router)
    app.include_router(performers_association_router)

    # Health check
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "events",
            "version": settings.app_version,
            "features": ["corecast", "badges", "performers_association"],
        }

    # Service info
    @app.get("/")
    async def service_info() -> dict:
        """Service information."""
        return {
            "service": "events",
            "description": "Competitions and achievements for SceneMachine Network",
            "features": {
                "corecast": {
                    "description": "Monthly $100k film competitions",
                    "prize_pool": "$100,000 USD",
                    "distribution": {
                        "1st": "$50,000 (50%)",
                        "2nd": "$25,000 (25%)",
                        "3rd": "$10,000 (10%)",
                        "4th-10th": "$15,000 (15%)",
                    },
                    "phases": [
                        "submissions_open",
                        "voting",
                        "judging",
                        "completed",
                    ],
                },
                "badges": {
                    "categories": ["competition", "special", "association"],
                    "competition_badges": [
                        "Gold (1st place)",
                        "Silver (2nd place)",
                        "Bronze (3rd place)",
                        "Finalist (Top 10)",
                        "Top 25",
                        "Top 50",
                        "Top 100",
                        "Participant",
                    ],
                    "special_badges": [
                        "People's Choice",
                        "Rising Star",
                        "Innovation",
                        "Technical Excellence",
                        "Best Storytelling",
                        "Visual Excellence",
                    ],
                },
                "performers_association": {
                    "tiers": [
                        {
                            "name": "Emerging",
                            "requirements": "1 video",
                            "fee_reduction": "0%",
                        },
                        {
                            "name": "Established",
                            "requirements": "5 videos, 10k views, $100 earnings",
                            "fee_reduction": "2%",
                        },
                        {
                            "name": "Professional",
                            "requirements": "20 videos, 100k views, $5k earnings",
                            "fee_reduction": "5%",
                        },
                        {
                            "name": "Elite",
                            "requirements": "50 videos, 1M views, $50k earnings, 1 CoreCast win",
                            "fee_reduction": "10%",
                        },
                        {
                            "name": "Legend",
                            "requirements": "100 videos, 10M views, $500k earnings, 3 CoreCast wins",
                            "fee_reduction": "15%",
                        },
                    ],
                },
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
        port=8011,  # Events service port
        reload=settings.debug,
    )
