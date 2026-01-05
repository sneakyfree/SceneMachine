"""
Quality score calculation for video discovery.

The quality score is a meritocratic ranking (0-100) that determines
video placement in feeds and search results.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...shared.models import Video, ViewEvent, WatchSession


async def calculate_quality_score(
    video: Video,
    db: AsyncSession,
) -> float:
    """
    Calculate a meritocratic quality score (0-100).
    Higher score = better discovery placement.

    Factors:
    - Engagement rate (likes/views): 15%
    - Watch time retention (avg watch % of completions): 30%
    - Growth velocity (recent views vs. age): 20%
    - Completion rate (views that finished): 25%
    - Share rate: 10%
    """
    if video.view_count == 0:
        return 0.0

    # Calculate view engagement (likes/views)
    view_engagement = (video.like_count / max(video.view_count, 1)) * 100
    view_engagement = min(view_engagement, 100)  # Cap at 100%

    # Calculate average watch retention
    result = await db.execute(
        select(func.avg(ViewEvent.watch_percent)).where(
            ViewEvent.video_id == video.id,
            ViewEvent.is_valid_view == True,
        )
    )
    avg_watch_percent = result.scalar() or 0
    retention_score = min(avg_watch_percent, 100)

    # Calculate growth velocity (views in last 7 days vs. lifetime)
    now = datetime.now(timezone.utc)
    age_days = max((now - video.created_at.replace(tzinfo=timezone.utc)).days, 1)

    result = await db.execute(
        select(func.count()).where(
            ViewEvent.video_id == video.id,
            ViewEvent.viewed_at >= now.replace(hour=0, minute=0, second=0)
            - __import__("datetime").timedelta(days=7),
            ViewEvent.is_valid_view == True,
        )
    )
    recent_views = result.scalar() or 0
    recent_velocity = (recent_views / age_days) if age_days > 0 else 0
    # Normalize velocity (expect ~10 views/day as baseline)
    velocity_score = min((recent_velocity / 10) * 100, 100)

    # Calculate completion rate
    result = await db.execute(
        select(func.count()).where(
            ViewEvent.video_id == video.id,
            ViewEvent.completed == True,
        )
    )
    completions = result.scalar() or 0
    completion_rate = (completions / max(video.view_count, 1)) * 100
    completion_rate = min(completion_rate, 100)

    # Calculate share rate
    share_rate = (video.share_count / max(video.view_count, 1)) * 1000  # Per 1000 views
    share_rate = min(share_rate, 100)

    # Weighted combination
    score = (
        view_engagement * 0.15
        + retention_score * 0.30
        + velocity_score * 0.20
        + completion_rate * 0.25
        + share_rate * 0.10
    )

    # Apply age decay (newer content gets a boost, but decays over time)
    # Full score for first 7 days, then gradual decay
    if age_days <= 7:
        age_factor = 1.0
    else:
        age_factor = 1 / (1 + (age_days - 7) / 365)

    final_score = score * age_factor

    return min(max(final_score, 0), 100)


async def update_video_quality_score(
    video_id: str,
    db: AsyncSession,
) -> float:
    """Update a video's quality score in the database."""
    from ...shared.models import Video

    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return 0.0

    new_score = await calculate_quality_score(video, db)
    video.quality_score = new_score
    await db.commit()

    return new_score


async def batch_update_quality_scores(
    db: AsyncSession,
    limit: int = 1000,
) -> int:
    """
    Batch update quality scores for videos.
    Called periodically by a background job.
    Returns number of videos updated.
    """
    from ...shared.models import Video, VideoStatus

    # Get videos that need score updates (published, recently active)
    result = await db.execute(
        select(Video)
        .where(Video.status == VideoStatus.PUBLISHED)
        .order_by(Video.updated_at.desc())
        .limit(limit)
    )
    videos = result.scalars().all()

    count = 0
    for video in videos:
        new_score = await calculate_quality_score(video, db)
        if abs(video.quality_score - new_score) > 0.1:  # Only update if changed
            video.quality_score = new_score
            count += 1

    await db.commit()
    return count
