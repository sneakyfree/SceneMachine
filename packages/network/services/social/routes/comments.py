"""
Comment routes for social service.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import Comment, CommentLike, User, Video, Notification
from ...auth.dependencies import get_current_user, get_optional_user
from ..schemas import (
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    CommentListResponse,
    CommentThreadResponse,
    UserSummary,
)

router = APIRouter(tags=["comments"])


@router.get("/comments/me", response_model=CommentListResponse)
async def get_my_video_comments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    filter: str = Query("all", regex="^(all|unread|held)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentListResponse:
    """Get all comments on the current user's videos."""
    # Get user's videos
    video_result = await db.execute(
        select(Video.id).where(Video.creator_id == current_user.id)
    )
    video_ids = [row[0] for row in video_result.all()]

    if not video_ids:
        return CommentListResponse(
            comments=[],
            total=0,
            page=page,
            per_page=per_page,
            has_more=False,
        )

    # Build base query for comments on user's videos
    base_conditions = [
        Comment.video_id.in_(video_ids),
        Comment.is_hidden == False,
    ]

    # Note: 'unread' and 'held' filters would need additional fields
    # For now, we return all comments but the structure supports extension

    # Count total
    count_query = select(func.count()).where(and_(*base_conditions))
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get comments with pagination
    offset = (page - 1) * per_page
    query = (
        select(Comment)
        .where(and_(*base_conditions))
        .order_by(Comment.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    comments = result.scalars().all()

    # Build responses with video info
    comment_responses = []
    for comment in comments:
        response = await _build_comment_response(comment, db, current_user)
        # Add video info
        video_result = await db.execute(
            select(Video.id, Video.title, Video.thumbnail_url).where(
                Video.id == comment.video_id
            )
        )
        video_row = video_result.first()
        if video_row:
            response_dict = response.model_dump()
            response_dict["video"] = {
                "id": str(video_row[0]),
                "title": video_row[1],
                "thumbnail_url": video_row[2],
            }
            comment_responses.append(response_dict)
        else:
            comment_responses.append(response)

    return CommentListResponse(
        comments=comment_responses,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(comment_responses)) < total,
    )


async def _build_comment_response(
    comment: Comment,
    db: AsyncSession,
    current_user: Optional[User] = None,
    include_user: bool = True,
    include_reply_count: bool = True,
) -> CommentResponse:
    """Build a comment response with joined data."""
    user_summary = None
    if include_user:
        result = await db.execute(select(User).where(User.id == comment.user_id))
        user = result.scalar_one_or_none()
        if user:
            user_summary = UserSummary(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                is_verified=user.is_verified,
                is_creator=user.is_creator,
            )

    reply_count = None
    if include_reply_count and comment.parent_id is None:
        result = await db.execute(
            select(func.count()).where(Comment.parent_id == comment.id)
        )
        reply_count = result.scalar() or 0

    is_liked = None
    if current_user:
        result = await db.execute(
            select(CommentLike).where(
                and_(
                    CommentLike.comment_id == comment.id,
                    CommentLike.user_id == current_user.id,
                )
            )
        )
        is_liked = result.scalar_one_or_none() is not None

    return CommentResponse(
        id=comment.id,
        video_id=comment.video_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        content=comment.content,
        like_count=comment.like_count,
        is_creator_heart=comment.is_creator_heart,
        is_pinned=comment.is_pinned,
        is_edited=comment.is_edited,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user=user_summary,
        reply_count=reply_count,
        is_liked=is_liked,
    )


@router.get("/videos/{video_id}/comments", response_model=CommentListResponse)
async def get_video_comments(
    video_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", regex="^(newest|oldest|top)$"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> CommentListResponse:
    """Get top-level comments for a video."""
    # Check if video exists
    result = await db.execute(select(Video).where(Video.id == video_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Count total top-level comments
    count_query = select(func.count()).where(
        and_(
            Comment.video_id == video_id,
            Comment.parent_id.is_(None),
            Comment.is_hidden == False,
        )
    )
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Build query
    offset = (page - 1) * per_page
    query = select(Comment).where(
        and_(
            Comment.video_id == video_id,
            Comment.parent_id.is_(None),
            Comment.is_hidden == False,
        )
    )

    # Apply sorting
    if sort == "newest":
        query = query.order_by(Comment.is_pinned.desc(), Comment.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Comment.is_pinned.desc(), Comment.created_at.asc())
    elif sort == "top":
        query = query.order_by(Comment.is_pinned.desc(), Comment.like_count.desc())

    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    comments = result.scalars().all()

    # Build responses
    comment_responses = []
    for comment in comments:
        response = await _build_comment_response(comment, db, current_user)
        comment_responses.append(response)

    return CommentListResponse(
        comments=comment_responses,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(comment_responses)) < total,
    )


@router.post("/videos/{video_id}/comments", response_model=CommentResponse)
async def create_comment(
    video_id: uuid.UUID,
    request: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Create a comment on a video."""
    # Check if video exists
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # If reply, check parent exists
    if request.parent_id:
        result = await db.execute(
            select(Comment).where(
                and_(
                    Comment.id == request.parent_id,
                    Comment.video_id == video_id,
                )
            )
        )
        parent = result.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )
        # Don't allow nested replies (only one level deep)
        if parent.parent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reply to a reply",
            )

    # Create comment
    comment = Comment(
        video_id=video_id,
        user_id=current_user.id,
        parent_id=request.parent_id,
        content=request.content,
    )
    db.add(comment)

    # Update video comment count
    video.comment_count += 1

    # Create notification for video creator or parent comment author
    if request.parent_id:
        # Notify parent comment author
        parent_result = await db.execute(
            select(Comment).where(Comment.id == request.parent_id)
        )
        parent_comment = parent_result.scalar_one()
        if parent_comment.user_id != current_user.id:
            notification = Notification(
                user_id=parent_comment.user_id,
                notification_type="reply",
                actor_id=current_user.id,
                video_id=video_id,
                comment_id=comment.id,
                title=f"{current_user.display_name} replied to your comment",
                message=request.content[:200],
            )
            db.add(notification)
    else:
        # Notify video creator
        if video.creator_id != current_user.id:
            notification = Notification(
                user_id=video.creator_id,
                notification_type="comment",
                actor_id=current_user.id,
                video_id=video_id,
                comment_id=comment.id,
                title=f"{current_user.display_name} commented on your video",
                message=request.content[:200],
            )
            db.add(notification)

    await db.commit()
    await db.refresh(comment)

    return await _build_comment_response(comment, db, current_user)


@router.get("/comments/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Get a single comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment or comment.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    return await _build_comment_response(comment, db, current_user)


@router.get("/comments/{comment_id}/thread", response_model=CommentThreadResponse)
async def get_comment_thread(
    comment_id: uuid.UUID,
    reply_page: int = Query(1, ge=1),
    reply_per_page: int = Query(10, ge=1, le=50),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> CommentThreadResponse:
    """Get a comment with its replies."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment or comment.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Get total reply count
    result = await db.execute(
        select(func.count()).where(
            and_(
                Comment.parent_id == comment_id,
                Comment.is_hidden == False,
            )
        )
    )
    total_replies = result.scalar() or 0

    # Get replies
    offset = (reply_page - 1) * reply_per_page
    query = (
        select(Comment)
        .where(
            and_(
                Comment.parent_id == comment_id,
                Comment.is_hidden == False,
            )
        )
        .order_by(Comment.created_at.asc())
        .offset(offset)
        .limit(reply_per_page)
    )
    result = await db.execute(query)
    replies = result.scalars().all()

    # Build responses
    comment_response = await _build_comment_response(comment, db, current_user)
    reply_responses = []
    for reply in replies:
        response = await _build_comment_response(
            reply, db, current_user, include_reply_count=False
        )
        reply_responses.append(response)

    return CommentThreadResponse(
        comment=comment_response,
        replies=reply_responses,
        total_replies=total_replies,
        has_more_replies=(offset + len(reply_responses)) < total_replies,
    )


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: uuid.UUID,
    request: CommentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Update a comment (only by author)."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this comment",
        )

    comment.content = request.content
    comment.is_edited = True
    comment.edited_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(comment)

    return await _build_comment_response(comment, db, current_user)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a comment (only by author or video creator)."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check authorization
    result = await db.execute(select(Video).where(Video.id == comment.video_id))
    video = result.scalar_one()

    if comment.user_id != current_user.id and video.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )

    # Delete replies first
    await db.execute(delete(Comment).where(Comment.parent_id == comment_id))

    # Delete the comment
    await db.delete(comment)

    # Update video comment count
    video.comment_count = max(0, video.comment_count - 1)

    await db.commit()


@router.post("/comments/{comment_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def like_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Like a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment or comment.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check if already liked
    result = await db.execute(
        select(CommentLike).where(
            and_(
                CommentLike.comment_id == comment_id,
                CommentLike.user_id == current_user.id,
            )
        )
    )
    if result.scalar_one_or_none():
        return  # Already liked, no-op

    # Create like
    like = CommentLike(comment_id=comment_id, user_id=current_user.id)
    db.add(like)
    comment.like_count += 1

    await db.commit()


@router.delete("/comments/{comment_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unlike a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check if liked
    result = await db.execute(
        select(CommentLike).where(
            and_(
                CommentLike.comment_id == comment_id,
                CommentLike.user_id == current_user.id,
            )
        )
    )
    like = result.scalar_one_or_none()
    if not like:
        return  # Not liked, no-op

    await db.delete(like)
    comment.like_count = max(0, comment.like_count - 1)

    await db.commit()


@router.post("/comments/{comment_id}/heart", status_code=status.HTTP_204_NO_CONTENT)
async def heart_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Creator heart on a comment (only by video creator)."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment or comment.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check if user is video creator
    result = await db.execute(select(Video).where(Video.id == comment.video_id))
    video = result.scalar_one()

    if video.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only video creator can heart comments",
        )

    comment.is_creator_heart = True

    # Notify comment author
    if comment.user_id != current_user.id:
        notification = Notification(
            user_id=comment.user_id,
            notification_type="heart",
            actor_id=current_user.id,
            video_id=comment.video_id,
            comment_id=comment.id,
            title=f"{current_user.display_name} loved your comment",
        )
        db.add(notification)

    await db.commit()


@router.delete("/comments/{comment_id}/heart", status_code=status.HTTP_204_NO_CONTENT)
async def unheart_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove creator heart from a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check if user is video creator
    result = await db.execute(select(Video).where(Video.id == comment.video_id))
    video = result.scalar_one()

    if video.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only video creator can manage hearts",
        )

    comment.is_creator_heart = False
    await db.commit()


@router.post("/comments/{comment_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def pin_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Pin a comment (only by video creator, only one pinned per video)."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment or comment.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check if user is video creator
    result = await db.execute(select(Video).where(Video.id == comment.video_id))
    video = result.scalar_one()

    if video.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only video creator can pin comments",
        )

    # Unpin any existing pinned comment
    await db.execute(
        select(Comment)
        .where(
            and_(
                Comment.video_id == comment.video_id,
                Comment.is_pinned == True,
            )
        )
        .execution_options(synchronize_session=False)
    )
    # Actually update
    result = await db.execute(
        select(Comment).where(
            and_(
                Comment.video_id == comment.video_id,
                Comment.is_pinned == True,
            )
        )
    )
    for pinned_comment in result.scalars().all():
        pinned_comment.is_pinned = False

    comment.is_pinned = True
    await db.commit()


@router.delete("/comments/{comment_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unpin a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Check if user is video creator
    result = await db.execute(select(Video).where(Video.id == comment.video_id))
    video = result.scalar_one()

    if video.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only video creator can manage pins",
        )

    comment.is_pinned = False
    await db.commit()
