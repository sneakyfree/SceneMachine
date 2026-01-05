"""
Recommendation routes for discovery service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    ContentType,
    Follow,
    User,
    Video,
    VideoStatus,
    WatchHistory,
)
from ...auth.dependencies import get_current_user, get_optional_user
from ..schemas import VideoSearchResult, RecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


async def _build_video_search_result(
    video: Video,
    db: AsyncSession,
) -> VideoSearchResult:
    """Build a video search result with creator info."""
    result = await db.execute(select(User).where(User.id == video.creator_id))
    creator = result.scalar_one()

    return VideoSearchResult(
        id=video.id,
        title=video.title,
        description=video.description,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=video.duration_seconds,
        creator_id=video.creator_id,
        creator_name=creator.display_name,
        creator_avatar=creator.avatar_url,
        content_type=video.content_type,
        view_count=video.view_count,
        like_count=video.like_count,
        quality_score=video.quality_score,
        published_at=video.published_at,
        made_with_studio=video.made_with_studio,
    )


@router.get("/similar/{video_id}", response_model=RecommendationResponse)
async def get_similar_videos(
    video_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Get videos similar to a given video.

    Similarity based on:
    - Same content type
    - Overlapping tags
    - Same creator
    """
    # Get the source video
    result = await db.execute(select(Video).where(Video.id == video_id))
    source_video = result.scalar_one_or_none()
    if not source_video:
        return RecommendationResponse(videos=[], reason="similar_to")

    # Find similar videos
    query = (
        select(Video)
        .where(
            and_(
                Video.id != video_id,
                Video.status == VideoStatus.PUBLISHED,
                or_(
                    # Same content type
                    Video.content_type == source_video.content_type,
                    # Same creator
                    Video.creator_id == source_video.creator_id,
                    # Overlapping tags (any tag matches)
                    *[Video.tags.any(tag) for tag in source_video.tags[:5]],
                ),
            )
        )
        .order_by(
            # Prioritize same creator
            (Video.creator_id == source_video.creator_id).desc(),
            # Then by quality score
            Video.quality_score.desc(),
        )
        .limit(limit)
    )

    result = await db.execute(query)
    videos = result.scalars().all()

    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return RecommendationResponse(
        videos=results,
        reason=f"similar_to:{source_video.title[:50]}",
    )


@router.get("/for-you", response_model=RecommendationResponse)
async def get_for_you_recommendations(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Get personalized recommendations based on watch history.
    """
    # Get user's watch history (content types and tags they've watched)
    result = await db.execute(
        select(Video.content_type, Video.tags)
        .join(WatchHistory, WatchHistory.video_id == Video.id)
        .where(WatchHistory.user_id == current_user.id)
        .order_by(WatchHistory.last_watched_at.desc())
        .limit(20)
    )
    history = result.all()

    if not history:
        # No history, return trending
        result = await db.execute(
            select(Video)
            .where(Video.status == VideoStatus.PUBLISHED)
            .order_by(Video.quality_score.desc())
            .limit(limit)
        )
        videos = result.scalars().all()
        results = []
        for video in videos:
            video_result = await _build_video_search_result(video, db)
            results.append(video_result)
        return RecommendationResponse(videos=results, reason="trending")

    # Extract preferred content types and tags
    preferred_types = set()
    preferred_tags = set()
    for content_type, tags in history:
        preferred_types.add(content_type)
        preferred_tags.update(tags[:3])  # Top 3 tags per video

    # Get watched video IDs to exclude
    result = await db.execute(
        select(WatchHistory.video_id).where(
            WatchHistory.user_id == current_user.id
        )
    )
    watched_ids = {row[0] for row in result.all()}

    # Find recommendations
    query = (
        select(Video)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.id.notin_(watched_ids),
                or_(
                    Video.content_type.in_(preferred_types),
                    *[Video.tags.any(tag) for tag in list(preferred_tags)[:10]],
                ),
            )
        )
        .order_by(Video.quality_score.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    videos = result.scalars().all()

    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return RecommendationResponse(
        videos=results,
        reason="because_you_watched",
    )


@router.get("/trending-in-genre/{content_type}", response_model=RecommendationResponse)
async def get_trending_in_genre(
    content_type: ContentType,
    period: str = Query("week", regex="^(day|week|month)$"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Get trending videos in a specific genre/content type.
    """
    # Determine time range
    now = datetime.now(timezone.utc)
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    else:  # month
        since = now - timedelta(days=30)

    # Get trending videos in genre
    query = (
        select(Video)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.content_type == content_type,
                Video.published_at >= since,
            )
        )
        .order_by(Video.quality_score.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    videos = result.scalars().all()

    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return RecommendationResponse(
        videos=results,
        reason=f"trending_in_{content_type.value}",
    )


@router.get("/from-following", response_model=RecommendationResponse)
async def get_from_following(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Get recent videos from creators the user follows.
    """
    # Get videos from followed creators
    query = (
        select(Video)
        .join(Follow, Follow.following_id == Video.creator_id)
        .where(
            and_(
                Follow.follower_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
        .order_by(Video.published_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    videos = result.scalars().all()

    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return RecommendationResponse(
        videos=results,
        reason="from_following",
    )


@router.get("/continue-watching", response_model=RecommendationResponse)
async def get_continue_watching(
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Get videos the user started but didn't finish.
    """
    # Get incomplete watch history
    query = (
        select(Video, WatchHistory)
        .join(WatchHistory, WatchHistory.video_id == Video.id)
        .where(
            and_(
                WatchHistory.user_id == current_user.id,
                WatchHistory.completed == False,
                WatchHistory.watch_percent >= 5,  # At least started watching
                WatchHistory.watch_percent < 90,  # But didn't finish
                Video.status == VideoStatus.PUBLISHED,
            )
        )
        .order_by(WatchHistory.last_watched_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    results = []
    for video, history in rows:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return RecommendationResponse(
        videos=results,
        reason="continue_watching",
    )


@router.get("/made-with-studio", response_model=RecommendationResponse)
async def get_made_with_studio(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Get top videos made with SceneMachine Studio.
    """
    query = (
        select(Video)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.made_with_studio == True,
            )
        )
        .order_by(Video.quality_score.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    videos = result.scalars().all()

    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return RecommendationResponse(
        videos=results,
        reason="made_with_studio",
    )
