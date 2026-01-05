"""
Studio integration service for SceneMachine Network.

Provides API endpoints for the SceneMachine Studio desktop application
to publish content directly to the Network platform.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import settings
from ...shared.database import init_db, close_db
from .routes import router as studio_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="SceneMachine Network - Studio Integration",
    description="API for SceneMachine Studio desktop application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - Allow Studio desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["tauri://localhost", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(studio_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "studio-integration"}


@app.get("/version")
async def get_version():
    """Get API version for Studio compatibility check."""
    return {
        "api_version": "1.0.0",
        "min_studio_version": "1.0.0",
        "features": [
            "publish",
            "analytics",
            "monetization",
            "social",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
