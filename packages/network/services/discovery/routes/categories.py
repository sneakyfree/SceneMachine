"""
Category and tag routes for discovery service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import ContentType, User, Video, VideoStatus
from ...auth.dependencies import get_optional_user
from ..schemas import (
    VideoSearchResult,
    CategoryResponse,
    CategoryListResponse,
    TrendingTagResponse,
    TrendingTagsResponse,
)

router = APIRouter(tags=["categories"])


# Content type display names
CONTENT_TYPE_NAMES = {
    ContentType.FILM: "Films",
    ContentType.SERIES: "Series",
    ContentType.SHORT: "Short Films",
    ContentType.ANIMATION: "Animation",
    ContentType.MUSIC_VIDEO: "Music Videos",
    ContentType.CLIP: "Clips",
    ContentType.OTHER: "Other",
}


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


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> CategoryListResponse:
    """
    List all content categories with counts and recent videos.
    """
    categories = []

    for content_type in ContentType:
        # Count videos in category
        result = await db.execute(
            select(func.count()).where(
                and_(
                    Video.content_type == content_type,
                    Video.status == VideoStatus.PUBLISHED,
                )
            )
        )
        video_count = result.scalar() or 0

        if video_count == 0:
            continue  # Skip empty categories

        # Get recent videos
        result = await db.execute(
            select(Video)
            .where(
                and_(
                    Video.content_type == content_type,
                    Video.status == VideoStatus.PUBLISHED,
                )
            )
            .order_by(Video.quality_score.desc())
            .limit(6)
        )
        videos = result.scalars().all()

        recent_videos = []
        for video in videos:
            video_result = await _build_video_search_result(video, db)
            recent_videos.append(video_result)

        categories.append(
            CategoryResponse(
                content_type=content_type,
                display_name=CONTENT_TYPE_NAMES.get(content_type, content_type.value),
                video_count=video_count,
                recent_videos=recent_videos,
            )
        )

    # Sort by video count
    categories.sort(key=lambda c: c.video_count, reverse=True)

    return CategoryListResponse(categories=categories)


@router.get("/categories/{content_type}")
async def get_category(
    content_type: ContentType,
    sort: str = Query("trending", regex="^(trending|newest|views)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get videos in a specific category."""
    # Count total
    result = await db.execute(
        select(func.count()).where(
            and_(
                Video.content_type == content_type,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
    )
    total = result.scalar() or 0

    # Build query with sorting
    query = select(Video).where(
        and_(
            Video.content_type == content_type,
            Video.status == VideoStatus.PUBLISHED,
        )
    )

    if sort == "trending":
        query = query.order_by(Video.quality_score.desc())
    elif sort == "newest":
        query = query.order_by(Video.published_at.desc())
    elif sort == "views":
        query = query.order_by(Video.view_count.desc())

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    videos = result.scalars().all()

    # Build results
    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return {
        "content_type": content_type,
        "display_name": CONTENT_TYPE_NAMES.get(content_type, content_type.value),
        "videos": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": (offset + len(results)) < total,
    }


@router.get("/tags/trending", response_model=TrendingTagsResponse)
async def get_trending_tags(
    period: str = Query("week", regex="^(day|week|month)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> TrendingTagsResponse:
    """
    Get trending tags based on recent video uploads and views.
    """
    # Determine time range
    now = datetime.now(timezone.utc)
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    else:  # month
        since = now - timedelta(days=30)

    # Get tags with video counts and view counts
    # This uses PostgreSQL unnest to expand the tags array
    result = await db.execute(
        select(
            func.unnest(Video.tags).label("tag"),
            func.count(Video.id).label("video_count"),
            func.sum(Video.view_count).label("view_count"),
        )
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.published_at >= since,
            )
        )
        .group_by(func.unnest(Video.tags))
        .order_by(func.sum(Video.view_count).desc())
        .limit(limit)
    )
    rows = result.all()

    # Calculate trend scores
    tags = []
    max_views = max((row.view_count or 0 for row in rows), default=1)

    for row in rows:
        # Trend score based on normalized views and video count
        view_score = (row.view_count or 0) / max_views * 50
        count_score = min(row.video_count * 5, 50)
        trend_score = view_score + count_score

        tags.append(
            TrendingTagResponse(
                tag=row.tag,
                video_count=row.video_count,
                view_count=row.view_count or 0,
                trend_score=round(trend_score, 2),
            )
        )

    return TrendingTagsResponse(tags=tags)


@router.get("/tags/{tag}")
async def get_tag_videos(
    tag: str,
    sort: str = Query("trending", regex="^(trending|newest|views)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get videos with a specific tag."""
    tag_lower = tag.lower()

    # Count total
    result = await db.execute(
        select(func.count()).where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.tags.any(tag_lower),
            )
        )
    )
    total = result.scalar() or 0

    # Build query
    query = select(Video).where(
        and_(
            Video.status == VideoStatus.PUBLISHED,
            Video.tags.any(tag_lower),
        )
    )

    if sort == "trending":
        query = query.order_by(Video.quality_score.desc())
    elif sort == "newest":
        query = query.order_by(Video.published_at.desc())
    elif sort == "views":
        query = query.order_by(Video.view_count.desc())

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    videos = result.scalars().all()

    # Build results
    results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        results.append(video_result)

    return {
        "tag": tag,
        "videos": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": (offset + len(results)) < total,
    }
