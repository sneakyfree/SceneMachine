"""Film festival routes."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.distribution import (
    FestivalStatus,
    FestivalSubmission,
    FilmFestival,
    MovieHeavenContent,
    SubmissionStatus,
)
from ....shared.models.user import User
from ...auth.dependencies import get_current_user
from ..schemas import (
    FestivalSubmissionCreate,
    FestivalSubmissionResponse,
    FilmFestivalCreate,
    FilmFestivalResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/festivals", tags=["Festivals"])


@router.get("", response_model=list[FilmFestivalResponse])
async def list_festivals(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
    accepting_submissions: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[FilmFestival]:
    """List film festivals."""
    query = select(FilmFestival)

    if status:
        try:
            festival_status = FestivalStatus(status)
            query = query.where(FilmFestival.status == festival_status)
        except ValueError:
            pass

    if accepting_submissions:
        query = query.where(FilmFestival.status == FestivalStatus.SUBMISSIONS_OPEN)

    query = query.order_by(FilmFestival.event_start).offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{festival_id}", response_model=FilmFestivalResponse)
async def get_festival(
    festival_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> FilmFestival:
    """Get festival details."""
    festival = await session.get(FilmFestival, festival_id)
    if not festival:
        raise HTTPException(status_code=404, detail="Festival not found")
    return festival


@router.post("", response_model=FilmFestivalResponse, status_code=status.HTTP_201_CREATED)
async def create_festival(
    data: FilmFestivalCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FilmFestival:
    """Create a new film festival (admin only)."""
    # TODO: Add admin role check
    # For now, allow any authenticated user to create festivals

    # Determine initial status based on dates
    now = datetime.utcnow()
    if now < data.submission_start:
        initial_status = FestivalStatus.UPCOMING
    elif now < data.submission_end:
        initial_status = FestivalStatus.SUBMISSIONS_OPEN
    else:
        initial_status = FestivalStatus.SUBMISSIONS_CLOSED

    festival = FilmFestival(
        name=data.name,
        description=data.description,
        logo_url=data.logo_url,
        website_url=data.website_url,
        status=initial_status,
        submission_start=data.submission_start,
        submission_end=data.submission_end,
        event_start=data.event_start,
        event_end=data.event_end,
        submission_fee=data.submission_fee,
        max_runtime_minutes=data.max_runtime_minutes,
        min_runtime_minutes=data.min_runtime_minutes,
        accepted_genres=data.accepted_genres,
        requires_studio_content=data.requires_studio_content,
        grand_prize_amount=data.grand_prize_amount,
        total_prize_pool=data.total_prize_pool,
        prize_breakdown=data.prize_breakdown,
    )

    session.add(festival)
    await session.commit()
    await session.refresh(festival)

    logger.info(f"Created film festival: {festival.name}")
    return festival


@router.patch("/{festival_id}", response_model=FilmFestivalResponse)
async def update_festival(
    festival_id: UUID,
    status: Optional[str] = None,
    description: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FilmFestival:
    """Update festival details (admin only)."""
    festival = await session.get(FilmFestival, festival_id)
    if not festival:
        raise HTTPException(status_code=404, detail="Festival not found")

    if status:
        try:
            festival.status = FestivalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

    if description is not None:
        festival.description = description

    await session.commit()
    await session.refresh(festival)
    return festival


# ============================================================================
# Submissions
# ============================================================================


@router.post(
    "/{festival_id}/submissions",
    response_model=FestivalSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_to_festival(
    festival_id: UUID,
    data: FestivalSubmissionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FestivalSubmission:
    """Submit content to a festival."""
    # Verify festival exists and is accepting submissions
    festival = await session.get(FilmFestival, festival_id)
    if not festival:
        raise HTTPException(status_code=404, detail="Festival not found")

    if festival.status != FestivalStatus.SUBMISSIONS_OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Festival is not accepting submissions (status: {festival.status.value})",
        )

    now = datetime.utcnow()
    if now < festival.submission_start or now > festival.submission_end:
        raise HTTPException(status_code=400, detail="Submission period not active")

    # Verify content exists and belongs to user
    content = await session.get(MovieHeavenContent, data.content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this content")

    # Check runtime requirements
    if festival.min_runtime_minutes and content.runtime_minutes < festival.min_runtime_minutes:
        raise HTTPException(
            status_code=400,
            detail=f"Content runtime ({content.runtime_minutes} min) below minimum ({festival.min_runtime_minutes} min)",
        )
    if festival.max_runtime_minutes and content.runtime_minutes > festival.max_runtime_minutes:
        raise HTTPException(
            status_code=400,
            detail=f"Content runtime ({content.runtime_minutes} min) exceeds maximum ({festival.max_runtime_minutes} min)",
        )

    # Check genre requirements
    if festival.accepted_genres:
        matching_genres = set(content.genres) & set(festival.accepted_genres)
        if not matching_genres:
            raise HTTPException(
                status_code=400,
                detail=f"Content must be in accepted genres: {festival.accepted_genres}",
            )

    # Check if already submitted
    existing = await session.execute(
        select(FestivalSubmission).where(
            and_(
                FestivalSubmission.festival_id == festival_id,
                FestivalSubmission.content_id == data.content_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Content already submitted to this festival")

    # TODO: Process submission fee payment via Stripe

    submission = FestivalSubmission(
        festival_id=festival_id,
        content_id=data.content_id,
        submitter_id=current_user.id,
        status=SubmissionStatus.SUBMITTED,
        fee_paid=festival.submission_fee,
        director_statement=data.director_statement,
        category=data.category,
    )

    session.add(submission)

    # Update festival submission count
    festival.submission_count += 1

    # Enable festival circuit on content
    content.festival_circuit_enabled = True

    await session.commit()
    await session.refresh(submission)

    logger.info(f"Content {data.content_id} submitted to festival {festival.name}")
    return submission


@router.get("/{festival_id}/submissions", response_model=list[FestivalSubmissionResponse])
async def list_festival_submissions(
    festival_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> list[FestivalSubmission]:
    """List submissions to a festival."""
    query = select(FestivalSubmission).where(FestivalSubmission.festival_id == festival_id)

    if status:
        try:
            submission_status = SubmissionStatus(status)
            query = query.where(FestivalSubmission.status == submission_status)
        except ValueError:
            pass

    query = query.order_by(desc(FestivalSubmission.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/submissions/mine", response_model=list[FestivalSubmissionResponse])
async def get_my_submissions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[FestivalSubmission]:
    """Get user's festival submissions."""
    query = (
        select(FestivalSubmission)
        .where(FestivalSubmission.submitter_id == current_user.id)
        .order_by(desc(FestivalSubmission.created_at))
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/submissions/{submission_id}", response_model=FestivalSubmissionResponse)
async def get_submission(
    submission_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> FestivalSubmission:
    """Get submission details."""
    submission = await session.get(FestivalSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


# ============================================================================
# Judging (Admin/Judge only)
# ============================================================================


@router.post("/submissions/{submission_id}/judge")
async def judge_submission(
    submission_id: UUID,
    score: float = Query(ge=0, le=100),
    notes: Optional[str] = None,
    judge_name: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FestivalSubmissionResponse:
    """Add a judge score to a submission."""
    submission = await session.get(FestivalSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get festival to check status
    festival = await session.get(FilmFestival, submission.festival_id)
    if festival and festival.status != FestivalStatus.JUDGING:
        raise HTTPException(status_code=400, detail="Festival is not in judging phase")

    # Add judge score
    if not submission.judge_scores:
        submission.judge_scores = {}
    submission.judge_scores[judge_name] = score

    # Calculate average score
    scores = list(submission.judge_scores.values())
    submission.average_score = sum(scores) / len(scores)

    # Update notes
    if notes:
        submission.judge_notes = notes

    # Update status to under_review
    if submission.status == SubmissionStatus.SUBMITTED:
        submission.status = SubmissionStatus.UNDER_REVIEW

    await session.commit()
    await session.refresh(submission)

    logger.info(f"Judge {judge_name} scored submission {submission_id}: {score}")
    return submission


@router.post("/submissions/{submission_id}/select")
async def select_submission(
    submission_id: UUID,
    selection_type: str = Query(...),  # selected, finalist, winner
    award_name: Optional[str] = None,
    prize_amount: Decimal = Decimal("0.00"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FestivalSubmissionResponse:
    """Select a submission (selected, finalist, or winner)."""
    submission = await session.get(FestivalSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Update status
    try:
        submission.status = SubmissionStatus(selection_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid selection type")

    # Set award if winner
    if selection_type == "winner" and award_name:
        submission.award_received = award_name
        submission.prize_amount = prize_amount

        # Update content festival stats
        content = await session.get(MovieHeavenContent, submission.content_id)
        if content:
            content.festival_wins += 1

    elif selection_type == "finalist":
        content = await session.get(MovieHeavenContent, submission.content_id)
        if content:
            content.festival_nominations += 1

    await session.commit()
    await session.refresh(submission)

    logger.info(f"Submission {submission_id} selected as {selection_type}")
    return submission


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: UUID,
    reason: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FestivalSubmissionResponse:
    """Reject a submission."""
    submission = await session.get(FestivalSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = SubmissionStatus.REJECTED
    if reason:
        submission.judge_notes = reason

    await session.commit()
    await session.refresh(submission)

    logger.info(f"Submission {submission_id} rejected")
    return submission


# ============================================================================
# Festival Winners/Results
# ============================================================================


@router.get("/{festival_id}/winners", response_model=list[FestivalSubmissionResponse])
async def get_festival_winners(
    festival_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[FestivalSubmission]:
    """Get festival winners."""
    query = (
        select(FestivalSubmission)
        .where(
            and_(
                FestivalSubmission.festival_id == festival_id,
                FestivalSubmission.status == SubmissionStatus.WINNER,
            )
        )
        .order_by(desc(FestivalSubmission.prize_amount))
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{festival_id}/finalists", response_model=list[FestivalSubmissionResponse])
async def get_festival_finalists(
    festival_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[FestivalSubmission]:
    """Get festival finalists."""
    query = (
        select(FestivalSubmission)
        .where(
            and_(
                FestivalSubmission.festival_id == festival_id,
                FestivalSubmission.status.in_(
                    [SubmissionStatus.FINALIST, SubmissionStatus.WINNER]
                ),
            )
        )
        .order_by(desc(FestivalSubmission.average_score))
    )

    result = await session.execute(query)
    return list(result.scalars().all())
