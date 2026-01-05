"""
Follow/unfollow routes for social service.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import Follow, User, CreatorProfile
from ...auth.dependencies import get_current_user, get_optional_user
from ..schemas import (
    FollowRequest,
    FollowResponse,
    FollowerListResponse,
    UserSummary,
)

router = APIRouter(prefix="/users", tags=["follows"])


@router.post("/{user_id}/follow", response_model=FollowResponse)
async def follow_user(
    user_id: uuid.UUID,
    request: FollowRequest = FollowRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FollowResponse:
    """Follow a user."""
    # Can't follow yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )

    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already following
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Update notification preference
        existing.notify_on_upload = request.notify_on_upload
        await db.commit()
        await db.refresh(existing)
        return FollowResponse.model_validate(existing)

    # Create follow
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_id,
        notify_on_upload=request.notify_on_upload,
    )
    db.add(follow)

    # Update follower count on creator profile if exists
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == user_id)
    )
    creator_profile = result.scalar_one_or_none()
    if creator_profile:
        creator_profile.subscriber_count += 1

    await db.commit()
    await db.refresh(follow)

    return FollowResponse.model_validate(follow)


@router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unfollow a user."""
    # Check if following
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id,
            )
        )
    )
    follow = result.scalar_one_or_none()
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user",
        )

    await db.delete(follow)

    # Update follower count on creator profile if exists
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == user_id)
    )
    creator_profile = result.scalar_one_or_none()
    if creator_profile and creator_profile.subscriber_count > 0:
        creator_profile.subscriber_count -= 1

    await db.commit()


@router.get("/{user_id}/followers", response_model=FollowerListResponse)
async def get_followers(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> FollowerListResponse:
    """Get a user's followers."""
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Count total
    count_query = select(func.count()).where(Follow.following_id == user_id)
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get followers with user info
    offset = (page - 1) * per_page
    query = (
        select(User, Follow)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == user_id)
        .order_by(Follow.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    rows = result.all()

    # Build user summaries
    users = []
    for user, follow in rows:
        # Check if current user is following this follower
        is_following = None
        if current_user:
            result = await db.execute(
                select(Follow).where(
                    and_(
                        Follow.follower_id == current_user.id,
                        Follow.following_id == user.id,
                    )
                )
            )
            is_following = result.scalar_one_or_none() is not None

        users.append(
            UserSummary(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                is_verified=user.is_verified,
                is_creator=user.is_creator,
                is_following=is_following,
            )
        )

    return FollowerListResponse(
        users=users,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(users)) < total,
    )


@router.get("/{user_id}/following", response_model=FollowerListResponse)
async def get_following(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> FollowerListResponse:
    """Get users that a user is following."""
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Count total
    count_query = select(func.count()).where(Follow.follower_id == user_id)
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get following with user info
    offset = (page - 1) * per_page
    query = (
        select(User, Follow)
        .join(Follow, Follow.following_id == User.id)
        .where(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    rows = result.all()

    # Build user summaries
    users = []
    for user, follow in rows:
        # Check if current user is following this user
        is_following = None
        if current_user:
            if current_user.id == user_id:
                # If viewing own following list, all are followed
                is_following = True
            else:
                result = await db.execute(
                    select(Follow).where(
                        and_(
                            Follow.follower_id == current_user.id,
                            Follow.following_id == user.id,
                        )
                    )
                )
                is_following = result.scalar_one_or_none() is not None

        users.append(
            UserSummary(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                is_verified=user.is_verified,
                is_creator=user.is_creator,
                is_following=is_following,
            )
        )

    return FollowerListResponse(
        users=users,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(users)) < total,
    )


@router.get("/{user_id}/is-following")
async def check_is_following(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if current user is following a user."""
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id,
            )
        )
    )
    follow = result.scalar_one_or_none()

    return {
        "is_following": follow is not None,
        "notify_on_upload": follow.notify_on_upload if follow else None,
    }
