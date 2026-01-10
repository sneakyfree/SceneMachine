"""CoreCast competition routes."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.events import (
    BadgeType,
    CoreCastEvent,
    CoreCastSubmission,
    CoreCastVote,
    EventStatus,
    PRIZE_DISTRIBUTION,
    PrizeDistribution,
    SubmissionPhase,
    UserBadge,
    VoteType,
)
from ....shared.models.user import User
from ....shared.models.video import Video
from ...auth.dependencies import get_current_user, get_current_admin
from ..schemas import (
    CoreCastEventCreate,
    CoreCastEventResponse,
    CoreCastSubmissionCreate,
    CoreCastSubmissionResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    VoteRequest,
    VoteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/corecast", tags=["CoreCast"])


# ============================================================================
# Event Endpoints
# ============================================================================


@router.get("/events", response_model=list[CoreCastEventResponse])
async def list_events(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> list[CoreCastEvent]:
    """List CoreCast events."""
    query = select(CoreCastEvent)

    if status_filter:
        try:
            event_status = EventStatus(status_filter)
            query = query.where(CoreCastEvent.status == event_status)
        except ValueError:
            pass

    query = query.order_by(desc(CoreCastEvent.year), desc(CoreCastEvent.month))
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/events/current", response_model=CoreCastEventResponse)
async def get_current_event(
    session: AsyncSession = Depends(get_session),
) -> CoreCastEvent:
    """Get the currently active CoreCast event."""
    now = datetime.utcnow()

    # Find event in any active phase
    query = select(CoreCastEvent).where(
        CoreCastEvent.status.in_([
            EventStatus.SUBMISSIONS_OPEN,
            EventStatus.VOTING,
            EventStatus.JUDGING,
        ])
    )

    result = await session.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        # Find next upcoming event
        query = (
            select(CoreCastEvent)
            .where(CoreCastEvent.status == EventStatus.UPCOMING)
            .order_by(CoreCastEvent.submissions_start)
            .limit(1)
        )
        result = await session.execute(query)
        event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="No active or upcoming event")

    return event


@router.get("/events/{event_id}", response_model=CoreCastEventResponse)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CoreCastEvent:
    """Get a CoreCast event by ID."""
    event = await session.get(CoreCastEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/events", response_model=CoreCastEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: CoreCastEventCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_admin),
) -> CoreCastEvent:
    """Create a new CoreCast event (admin only)."""
    # Check for existing event in same month
    existing = await session.execute(
        select(CoreCastEvent).where(
            and_(
                CoreCastEvent.month == data.month,
                CoreCastEvent.year == data.year,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"Event already exists for {data.month}/{data.year}"
        )

    # Set default prize distribution if not provided
    prize_dist = data.prize_distribution
    if not prize_dist:
        prize_dist = {str(k): str(v) for k, v in PRIZE_DISTRIBUTION.items()}

    event = CoreCastEvent(
        name=data.name,
        description=data.description,
        theme=data.theme,
        banner_url=data.banner_url,
        month=data.month,
        year=data.year,
        status=EventStatus.UPCOMING,
        submissions_start=data.submissions_start,
        submissions_end=data.submissions_end,
        voting_start=data.voting_start,
        voting_end=data.voting_end,
        results_announcement=data.results_announcement,
        total_prize_pool=data.total_prize_pool,
        prize_distribution=prize_dist,
        max_submissions_per_user=data.max_submissions_per_user,
        min_duration_seconds=data.min_duration_seconds,
        max_duration_seconds=data.max_duration_seconds,
        requires_studio_content=data.requires_studio_content,
        sponsors=data.sponsors,
    )

    session.add(event)
    await session.commit()
    await session.refresh(event)

    logger.info(f"Created CoreCast event: {event.name}")
    return event


@router.patch("/events/{event_id}/status")
async def update_event_status(
    event_id: UUID,
    new_status: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CoreCastEventResponse:
    """Update event status (admin only)."""
    event = await session.get(CoreCastEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        event.status = EventStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    await session.commit()
    await session.refresh(event)

    logger.info(f"Updated CoreCast event {event_id} status to {new_status}")
    return event


# ============================================================================
# Submission Endpoints
# ============================================================================


@router.post(
    "/submissions", response_model=CoreCastSubmissionResponse, status_code=status.HTTP_201_CREATED
)
async def create_submission(
    data: CoreCastSubmissionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CoreCastSubmission:
    """Submit a video to a CoreCast event."""
    # Verify event exists and is accepting submissions
    event = await session.get(CoreCastEvent, data.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != EventStatus.SUBMISSIONS_OPEN:
        raise HTTPException(
            status_code=400, detail="Event is not accepting submissions"
        )

    now = datetime.utcnow()
    if now < event.submissions_start or now > event.submissions_end:
        raise HTTPException(status_code=400, detail="Submission period not active")

    # Verify video exists and belongs to user
    video = await session.get(Video, data.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check duration requirements
    if video.duration_seconds < event.min_duration_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"Video too short (min {event.min_duration_seconds}s)",
        )
    if video.duration_seconds > event.max_duration_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"Video too long (max {event.max_duration_seconds}s)",
        )

    # Check if made with studio (if required)
    if event.requires_studio_content and not video.made_with_studio:
        raise HTTPException(
            status_code=400, detail="Only Scene Machine Studio content is eligible"
        )

    # Check submission limit
    user_submissions = await session.execute(
        select(func.count(CoreCastSubmission.id)).where(
            and_(
                CoreCastSubmission.event_id == data.event_id,
                CoreCastSubmission.creator_id == current_user.id,
            )
        )
    )
    count = user_submissions.scalar()
    if count >= event.max_submissions_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {event.max_submissions_per_user} submissions per user",
        )

    # Check if video already submitted
    existing = await session.execute(
        select(CoreCastSubmission).where(
            and_(
                CoreCastSubmission.event_id == data.event_id,
                CoreCastSubmission.video_id == data.video_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Video already submitted to this event")

    submission = CoreCastSubmission(
        event_id=data.event_id,
        video_id=data.video_id,
        creator_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        phase=SubmissionPhase.SUBMITTED,
    )

    session.add(submission)

    # Update event stats
    event.submission_count += 1

    await session.commit()
    await session.refresh(submission)

    logger.info(f"Created CoreCast submission {submission.id} for event {data.event_id}")
    return submission


@router.get("/submissions/mine", response_model=list[CoreCastSubmissionResponse])
async def get_my_submissions(
    event_id: Optional[UUID] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CoreCastSubmission]:
    """Get user's CoreCast submissions."""
    query = select(CoreCastSubmission).where(CoreCastSubmission.creator_id == current_user.id)

    if event_id:
        query = query.where(CoreCastSubmission.event_id == event_id)

    query = query.order_by(desc(CoreCastSubmission.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/submissions/{submission_id}", response_model=CoreCastSubmissionResponse)
async def get_submission(
    submission_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CoreCastSubmission:
    """Get a submission by ID."""
    submission = await session.get(CoreCastSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.delete("/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_submission(
    submission_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Withdraw a submission (only during submission phase)."""
    submission = await session.get(CoreCastSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if still in submission phase
    event = await session.get(CoreCastEvent, submission.event_id)
    if event and event.status != EventStatus.SUBMISSIONS_OPEN:
        raise HTTPException(status_code=400, detail="Cannot withdraw after submissions close")

    # Update event stats
    if event:
        event.submission_count -= 1

    await session.delete(submission)
    await session.commit()

    logger.info(f"Submission {submission_id} withdrawn")


# ============================================================================
# Voting Endpoints
# ============================================================================


@router.post("/vote", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def vote_on_submission(
    data: VoteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CoreCastVote:
    """Vote on a CoreCast submission."""
    # Get submission
    submission = await session.get(CoreCastSubmission, data.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Check if voting is open
    event = await session.get(CoreCastEvent, submission.event_id)
    if not event or event.status != EventStatus.VOTING:
        raise HTTPException(status_code=400, detail="Voting is not open")

    # Can't vote on own submission
    if submission.creator_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot vote on your own submission")

    # Check for existing vote
    existing = await session.execute(
        select(CoreCastVote).where(
            and_(
                CoreCastVote.submission_id == data.submission_id,
                CoreCastVote.voter_id == current_user.id,
                CoreCastVote.vote_type == VoteType.PUBLIC,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already voted on this submission")

    vote = CoreCastVote(
        submission_id=data.submission_id,
        voter_id=current_user.id,
        vote_type=VoteType.PUBLIC,
    )
    session.add(vote)

    # Update submission vote count
    submission.public_votes += 1

    # Update event stats
    event.vote_count += 1

    # Track unique voters
    voter_check = await session.execute(
        select(CoreCastVote).where(
            and_(
                CoreCastVote.voter_id == current_user.id,
                CoreCastVote.submission_id.in_(
                    select(CoreCastSubmission.id).where(
                        CoreCastSubmission.event_id == event.id
                    )
                ),
            )
        )
    )
    if not voter_check.scalars().first():
        event.unique_voters += 1

    await session.commit()
    await session.refresh(vote)

    logger.info(f"User {current_user.id} voted on submission {data.submission_id}")
    return vote


@router.post("/judge-vote", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def judge_vote(
    data: VoteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CoreCastVote:
    """Cast a judge vote on a submission (judge only)."""
    if data.score is None:
        raise HTTPException(status_code=400, detail="Judge votes require a score")

    submission = await session.get(CoreCastSubmission, data.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    event = await session.get(CoreCastEvent, submission.event_id)
    if not event or event.status != EventStatus.JUDGING:
        raise HTTPException(status_code=400, detail="Judging phase not active")

    # Verify user is a judge for this event
    if str(current_user.id) not in (event.judge_ids or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized as a judge for this event"
        )

    # Check for existing judge vote from this user
    existing = await session.execute(
        select(CoreCastVote).where(
            and_(
                CoreCastVote.submission_id == data.submission_id,
                CoreCastVote.voter_id == current_user.id,
                CoreCastVote.vote_type == VoteType.JUDGE,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already judged this submission")

    vote = CoreCastVote(
        submission_id=data.submission_id,
        voter_id=current_user.id,
        vote_type=VoteType.JUDGE,
        score=data.score,
        notes=data.notes,
    )
    session.add(vote)

    # Update judge score (average of all judge scores)
    judge_votes = await session.execute(
        select(CoreCastVote.score).where(
            and_(
                CoreCastVote.submission_id == data.submission_id,
                CoreCastVote.vote_type == VoteType.JUDGE,
                CoreCastVote.score.isnot(None),
            )
        )
    )
    scores = [row[0] for row in judge_votes.all()] + [data.score]
    submission.judge_score = sum(scores) / len(scores)

    await session.commit()
    await session.refresh(vote)

    logger.info(f"Judge {current_user.id} scored submission {data.submission_id}: {data.score}")
    return vote


# ============================================================================
# Leaderboard & Results
# ============================================================================


@router.get("/events/{event_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    event_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> LeaderboardResponse:
    """Get event leaderboard."""
    event = await session.get(CoreCastEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get submissions ordered by combined score
    query = (
        select(CoreCastSubmission)
        .where(
            and_(
                CoreCastSubmission.event_id == event_id,
                CoreCastSubmission.is_qualified == True,
            )
        )
        .order_by(desc(CoreCastSubmission.combined_score), desc(CoreCastSubmission.public_votes))
        .limit(limit)
    )

    result = await session.execute(query)
    submissions = list(result.scalars().all())

    entries = []
    for rank, sub in enumerate(submissions, 1):
        entries.append(
            LeaderboardEntry(
                rank=rank,
                submission_id=sub.id,
                creator_id=sub.creator_id,
                creator_name=sub.creator.username if sub.creator else "Unknown",
                title=sub.title,
                public_votes=sub.public_votes,
                judge_score=sub.judge_score,
                combined_score=sub.combined_score,
                badges=sub.special_badges,
            )
        )

    return LeaderboardResponse(
        event_id=event_id,
        event_name=event.name,
        phase=event.status.value,
        entries=entries,
        total_entries=event.submission_count,
        last_updated=datetime.utcnow(),
    )


@router.post("/events/{event_id}/finalize")
async def finalize_results(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Finalize event results and distribute prizes (admin only)."""
    event = await session.get(CoreCastEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != EventStatus.JUDGING:
        raise HTTPException(status_code=400, detail="Event must be in judging phase")

    # Calculate combined scores for all submissions
    submissions = await session.execute(
        select(CoreCastSubmission)
        .where(
            and_(
                CoreCastSubmission.event_id == event_id,
                CoreCastSubmission.is_qualified == True,
            )
        )
        .order_by(desc(CoreCastSubmission.combined_score), desc(CoreCastSubmission.public_votes))
    )
    all_submissions = list(submissions.scalars().all())

    # Find max values for normalization
    max_public = max((s.public_votes for s in all_submissions), default=1)
    max_peer = max((s.peer_votes for s in all_submissions), default=1)

    # Calculate combined scores and assign ranks
    prizes_distributed = []
    for rank, submission in enumerate(all_submissions, 1):
        # Combined score: 30% public, 50% judge, 20% peer
        public_norm = (submission.public_votes / max_public) * 100 if max_public > 0 else 0
        peer_norm = (submission.peer_votes / max_peer) * 100 if max_peer > 0 else 0
        judge = submission.judge_score or 0

        submission.combined_score = (public_norm * 0.3) + (judge * 0.5) + (peer_norm * 0.2)
        submission.final_rank = rank

        # Assign phase based on rank
        if rank == 1:
            submission.phase = SubmissionPhase.WINNER
        elif rank <= 10:
            submission.phase = SubmissionPhase.FINALIST
        elif rank <= 25:
            submission.phase = SubmissionPhase.TOP_25
        elif rank <= 50:
            submission.phase = SubmissionPhase.TOP_50
        elif rank <= 100:
            submission.phase = SubmissionPhase.TOP_100

        # Distribute prizes to top 10
        if rank <= 10:
            prize_amount = PRIZE_DISTRIBUTION.get(rank, Decimal("0.00"))
            submission.prize_amount = prize_amount

            # Determine badge
            if rank == 1:
                badge = BadgeType.GOLD
            elif rank == 2:
                badge = BadgeType.SILVER
            elif rank == 3:
                badge = BadgeType.BRONZE
            else:
                badge = BadgeType.FINALIST

            # Create prize distribution record
            prize_dist = PrizeDistribution(
                event_id=event_id,
                submission_id=submission.id,
                recipient_id=submission.creator_id,
                amount=prize_amount,
                final_rank=rank,
                badge_awarded=badge,
            )
            session.add(prize_dist)

            # Award badge
            user_badge = UserBadge(
                user_id=submission.creator_id,
                badge_type=badge,
                event_id=event_id,
                award_reason=f"CoreCast {event.name} - Rank #{rank}",
            )
            session.add(user_badge)

            prizes_distributed.append({
                "rank": rank,
                "submission_id": str(submission.id),
                "amount": float(prize_amount),
                "badge": badge.value,
            })

    # Find People's Choice (most public votes)
    if all_submissions:
        peoples_choice = max(all_submissions, key=lambda s: s.public_votes)
        peoples_badge = UserBadge(
            user_id=peoples_choice.creator_id,
            badge_type=BadgeType.PEOPLES_CHOICE,
            event_id=event_id,
            award_reason=f"CoreCast {event.name} - People's Choice ({peoples_choice.public_votes} votes)",
        )
        session.add(peoples_badge)
        peoples_choice.special_badges = list(peoples_choice.special_badges) + ["peoples_choice"]

    # Update event status
    event.status = EventStatus.COMPLETED

    await session.commit()

    logger.info(f"Finalized CoreCast event {event_id} with {len(prizes_distributed)} prizes")
    return {
        "event_id": str(event_id),
        "status": "completed",
        "total_submissions": len(all_submissions),
        "prizes_distributed": prizes_distributed,
    }
