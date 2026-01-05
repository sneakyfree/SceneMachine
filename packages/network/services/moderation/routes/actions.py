"""
Moderation action routes for moderation service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    ActionType,
    Comment,
    ModerationAction,
    Strike,
    User,
    Video,
    VideoStatus,
    MAX_STRIKES,
    STRIKE_EXPIRATION_DAYS,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    ModerationActionRequest,
    ModerationActionResponse,
    ModerationActionListResponse,
)

router = APIRouter(prefix="/actions", tags=["moderation-actions"])


def _require_moderator(user: User) -> None:
    """Verify user is a moderator."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )


@router.post("", response_model=ModerationActionResponse, status_code=status.HTTP_201_CREATED)
async def create_action(
    request: ModerationActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModerationActionResponse:
    """
    Create a moderation action against a user.

    Actions can include warnings, video removal, comment removal,
    temporary bans, and permanent bans.
    """
    _require_moderator(current_user)

    # Verify target user exists
    result = await db.execute(
        select(User).where(User.id == request.target_user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    # Create action
    action = ModerationAction(
        target_user_id=request.target_user_id,
        moderator_id=current_user.id,
        action_type=request.action_type,
        reason=request.reason,
        video_id=request.video_id,
        comment_id=request.comment_id,
        report_id=request.report_id,
        duration_hours=request.duration_hours,
        notes=request.notes,
    )

    # Calculate expiration for temporary actions
    if request.duration_hours and request.action_type in (
        ActionType.TEMP_BAN,
        ActionType.MONETIZATION_SUSPEND,
    ):
        action.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=request.duration_hours
        )

    db.add(action)

    # Execute the action
    action_result = await _execute_action(
        db, action, target_user, request.add_strike
    )

    await db.commit()
    await db.refresh(action)

    return ModerationActionResponse.model_validate(action)


async def _execute_action(
    db: AsyncSession,
    action: ModerationAction,
    target_user: User,
    add_strike: bool = False,
) -> dict:
    """Execute the moderation action."""
    result = {"strike_added": False, "account_terminated": False}

    # Handle different action types
    if action.action_type == ActionType.WARNING:
        # Just log, maybe send notification
        pass

    elif action.action_type == ActionType.CONTENT_REMOVE:
        if action.video_id:
            video_result = await db.execute(
                select(Video).where(Video.id == action.video_id)
            )
            video = video_result.scalar_one_or_none()
            if video:
                video.status = VideoStatus.REMOVED

        if action.comment_id:
            comment_result = await db.execute(
                select(Comment).where(Comment.id == action.comment_id)
            )
            comment = comment_result.scalar_one_or_none()
            if comment:
                comment.is_deleted = True

    elif action.action_type == ActionType.CHANNEL_SUSPEND:
        # Mark all user videos as unlisted
        await db.execute(
            select(Video)
            .where(Video.creator_id == target_user.id)
            .where(Video.status == VideoStatus.PUBLISHED)
        )
        # Would update in batch

    elif action.action_type == ActionType.TEMP_BAN:
        target_user.is_suspended = True
        target_user.suspended_until = action.expires_at

    elif action.action_type == ActionType.PERM_BAN:
        target_user.is_suspended = True
        target_user.is_terminated = True

    elif action.action_type == ActionType.MONETIZATION_SUSPEND:
        # Would update creator profile
        pass

    # Add strike if requested
    if add_strike and action.action_type in (
        ActionType.CONTENT_REMOVE,
        ActionType.CHANNEL_SUSPEND,
        ActionType.TEMP_BAN,
    ):
        strike = Strike(
            user_id=target_user.id,
            action_id=action.id,
            reason=action.reason,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=STRIKE_EXPIRATION_DAYS),
        )
        db.add(strike)
        result["strike_added"] = True

        # Check if user should be terminated
        active_strikes = await db.execute(
            select(func.count()).where(
                and_(
                    Strike.user_id == target_user.id,
                    Strike.is_active == True,
                    or_(
                        Strike.expires_at > datetime.now(timezone.utc),
                        Strike.expires_at == None,
                    ),
                )
            )
        )
        strike_count = (active_strikes.scalar() or 0) + 1  # +1 for new strike

        if strike_count >= MAX_STRIKES:
            target_user.is_suspended = True
            target_user.is_terminated = True
            result["account_terminated"] = True

    return result


@router.get("", response_model=ModerationActionListResponse)
async def get_actions(
    target_user_id: Optional[uuid.UUID] = Query(None),
    moderator_id: Optional[uuid.UUID] = Query(None),
    action_type: Optional[ActionType] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModerationActionListResponse:
    """Get moderation actions (moderator only)."""
    _require_moderator(current_user)

    # Build query
    query = select(ModerationAction)

    if target_user_id:
        query = query.where(ModerationAction.target_user_id == target_user_id)
    if moderator_id:
        query = query.where(ModerationAction.moderator_id == moderator_id)
    if action_type:
        query = query.where(ModerationAction.action_type == action_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get actions
    offset = (page - 1) * per_page
    query = query.order_by(ModerationAction.created_at.desc())
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    actions = result.scalars().all()

    return ModerationActionListResponse(
        actions=[ModerationActionResponse.model_validate(a) for a in actions],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{action_id}", response_model=ModerationActionResponse)
async def get_action(
    action_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModerationActionResponse:
    """Get a specific moderation action (moderator only)."""
    _require_moderator(current_user)

    result = await db.execute(
        select(ModerationAction).where(ModerationAction.id == action_id)
    )
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    return ModerationActionResponse.model_validate(action)


@router.post("/{action_id}/revoke")
async def revoke_action(
    action_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Revoke a moderation action.

    This will undo the action if possible (e.g., unban user, restore content).
    """
    _require_moderator(current_user)

    result = await db.execute(
        select(ModerationAction).where(ModerationAction.id == action_id)
    )
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    if action.revoked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action already revoked",
        )

    # Revoke the action
    action.revoked_at = datetime.now(timezone.utc)
    action.revoked_by = current_user.id

    # Undo action effects
    await _undo_action(db, action)

    await db.commit()

    return {
        "action_id": str(action_id),
        "status": "revoked",
        "revoked_by": str(current_user.id),
    }


async def _undo_action(db: AsyncSession, action: ModerationAction) -> None:
    """Undo the effects of a moderation action."""
    # Get target user
    result = await db.execute(
        select(User).where(User.id == action.target_user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        return

    if action.action_type == ActionType.CONTENT_REMOVE:
        # Restore content (would need audit trail)
        pass

    elif action.action_type in (ActionType.TEMP_BAN, ActionType.PERM_BAN):
        # Check if there are other active bans
        other_bans = await db.execute(
            select(ModerationAction).where(
                and_(
                    ModerationAction.target_user_id == target_user.id,
                    ModerationAction.action_type.in_(
                        [ActionType.TEMP_BAN, ActionType.PERM_BAN]
                    ),
                    ModerationAction.id != action.id,
                    ModerationAction.revoked_at == None,
                    or_(
                        ModerationAction.expires_at > datetime.now(timezone.utc),
                        ModerationAction.expires_at == None,
                    ),
                )
            )
        )
        if not other_bans.scalar_one_or_none():
            target_user.is_suspended = False
            if action.action_type == ActionType.PERM_BAN:
                target_user.is_terminated = False

    # Deactivate associated strike
    result = await db.execute(
        select(Strike).where(Strike.action_id == action.id)
    )
    strike = result.scalar_one_or_none()
    if strike:
        strike.is_active = False
