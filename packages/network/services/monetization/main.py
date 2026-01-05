"""
Monetization service for SceneMachine Network.

Handles earnings, payments, tips, and payouts.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...shared.config import settings
from ...shared.database import init_db, close_db
from .routes.earnings import router as earnings_router
from .routes.payments import router as payments_router
from .routes.payouts import router as payouts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="SceneMachine Network - Monetization Service",
    description="Earnings, payments, tips, and payouts",
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
app.include_router(earnings_router)
app.include_router(payments_router)
app.include_router(payouts_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "monetization"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
