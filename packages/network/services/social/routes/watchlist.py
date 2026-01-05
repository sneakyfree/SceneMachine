"""
Watchlist routes for social service.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import Watchlist, User, Video
from ...auth.dependencies import get_current_user
from ..schemas import (
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistResponse,
    VideoSummary,
)

router = APIRouter(prefix="/me/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistResponse:
    """Get current user's watchlist."""
    # Count total
    count_query = select(func.count()).where(Watchlist.user_id == current_user.id)
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get watchlist items with video info
    offset = (page - 1) * per_page
    query = (
        select(Watchlist, Video, User)
        .join(Video, Watchlist.video_id == Video.id)
        .join(User, Video.creator_id == User.id)
        .where(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    rows = result.all()

    # Build responses
    items = []
    for watchlist_item, video, creator in rows:
        video_summary = VideoSummary(
            id=video.id,
            title=video.title,
            thumbnail_url=video.thumbnail_url,
            duration_seconds=video.duration_seconds,
            creator_id=video.creator_id,
            creator_name=creator.display_name,
            view_count=video.view_count,
            like_count=video.like_count,
        )
        items.append(
            WatchlistItemResponse(
                video_id=watchlist_item.video_id,
                user_id=watchlist_item.user_id,
                note=watchlist_item.note,
                created_at=watchlist_item.created_at,
                video=video_summary,
            )
        )

    return WatchlistResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(items)) < total,
    )


@router.post("/{video_id}", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    video_id: uuid.UUID,
    request: WatchlistAddRequest = WatchlistAddRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistItemResponse:
    """Add a video to watchlist."""
    # Check if video exists
    result = await db.execute(
        select(Video, User)
        .join(User, Video.creator_id == User.id)
        .where(Video.id == video_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    video, creator = row

    # Check if already in watchlist
    result = await db.execute(
        select(Watchlist).where(
            and_(
                Watchlist.user_id == current_user.id,
                Watchlist.video_id == video_id,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Update note if provided
        if request.note is not None:
            existing.note = request.note
            await db.commit()
            await db.refresh(existing)

        video_summary = VideoSummary(
            id=video.id,
            title=video.title,
            thumbnail_url=video.thumbnail_url,
            duration_seconds=video.duration_seconds,
            creator_id=video.creator_id,
            creator_name=creator.display_name,
            view_count=video.view_count,
            like_count=video.like_count,
        )
        return WatchlistItemResponse(
            video_id=existing.video_id,
            user_id=existing.user_id,
            note=existing.note,
            created_at=existing.created_at,
            video=video_summary,
        )

    # Add to watchlist
    watchlist_item = Watchlist(
        user_id=current_user.id,
        video_id=video_id,
        note=request.note,
    )
    db.add(watchlist_item)
    await db.commit()
    await db.refresh(watchlist_item)

    video_summary = VideoSummary(
        id=video.id,
        title=video.title,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=video.duration_seconds,
        creator_id=video.creator_id,
        creator_name=creator.display_name,
        view_count=video.view_count,
        like_count=video.like_count,
    )
    return WatchlistItemResponse(
        video_id=watchlist_item.video_id,
        user_id=watchlist_item.user_id,
        note=watchlist_item.note,
        created_at=watchlist_item.created_at,
        video=video_summary,
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a video from watchlist."""
    result = await db.execute(
        select(Watchlist).where(
            and_(
                Watchlist.user_id == current_user.id,
                Watchlist.video_id == video_id,
            )
        )
    )
    watchlist_item = result.scalar_one_or_none()
    if not watchlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not in watchlist",
        )

    await db.delete(watchlist_item)
    await db.commit()


@router.get("/{video_id}/check")
async def check_in_watchlist(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a video is in watchlist."""
    result = await db.execute(
        select(Watchlist).where(
            and_(
                Watchlist.user_id == current_user.id,
                Watchlist.video_id == video_id,
            )
        )
    )
    watchlist_item = result.scalar_one_or_none()

    return {
        "in_watchlist": watchlist_item is not None,
        "note": watchlist_item.note if watchlist_item else None,
        "added_at": watchlist_item.created_at if watchlist_item else None,
    }


@router.put("/{video_id}/note")
async def update_watchlist_note(
    video_id: uuid.UUID,
    request: WatchlistAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update note for a watchlist item."""
    result = await db.execute(
        select(Watchlist).where(
            and_(
                Watchlist.user_id == current_user.id,
                Watchlist.video_id == video_id,
            )
        )
    )
    watchlist_item = result.scalar_one_or_none()
    if not watchlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not in watchlist",
        )

    watchlist_item.note = request.note
    await db.commit()

    return {"note": watchlist_item.note, "updated_at": watchlist_item.updated_at}
