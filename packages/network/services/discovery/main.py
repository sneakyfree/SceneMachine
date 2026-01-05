"""
Discovery service for SceneMachine Network.

Handles search, categories, tags, and recommendations.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import settings
from ...shared.database import init_db, close_db
from .routes.search import router as search_router
from .routes.categories import router as categories_router
from .routes.recommendations import router as recommendations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="SceneMachine Network - Discovery Service",
    description="Search, categories, tags, and recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search_router)
app.include_router(categories_router)
app.include_router(recommendations_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "discovery"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
