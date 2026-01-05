"""
Reaction routes for social service.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import Reaction, ReactionType, User, Video, Notification
from ...auth.dependencies import get_current_user, get_optional_user
from ..schemas import (
    ReactionRequest,
    ReactionResponse,
    ReactionSummaryResponse,
)

router = APIRouter(tags=["reactions"])


@router.post("/videos/{video_id}/react", response_model=ReactionResponse)
async def react_to_video(
    video_id: uuid.UUID,
    request: ReactionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReactionResponse:
    """React to a video. Replaces any existing reaction."""
    # Check if video exists
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Check if user already has a reaction
    result = await db.execute(
        select(Reaction).where(
            and_(
                Reaction.user_id == current_user.id,
                Reaction.video_id == video_id,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing reaction
        old_type = existing.reaction_type
        existing.reaction_type = request.reaction_type
        await db.commit()
        await db.refresh(existing)

        # Update video like count if changing from/to like
        if old_type == ReactionType.LIKE and request.reaction_type != ReactionType.LIKE:
            video.like_count = max(0, video.like_count - 1)
        elif (
            old_type != ReactionType.LIKE and request.reaction_type == ReactionType.LIKE
        ):
            video.like_count += 1
        await db.commit()

        return ReactionResponse.model_validate(existing)

    # Create new reaction
    reaction = Reaction(
        user_id=current_user.id,
        video_id=video_id,
        reaction_type=request.reaction_type,
    )
    db.add(reaction)

    # Update video like count if like
    if request.reaction_type == ReactionType.LIKE:
        video.like_count += 1

    # Notify video creator
    if video.creator_id != current_user.id:
        notification = Notification(
            user_id=video.creator_id,
            notification_type="reaction",
            actor_id=current_user.id,
            video_id=video_id,
            title=f"{current_user.display_name} reacted to your video",
            message=f"{request.reaction_type.value} on {video.title}",
        )
        db.add(notification)

    await db.commit()
    await db.refresh(reaction)

    return ReactionResponse.model_validate(reaction)


@router.delete("/videos/{video_id}/react", status_code=status.HTTP_204_NO_CONTENT)
async def remove_reaction(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove reaction from a video."""
    result = await db.execute(
        select(Reaction).where(
            and_(
                Reaction.user_id == current_user.id,
                Reaction.video_id == video_id,
            )
        )
    )
    reaction = result.scalar_one_or_none()
    if not reaction:
        return  # No reaction to remove

    # Update video like count if was a like
    if reaction.reaction_type == ReactionType.LIKE:
        result = await db.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if video:
            video.like_count = max(0, video.like_count - 1)

    await db.delete(reaction)
    await db.commit()


@router.get("/videos/{video_id}/reactions", response_model=ReactionSummaryResponse)
async def get_video_reactions(
    video_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> ReactionSummaryResponse:
    """Get reaction summary for a video."""
    # Check if video exists
    result = await db.execute(select(Video).where(Video.id == video_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Count reactions by type
    result = await db.execute(
        select(Reaction.reaction_type, func.count())
        .where(Reaction.video_id == video_id)
        .group_by(Reaction.reaction_type)
    )
    counts = dict(result.all())

    total = sum(counts.values())

    # Get user's reaction
    user_reaction = None
    if current_user:
        result = await db.execute(
            select(Reaction).where(
                and_(
                    Reaction.user_id == current_user.id,
                    Reaction.video_id == video_id,
                )
            )
        )
        reaction = result.scalar_one_or_none()
        if reaction:
            user_reaction = reaction.reaction_type

    return ReactionSummaryResponse(
        video_id=video_id,
        total_reactions=total,
        like_count=counts.get(ReactionType.LIKE, 0),
        love_count=counts.get(ReactionType.LOVE, 0),
        fire_count=counts.get(ReactionType.FIRE, 0),
        mind_blown_count=counts.get(ReactionType.MIND_BLOWN, 0),
        sad_count=counts.get(ReactionType.SAD, 0),
        laugh_count=counts.get(ReactionType.LAUGH, 0),
        user_reaction=user_reaction,
    )


@router.get("/videos/{video_id}/my-reaction")
async def get_my_reaction(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user's reaction on a video."""
    result = await db.execute(
        select(Reaction).where(
            and_(
                Reaction.user_id == current_user.id,
                Reaction.video_id == video_id,
            )
        )
    )
    reaction = result.scalar_one_or_none()

    if not reaction:
        return {"has_reaction": False, "reaction_type": None}

    return {
        "has_reaction": True,
        "reaction_type": reaction.reaction_type,
        "created_at": reaction.created_at,
    }
