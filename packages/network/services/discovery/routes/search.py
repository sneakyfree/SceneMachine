"""
Search routes for discovery service.
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
    User,
    Video,
    VideoStatus,
    CreatorProfile,
)
from ...auth.dependencies import get_optional_user
from ..schemas import (
    VideoSearchResult,
    SearchResponse,
    CreatorSearchResult,
    CreatorSearchResponse,
    AutocompleteResponse,
)

router = APIRouter(prefix="/search", tags=["search"])


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


@router.get("/videos", response_model=SearchResponse)
async def search_videos(
    q: str = Query(..., min_length=1, max_length=200),
    content_type: Optional[ContentType] = Query(None),
    duration_min: Optional[int] = Query(None, ge=0),
    duration_max: Optional[int] = Query(None, ge=0),
    upload_date: Optional[str] = Query(
        None, regex="^(today|week|month|year)$"
    ),
    sort: str = Query("relevance", regex="^(relevance|date|views|rating)$"),
    made_with_studio: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Search videos with filters.

    Supports:
    - Full-text search on title, description, tags
    - Content type filtering
    - Duration filtering
    - Upload date filtering
    - Made with Studio badge filtering
    - Multiple sort options
    """
    # Base query
    query = select(Video).where(Video.status == VideoStatus.PUBLISHED)

    # Text search (simple ILIKE for now, Elasticsearch for production)
    search_pattern = f"%{q}%"
    query = query.where(
        or_(
            Video.title.ilike(search_pattern),
            Video.description.ilike(search_pattern),
            Video.tags.any(q.lower()),  # PostgreSQL array contains
        )
    )

    # Content type filter
    if content_type:
        query = query.where(Video.content_type == content_type)

    # Duration filter
    if duration_min is not None:
        query = query.where(Video.duration_seconds >= duration_min)
    if duration_max is not None:
        query = query.where(Video.duration_seconds <= duration_max)

    # Upload date filter
    if upload_date:
        now = datetime.now(timezone.utc)
        if upload_date == "today":
            since = now - timedelta(days=1)
        elif upload_date == "week":
            since = now - timedelta(days=7)
        elif upload_date == "month":
            since = now - timedelta(days=30)
        else:  # year
            since = now - timedelta(days=365)
        query = query.where(Video.published_at >= since)

    # Made with Studio filter
    if made_with_studio is not None:
        query = query.where(Video.made_with_studio == made_with_studio)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Sorting
    if sort == "relevance":
        # For simple relevance, prioritize title matches and quality score
        query = query.order_by(
            Video.title.ilike(f"{q}%").desc(),  # Prefix matches first
            Video.quality_score.desc(),
        )
    elif sort == "date":
        query = query.order_by(Video.published_at.desc())
    elif sort == "views":
        query = query.order_by(Video.view_count.desc())
    elif sort == "rating":
        query = query.order_by(Video.quality_score.desc())

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    videos = result.scalars().all()

    # Build results
    results = []
    for video in videos:
        result = await _build_video_search_result(video, db)
        results.append(result)

    filters_applied = {
        "content_type": content_type.value if content_type else None,
        "duration_min": duration_min,
        "duration_max": duration_max,
        "upload_date": upload_date,
        "made_with_studio": made_with_studio,
        "sort": sort,
    }

    return SearchResponse(
        results=results,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(results)) < total,
        query=q,
        filters_applied=filters_applied,
    )


@router.get("/creators", response_model=CreatorSearchResponse)
async def search_creators(
    q: str = Query(..., min_length=1, max_length=200),
    verified_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> CreatorSearchResponse:
    """Search creators by username, display name, or bio."""
    # Base query for creators (users with at least one video)
    search_pattern = f"%{q}%"
    query = (
        select(User, CreatorProfile)
        .outerjoin(CreatorProfile, CreatorProfile.user_id == User.id)
        .where(
            and_(
                User.is_creator == True,
                or_(
                    User.username.ilike(search_pattern),
                    User.display_name.ilike(search_pattern),
                    User.bio.ilike(search_pattern),
                ),
            )
        )
    )

    if verified_only:
        query = query.where(User.is_verified == True)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Sort by subscriber count
    query = query.order_by(
        func.coalesce(CreatorProfile.subscriber_count, 0).desc()
    )

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    # Get video counts and total views for each creator
    results = []
    for user, profile in rows:
        # Count videos
        video_count_result = await db.execute(
            select(func.count()).where(
                and_(
                    Video.creator_id == user.id,
                    Video.status == VideoStatus.PUBLISHED,
                )
            )
        )
        video_count = video_count_result.scalar() or 0

        # Sum views
        view_count_result = await db.execute(
            select(func.sum(Video.view_count)).where(
                and_(
                    Video.creator_id == user.id,
                    Video.status == VideoStatus.PUBLISHED,
                )
            )
        )
        total_views = view_count_result.scalar() or 0

        results.append(
            CreatorSearchResult(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                bio=user.bio,
                is_verified=user.is_verified,
                subscriber_count=profile.subscriber_count if profile else 0,
                video_count=video_count,
                total_views=total_views,
            )
        )

    return CreatorSearchResponse(
        results=results,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(results)) < total,
    )


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def search_autocomplete(
    q: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    """
    Get autocomplete suggestions for search.
    Returns matching video titles, tags, and creators.
    """
    search_pattern = f"%{q}%"
    suggestions = set()

    # Get matching video titles
    result = await db.execute(
        select(Video.title)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.title.ilike(search_pattern),
            )
        )
        .limit(5)
    )
    for (title,) in result.all():
        suggestions.add(title)

    # Get matching tags
    result = await db.execute(
        select(func.unnest(Video.tags).label("tag"))
        .where(Video.status == VideoStatus.PUBLISHED)
        .distinct()
        .limit(100)
    )
    for (tag,) in result.all():
        if q.lower() in tag.lower():
            suggestions.add(tag)
            if len(suggestions) >= 10:
                break

    # Get top 3 matching videos
    result = await db.execute(
        select(Video)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.title.ilike(search_pattern),
            )
        )
        .order_by(Video.quality_score.desc())
        .limit(3)
    )
    videos = result.scalars().all()
    video_results = []
    for video in videos:
        video_result = await _build_video_search_result(video, db)
        video_results.append(video_result)

    # Get top 2 matching creators
    result = await db.execute(
        select(User, CreatorProfile)
        .outerjoin(CreatorProfile, CreatorProfile.user_id == User.id)
        .where(
            and_(
                User.is_creator == True,
                or_(
                    User.username.ilike(search_pattern),
                    User.display_name.ilike(search_pattern),
                ),
            )
        )
        .order_by(func.coalesce(CreatorProfile.subscriber_count, 0).desc())
        .limit(2)
    )
    rows = result.all()
    creator_results = []
    for user, profile in rows:
        creator_results.append(
            CreatorSearchResult(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                bio=user.bio,
                is_verified=user.is_verified,
                subscriber_count=profile.subscriber_count if profile else 0,
                video_count=0,  # Skip counting for autocomplete
                total_views=0,
            )
        )

    return AutocompleteResponse(
        suggestions=list(suggestions)[:10],
        videos=video_results,
        creators=creator_results,
    )
