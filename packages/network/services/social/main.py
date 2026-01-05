"""
Social service for SceneMachine Network.

Handles follows, comments, reactions, watchlist, feed, and notifications.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import settings
from ...shared.database import init_db, close_db
from .routes.follows import router as follows_router
from .routes.comments import router as comments_router
from .routes.reactions import router as reactions_router
from .routes.watchlist import router as watchlist_router
from .routes.feed import router as feed_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="SceneMachine Network - Social Service",
    description="Social features: follows, comments, reactions, watchlist, feed",
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
app.include_router(follows_router)
app.include_router(comments_router)
app.include_router(reactions_router)
app.include_router(watchlist_router)
app.include_router(feed_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "social"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
