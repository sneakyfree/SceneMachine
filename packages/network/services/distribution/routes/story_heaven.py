"""StoryHeaven (short-form) distribution routes."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.distribution import (
    ContentFormat,
    StoryHeavenDuet,
    StoryHeavenPost,
    StoryHeavenSound,
)
from ....shared.models.user import User
from ....shared.models.video import Video
from ...auth.dependencies import get_current_user
from ..schemas import (
    DuetCreate,
    StoryHeavenPostCreate,
    StoryHeavenPostResponse,
    StoryHeavenSoundResponse,
    TrendingFeedParams,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/story-heaven", tags=["StoryHeaven"])

# Viral threshold (views in 24 hours)
VIRAL_THRESHOLD = 100_000
TRENDING_DECAY_HOURS = 72


@router.post("/posts", response_model=StoryHeavenPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: StoryHeavenPostCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StoryHeavenPost:
    """Create a StoryHeaven post from a video."""
    # Verify video exists and belongs to user
    video = await session.get(Video, data.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to post this video")

    # Check video duration (max 10 minutes for StoryHeaven)
    if video.duration_seconds > 600:
        raise HTTPException(
            status_code=400,
            detail="Video too long for StoryHeaven (max 10 minutes)",
        )

    # Check if already posted
    existing = await session.execute(
        select(StoryHeavenPost).where(StoryHeavenPost.video_id == data.video_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Video already posted to StoryHeaven")

    # Parse format
    try:
        content_format = ContentFormat(data.format)
    except ValueError:
        content_format = ContentFormat.VERTICAL_916

    post = StoryHeavenPost(
        video_id=data.video_id,
        creator_id=current_user.id,
        format=content_format,
        hashtags=data.hashtags[:30],  # Max 30 hashtags
        allow_duets=data.allow_duets,
        allow_sound_reuse=data.allow_sound_reuse,
        allow_comments=data.allow_comments,
        optimized_for_mobile=content_format == ContentFormat.VERTICAL_916,
    )

    session.add(post)
    await session.commit()
    await session.refresh(post)

    logger.info(f"Created StoryHeaven post {post.id} for video {data.video_id}")
    return post


@router.get("/posts/{post_id}", response_model=StoryHeavenPostResponse)
async def get_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> StoryHeavenPost:
    """Get a StoryHeaven post by ID."""
    post = await session.get(StoryHeavenPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("/feed/trending", response_model=list[StoryHeavenPostResponse])
async def get_trending_feed(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    hashtag: Optional[str] = None,
    sound_id: Optional[UUID] = None,
    session: AsyncSession = Depends(get_session),
) -> list[StoryHeavenPost]:
    """Get trending StoryHeaven posts."""
    query = select(StoryHeavenPost)

    # Filter by hashtag
    if hashtag:
        query = query.where(StoryHeavenPost.hashtags.contains([hashtag.lower()]))

    # Filter by sound
    if sound_id:
        query = query.where(StoryHeavenPost.original_sound_id == sound_id)

    # Order by trending score (decayed by time)
    query = query.order_by(desc(StoryHeavenPost.trending_score), desc(StoryHeavenPost.created_at))
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/feed/for-you", response_model=list[StoryHeavenPostResponse])
async def get_for_you_feed(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[StoryHeavenPost]:
    """Get personalized 'For You' feed based on user preferences and behavior."""
    from ....shared.models.social import Follow, VideoLike
    from ....shared.models.analytics import VideoView

    # Get user's followed creators for boosting their content
    follows_result = await session.execute(
        select(Follow.followed_id).where(Follow.follower_id == current_user.id)
    )
    followed_ids = {row[0] for row in follows_result.all()}

    # Get hashtags from user's recently liked videos (last 50)
    liked_videos_result = await session.execute(
        select(StoryHeavenPost.hashtags)
        .join(VideoLike, VideoLike.video_id == StoryHeavenPost.video_id)
        .where(VideoLike.user_id == current_user.id)
        .order_by(VideoLike.created_at.desc())
        .limit(50)
    )
    preferred_hashtags = set()
    for row in liked_videos_result.all():
        if row[0]:
            preferred_hashtags.update(row[0][:5])  # Top 5 hashtags per video

    # Get all candidate posts (recent + trending)
    query = (
        select(StoryHeavenPost)
        .where(StoryHeavenPost.created_at >= datetime.utcnow() - timedelta(days=7))
        .order_by(desc(StoryHeavenPost.trending_score))
        .limit(200)  # Candidate pool
    )
    result = await session.execute(query)
    candidates = list(result.scalars().all())

    # Score each post based on personalization factors
    scored_posts = []
    for post in candidates:
        score = post.trending_score or 0

        # Boost content from followed creators (2x boost)
        if post.creator_id in followed_ids:
            score *= 2.0

        # Boost content with matching hashtags (1.5x per matching tag, max 3x)
        matching_tags = len(set(post.hashtags or []) & preferred_hashtags)
        if matching_tags > 0:
            score *= min(3.0, 1.0 + (matching_tags * 0.5))

        # Recency boost: newer content gets a boost
        hours_old = (datetime.utcnow() - post.created_at).total_seconds() / 3600
        recency_factor = max(0.5, 1.0 - (hours_old / 168))  # Decay over 7 days
        score *= recency_factor

        # Engagement velocity: high engagement in short time
        if hours_old > 0:
            velocity = (post.like_count + post.comment_count * 2) / hours_old
            score += velocity * 0.1

        # Diversity: slight penalty for creators we've seen a lot recently
        # (simplified - full implementation would track session views)

        scored_posts.append((post, score))

    # Sort by personalized score
    scored_posts.sort(key=lambda x: x[1], reverse=True)

    # Apply pagination
    paginated = scored_posts[offset : offset + limit]
    return [post for post, _ in paginated]


@router.get("/feed/following", response_model=list[StoryHeavenPostResponse])
async def get_following_feed(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[StoryHeavenPost]:
    """Get posts from followed creators."""
    from ....shared.models.social import Follow

    # Get followed user IDs
    follows_query = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
    follows_result = await session.execute(follows_query)
    followed_ids = [row[0] for row in follows_result.all()]

    if not followed_ids:
        return []

    query = (
        select(StoryHeavenPost)
        .where(StoryHeavenPost.creator_id.in_(followed_ids))
        .order_by(desc(StoryHeavenPost.created_at))
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.post("/posts/{post_id}/view")
async def record_view(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Record a view on a post."""
    post = await session.get(StoryHeavenPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.view_count += 1

    # Update trending score (simple decay formula)
    hours_since_creation = (datetime.utcnow() - post.created_at).total_seconds() / 3600
    decay_factor = max(0.1, 1 - (hours_since_creation / TRENDING_DECAY_HOURS))
    engagement_score = (
        post.view_count * 1
        + post.like_count * 5
        + post.share_count * 10
        + post.comment_count * 3
        + post.duet_count * 15
    )
    post.trending_score = engagement_score * decay_factor / 1000

    # Check viral threshold (100k views in 24 hours)
    if not post.viral_threshold_reached and post.view_count >= VIRAL_THRESHOLD:
        if hours_since_creation <= 24:
            post.viral_threshold_reached = True
            post.viral_reached_at = datetime.utcnow()
            logger.info(f"Post {post_id} reached viral threshold!")

    await session.commit()
    return {"view_count": post.view_count, "trending_score": post.trending_score}


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Like a post."""
    post = await session.get(StoryHeavenPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.like_count += 1
    await session.commit()
    return {"like_count": post.like_count}


@router.post("/posts/{post_id}/share")
async def share_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Record a share on a post."""
    post = await session.get(StoryHeavenPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.share_count += 1
    await session.commit()
    return {"share_count": post.share_count}


@router.post("/duets", response_model=StoryHeavenPostResponse, status_code=status.HTTP_201_CREATED)
async def create_duet(
    data: DuetCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StoryHeavenPost:
    """Create a duet response to an existing post."""
    # Get original post
    original = await session.get(StoryHeavenPost, data.original_post_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original post not found")

    if not original.allow_duets:
        raise HTTPException(status_code=400, detail="Duets not allowed on this post")

    # Get response video
    response_video = await session.get(Video, data.response_video_id)
    if not response_video:
        raise HTTPException(status_code=404, detail="Response video not found")
    if response_video.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Create response post
    response_post = StoryHeavenPost(
        video_id=data.response_video_id,
        creator_id=current_user.id,
        format=original.format,  # Match original format
        hashtags=original.hashtags[:10],  # Inherit some hashtags
        original_sound_id=original.original_sound_id,
        uses_trending_sound=original.uses_trending_sound,
        allow_duets=True,
        allow_sound_reuse=True,
        allow_comments=True,
    )
    session.add(response_post)
    await session.flush()

    # Create duet relationship
    duet = StoryHeavenDuet(
        original_post_id=data.original_post_id,
        response_post_id=response_post.id,
        creator_id=current_user.id,
    )
    session.add(duet)

    # Update original post duet count
    original.duet_count += 1

    await session.commit()
    await session.refresh(response_post)

    logger.info(f"Created duet {response_post.id} responding to {data.original_post_id}")
    return response_post


@router.get("/sounds/trending", response_model=list[StoryHeavenSoundResponse])
async def get_trending_sounds(
    limit: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[StoryHeavenSound]:
    """Get trending sounds."""
    query = (
        select(StoryHeavenSound)
        .where(StoryHeavenSound.is_trending == True)
        .order_by(desc(StoryHeavenSound.usage_count))
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/sounds/{sound_id}", response_model=StoryHeavenSoundResponse)
async def get_sound(
    sound_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> StoryHeavenSound:
    """Get a sound by ID."""
    sound = await session.get(StoryHeavenSound, sound_id)
    if not sound:
        raise HTTPException(status_code=404, detail="Sound not found")
    return sound


@router.get("/sounds/{sound_id}/posts", response_model=list[StoryHeavenPostResponse])
async def get_posts_using_sound(
    sound_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[StoryHeavenPost]:
    """Get posts using a specific sound."""
    query = (
        select(StoryHeavenPost)
        .where(StoryHeavenPost.original_sound_id == sound_id)
        .order_by(desc(StoryHeavenPost.view_count))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/hashtags/{hashtag}/posts", response_model=list[StoryHeavenPostResponse])
async def get_posts_by_hashtag(
    hashtag: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[StoryHeavenPost]:
    """Get posts with a specific hashtag."""
    query = (
        select(StoryHeavenPost)
        .where(StoryHeavenPost.hashtags.contains([hashtag.lower()]))
        .order_by(desc(StoryHeavenPost.trending_score), desc(StoryHeavenPost.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a StoryHeaven post."""
    post = await session.get(StoryHeavenPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await session.delete(post)
    await session.commit()
    logger.info(f"Deleted StoryHeaven post {post_id}")
