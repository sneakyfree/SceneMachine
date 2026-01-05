"""
Moderation Service for SceneMachine Network.

Handles content moderation, reports, appeals, and safety features.
Port: 8009
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...shared.config import settings
from ...shared.database import get_db, init_db
from ...shared.models import (
    Appeal,
    AppealStatus,
    ContentFlag,
    ModerationAction,
    Report,
    ReportStatus,
    Strike,
    User,
)
from ..auth.dependencies import get_current_user
from .routes import (
    reports_router,
    actions_router,
    strikes_router,
    appeals_router,
    flags_router,
)
from .schemas import ModerationStatsResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await init_db()
    yield


app = FastAPI(
    title="SceneMachine Moderation Service",
    description="Content moderation, reports, and safety for SceneMachine Network",
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
app.include_router(reports_router, prefix="/api/v1")
app.include_router(actions_router, prefix="/api/v1")
app.include_router(strikes_router, prefix="/api/v1")
app.include_router(appeals_router, prefix="/api/v1")
app.include_router(flags_router, prefix="/api/v1")


def _require_moderator(user: User) -> None:
    """Verify user is a moderator."""
    from fastapi import HTTPException, status
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "moderation"}


@app.get("/api/v1/stats", response_model=ModerationStatsResponse)
async def get_moderation_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModerationStatsResponse:
    """Get moderation statistics (moderator only)."""
    _require_moderator(current_user)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Pending reports
    result = await db.execute(
        select(func.count()).where(Report.status == ReportStatus.PENDING)
    )
    pending_reports = result.scalar() or 0

    # Reports today
    result = await db.execute(
        select(func.count()).where(
            and_(
                Report.created_at >= today_start,
            )
        )
    )
    reports_today = result.scalar() or 0

    # Reports this week
    result = await db.execute(
        select(func.count()).where(
            and_(
                Report.created_at >= week_start,
            )
        )
    )
    reports_this_week = result.scalar() or 0

    # Average resolution time (simplified)
    avg_resolution_hours = 0.0
    result = await db.execute(
        select(Report)
        .where(Report.reviewed_at != None)
        .order_by(Report.reviewed_at.desc())
        .limit(100)
    )
    recent_resolved = result.scalars().all()
    if recent_resolved:
        total_hours = sum(
            (r.reviewed_at - r.created_at).total_seconds() / 3600
            for r in recent_resolved
            if r.reviewed_at
        )
        avg_resolution_hours = total_hours / len(recent_resolved)

    # Actions today
    result = await db.execute(
        select(func.count()).where(
            ModerationAction.created_at >= today_start
        )
    )
    actions_today = result.scalar() or 0

    # Actions this week
    result = await db.execute(
        select(func.count()).where(
            ModerationAction.created_at >= week_start
        )
    )
    actions_this_week = result.scalar() or 0

    # Content removed today
    from ...shared.models import ActionType
    result = await db.execute(
        select(func.count()).where(
            and_(
                ModerationAction.action_type == ActionType.CONTENT_REMOVE,
                ModerationAction.created_at >= today_start,
            )
        )
    )
    content_removed_today = result.scalar() or 0

    # Accounts suspended today
    result = await db.execute(
        select(func.count()).where(
            and_(
                ModerationAction.action_type.in_([
                    ActionType.TEMP_BAN,
                    ActionType.PERM_BAN,
                ]),
                ModerationAction.created_at >= today_start,
            )
        )
    )
    accounts_suspended_today = result.scalar() or 0

    # Pending appeals
    result = await db.execute(
        select(func.count()).where(Appeal.status == AppealStatus.PENDING)
    )
    pending_appeals = result.scalar() or 0

    # Appeals approval rate
    result = await db.execute(
        select(
            func.count().filter(Appeal.status == AppealStatus.APPROVED),
            func.count().filter(Appeal.reviewed_at != None),
        )
    )
    row = result.one()
    approved, total_reviewed = row
    appeals_approved_rate = 0.0
    if total_reviewed > 0:
        appeals_approved_rate = approved / total_reviewed * 100

    # Pending flags
    result = await db.execute(
        select(func.count()).where(ContentFlag.reviewed_at == None)
    )
    pending_flags = result.scalar() or 0

    # False positive rate
    result = await db.execute(
        select(
            func.count().filter(ContentFlag.is_accurate == False),
            func.count().filter(ContentFlag.reviewed_at != None),
        )
    )
    row = result.one()
    false_positives, total_reviewed_flags = row
    false_positive_rate = 0.0
    if total_reviewed_flags > 0:
        false_positive_rate = false_positives / total_reviewed_flags * 100

    # Strikes issued today
    result = await db.execute(
        select(func.count()).where(Strike.created_at >= today_start)
    )
    strikes_issued_today = result.scalar() or 0

    # Accounts terminated today
    result = await db.execute(
        select(func.count()).where(
            and_(
                User.is_terminated == True,
                User.updated_at >= today_start,
            )
        )
    )
    accounts_terminated_today = result.scalar() or 0

    return ModerationStatsResponse(
        pending_reports=pending_reports,
        reports_today=reports_today,
        reports_this_week=reports_this_week,
        avg_resolution_hours=round(avg_resolution_hours, 1),
        actions_today=actions_today,
        actions_this_week=actions_this_week,
        content_removed_today=content_removed_today,
        accounts_suspended_today=accounts_suspended_today,
        pending_appeals=pending_appeals,
        appeals_approved_rate=round(appeals_approved_rate, 1),
        pending_flags=pending_flags,
        false_positive_rate=round(false_positive_rate, 1),
        strikes_issued_today=strikes_issued_today,
        accounts_terminated_today=accounts_terminated_today,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
