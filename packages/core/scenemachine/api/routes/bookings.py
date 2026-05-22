"""Booking API routes for ActForge marketplace."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.database import get_session
from scenemachine.models import (
    Booking,
    BookingMode,
    BookingStatus,
    PaymentStatus,
    PerformanceTake,
    Performer,
    PerformerAvailability,
    PerformerRating,
)
from scenemachine.services.performer_payouts import get_payout_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class BlinkBookingRequest(BaseModel):
    """Request for Blink mode (10-second auto-match)."""

    project_id: UUID
    shot_id: UUID | None = None
    duration_seconds: float = Field(default=10.0, ge=1.0, le=30.0)
    emotion_requirements: list[str] = Field(default_factory=list)
    max_price_usd: float | None = Field(default=None, ge=1.0)
    special_instructions: str | None = None


class DeepBookingRequest(BaseModel):
    """Request for Deep mode (method acting)."""

    project_id: UUID
    shot_id: UUID | None = None
    performer_id: UUID
    duration_seconds: float = Field(default=120.0, ge=30.0, le=300.0)
    emotion_requirements: list[str] = Field(default_factory=list)
    motion_requirements: dict | None = None
    special_instructions: str | None = None
    character_context: str | None = None
    scene_description: str | None = None


class EpicBookingRequest(BaseModel):
    """Request for Epic mode (long-form)."""

    project_id: UUID
    shot_id: UUID | None = None
    performer_id: UUID
    duration_seconds: float = Field(default=600.0, ge=300.0, le=1200.0)
    emotion_requirements: list[str] = Field(default_factory=list)
    motion_requirements: dict | None = None
    special_instructions: str | None = None
    character_context: str | None = None
    scene_description: str | None = None


class BookingDeliveryRequest(BaseModel):
    """Request to deliver a take for a booking."""

    take_id: UUID


class BookingRatingRequest(BaseModel):
    """Request to rate a performer after booking completion."""

    overall_score: float = Field(..., ge=1.0, le=5.0)
    motion_quality_score: float | None = Field(default=None, ge=1.0, le=5.0)
    emotion_accuracy_score: float | None = Field(default=None, ge=1.0, le=5.0)
    professionalism_score: float | None = Field(default=None, ge=1.0, le=5.0)
    timeliness_score: float | None = Field(default=None, ge=1.0, le=5.0)
    would_rehire: bool
    review_text: str | None = None
    review_title: str | None = None
    is_public: bool = True


class DisputeRequest(BaseModel):
    """Request to dispute a booking delivery."""

    reason: str = Field(..., min_length=10, max_length=2000)


class PerformerSummaryResponse(BaseModel):
    """Performer summary for booking responses."""

    id: str
    stage_name: str
    performer_type: str
    aci_score: float
    profile_image_url: str | None


class BookingResponse(BaseModel):
    """Booking response."""

    id: str
    project_id: str
    shot_id: str | None
    performer: PerformerSummaryResponse | None
    booking_mode: str
    status: str
    duration_requested_seconds: float
    duration_delivered_seconds: float | None
    emotion_requirements: list[str]
    price_usd: float
    platform_fee_usd: float
    performer_payout_usd: float
    payment_status: str
    retry_count: int
    max_retries: int
    take_id: str | None
    requested_at: str
    matched_at: str | None
    accepted_at: str | None
    delivered_at: str | None
    completed_at: str | None


class BookingListResponse(BaseModel):
    """List of bookings response."""

    bookings: list[BookingResponse]
    total: int
    page: int
    page_size: int


class BlinkMatchResponse(BaseModel):
    """Response for Blink mode auto-match."""

    booking_id: str
    matched_performer: PerformerSummaryResponse
    estimated_delivery_seconds: int
    price_usd: float
    status: str


# =============================================================================
# Helper Functions
# =============================================================================


def booking_to_response(booking: Booking) -> BookingResponse:
    """Convert booking model to response."""
    performer_summary = None
    if booking.performer:
        performer_summary = PerformerSummaryResponse(
            id=str(booking.performer.id),
            stage_name=booking.performer.stage_name,
            performer_type=booking.performer.performer_type.value,
            aci_score=booking.performer.aci_score,
            profile_image_url=booking.performer.profile_image_path,
        )

    return BookingResponse(
        id=str(booking.id),
        project_id=str(booking.project_id),
        shot_id=str(booking.shot_id) if booking.shot_id else None,
        performer=performer_summary,
        booking_mode=booking.booking_mode.value,
        status=booking.status.value,
        duration_requested_seconds=booking.duration_requested_seconds,
        duration_delivered_seconds=booking.duration_delivered_seconds,
        emotion_requirements=booking.emotion_requirements or [],
        price_usd=booking.price_usd,
        platform_fee_usd=booking.platform_fee_usd,
        performer_payout_usd=booking.performer_payout_usd,
        payment_status=booking.payment_status.value,
        retry_count=booking.retry_count,
        max_retries=booking.max_retries,
        take_id=str(booking.take_id) if booking.take_id else None,
        requested_at=booking.requested_at.isoformat(),
        matched_at=booking.matched_at.isoformat() if booking.matched_at else None,
        accepted_at=booking.accepted_at.isoformat() if booking.accepted_at else None,
        delivered_at=booking.delivered_at.isoformat() if booking.delivered_at else None,
        completed_at=booking.completed_at.isoformat() if booking.completed_at else None,
    )


async def find_available_performer(
    session: AsyncSession,
    emotion_requirements: list[str],
    max_price: float | None,
    duration_seconds: float,
) -> Performer | None:
    """Find an available performer matching requirements."""
    stmt = (
        select(Performer)
        .where(
            and_(
                Performer.is_active == True,  # noqa: E712
                Performer.availability_status == PerformerAvailability.AVAILABLE,
            )
        )
        .order_by(Performer.aci_score.desc())
    )

    result = await session.execute(stmt)
    performers = result.scalars().all()

    for performer in performers:
        # Check price
        if max_price and performer.pricing:
            blink_price = performer.pricing.get("blink", 0)
            if blink_price > max_price:
                continue

        # Check specialties match emotions (basic matching)
        if emotion_requirements and performer.specialties:
            # Simple check: at least some overlap
            if not any(e.lower() in [s.lower() for s in performer.specialties] for e in emotion_requirements):
                continue

        return performer

    return None


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=BookingListResponse)
async def list_bookings(
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: BookingStatus | None = Query(None),
    mode_filter: BookingMode | None = Query(None),
    project_id: UUID | None = Query(None),
    performer_id: UUID | None = Query(None),
) -> BookingListResponse:
    """List bookings with filtering and pagination."""
    stmt = select(Booking).options(selectinload(Booking.performer))

    # Apply filters
    if status_filter:
        stmt = stmt.where(Booking.status == status_filter)
    if mode_filter:
        stmt = stmt.where(Booking.booking_mode == mode_filter)
    if project_id:
        stmt = stmt.where(Booking.project_id == project_id)
    if performer_id:
        stmt = stmt.where(Booking.performer_id == performer_id)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Booking.requested_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    bookings = result.scalars().all()

    return BookingListResponse(
        bookings=[booking_to_response(b) for b in bookings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """Get booking details."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.performer))
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    return booking_to_response(booking)


@router.post("/blink", response_model=BlinkMatchResponse, status_code=status.HTTP_201_CREATED)
async def create_blink_booking(
    request: BlinkBookingRequest,
    session: AsyncSession = Depends(get_session),
    requester_user_id: UUID = Query(...),  # In production, get from auth
) -> BlinkMatchResponse:
    """
    Create a Blink mode booking (10-second auto-match).

    Automatically finds the best available performer and creates a booking.
    """
    # Find matching performer
    performer = await find_available_performer(
        session,
        request.emotion_requirements,
        request.max_price_usd,
        request.duration_seconds,
    )

    if not performer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No available performers matching requirements",
        )

    # Calculate price
    price = 5.0  # Default Blink price
    if performer.pricing and "blink" in performer.pricing:
        price = performer.pricing["blink"]

    # Calculate payout split
    payout_service = get_payout_service(session)
    calculation = payout_service.calculate_payout(price, performer.lifetime_earnings_usd)

    # Create booking
    now = datetime.now(UTC)
    booking = Booking(
        project_id=request.project_id,
        shot_id=request.shot_id,
        performer_id=performer.id,
        requester_user_id=requester_user_id,
        booking_mode=BookingMode.BLINK,
        status=BookingStatus.MATCHED,
        duration_requested_seconds=request.duration_seconds,
        emotion_requirements=request.emotion_requirements,
        special_instructions=request.special_instructions,
        price_usd=price,
        platform_fee_usd=float(calculation.platform_fee_usd),
        performer_payout_usd=float(calculation.performer_payout_usd),
        max_price_usd=request.max_price_usd,
        payment_status=PaymentStatus.PENDING,
        requested_at=now,
        matched_at=now,
        expires_at=now + timedelta(hours=1),
    )

    session.add(booking)

    # Update performer stats
    performer.total_bookings += 1

    await session.commit()
    await session.refresh(booking)

    logger.info(f"Created Blink booking {booking.id} with performer {performer.stage_name}")

    return BlinkMatchResponse(
        booking_id=str(booking.id),
        matched_performer=PerformerSummaryResponse(
            id=str(performer.id),
            stage_name=performer.stage_name,
            performer_type=performer.performer_type.value,
            aci_score=performer.aci_score,
            profile_image_url=performer.profile_image_path,
        ),
        estimated_delivery_seconds=10,
        price_usd=price,
        status=BookingStatus.MATCHED.value,
    )


@router.post("/deep", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_deep_booking(
    request: DeepBookingRequest,
    session: AsyncSession = Depends(get_session),
    requester_user_id: UUID = Query(...),
) -> BookingResponse:
    """
    Create a Deep mode booking (method acting).

    Requires specifying a performer. The performer must accept the booking.
    """
    # Get performer
    performer_stmt = select(Performer).where(Performer.id == request.performer_id)
    performer_result = await session.execute(performer_stmt)
    performer = performer_result.scalar_one_or_none()

    if not performer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performer not found",
        )

    if performer.availability_status != PerformerAvailability.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Performer is not available",
        )

    # Calculate price
    price = 25.0  # Default Deep price
    if performer.pricing and "deep" in performer.pricing:
        price = performer.pricing["deep"]

    # Calculate payout split
    payout_service = get_payout_service(session)
    calculation = payout_service.calculate_payout(price, performer.lifetime_earnings_usd)

    # Create booking
    now = datetime.now(UTC)
    booking = Booking(
        project_id=request.project_id,
        shot_id=request.shot_id,
        performer_id=performer.id,
        requester_user_id=requester_user_id,
        booking_mode=BookingMode.DEEP,
        status=BookingStatus.REQUESTED,
        duration_requested_seconds=request.duration_seconds,
        emotion_requirements=request.emotion_requirements,
        motion_requirements=request.motion_requirements,
        special_instructions=request.special_instructions,
        character_context=request.character_context,
        scene_description=request.scene_description,
        price_usd=price,
        platform_fee_usd=float(calculation.platform_fee_usd),
        performer_payout_usd=float(calculation.performer_payout_usd),
        payment_status=PaymentStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(hours=24),
    )

    session.add(booking)

    # Update performer stats
    performer.total_bookings += 1

    await session.commit()
    await session.refresh(booking)

    return booking_to_response(booking)


@router.post("/epic", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_epic_booking(
    request: EpicBookingRequest,
    session: AsyncSession = Depends(get_session),
    requester_user_id: UUID = Query(...),
) -> BookingResponse:
    """
    Create an Epic mode booking (long-form).

    For feature-length takes (5-20 minutes). Requires performer acceptance.
    """
    # Get performer
    performer_stmt = select(Performer).where(Performer.id == request.performer_id)
    performer_result = await session.execute(performer_stmt)
    performer = performer_result.scalar_one_or_none()

    if not performer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performer not found",
        )

    if performer.availability_status != PerformerAvailability.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Performer is not available",
        )

    # Calculate price (per minute)
    minutes = request.duration_seconds / 60
    price_per_minute = 10.0  # Default Epic price per minute
    if performer.pricing and "epic_per_minute" in performer.pricing:
        price_per_minute = performer.pricing["epic_per_minute"]
    price = price_per_minute * minutes

    # Calculate payout split
    payout_service = get_payout_service(session)
    calculation = payout_service.calculate_payout(price, performer.lifetime_earnings_usd)

    # Create booking
    now = datetime.now(UTC)
    booking = Booking(
        project_id=request.project_id,
        shot_id=request.shot_id,
        performer_id=performer.id,
        requester_user_id=requester_user_id,
        booking_mode=BookingMode.EPIC,
        status=BookingStatus.REQUESTED,
        duration_requested_seconds=request.duration_seconds,
        emotion_requirements=request.emotion_requirements,
        motion_requirements=request.motion_requirements,
        special_instructions=request.special_instructions,
        character_context=request.character_context,
        scene_description=request.scene_description,
        price_usd=price,
        platform_fee_usd=float(calculation.platform_fee_usd),
        performer_payout_usd=float(calculation.performer_payout_usd),
        payment_status=PaymentStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(hours=48),
    )

    session.add(booking)

    # Update performer stats
    performer.total_bookings += 1

    await session.commit()
    await session.refresh(booking)

    return booking_to_response(booking)


@router.post("/{booking_id}/accept", response_model=BookingResponse)
async def accept_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """Performer accepts a booking."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.performer))
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if not booking.can_transition_to(BookingStatus.ACCEPTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept booking in {booking.status.value} status",
        )

    booking.status = BookingStatus.ACCEPTED
    booking.accepted_at = datetime.now(UTC)
    booking.payment_status = PaymentStatus.ESCROWED

    await session.commit()
    await session.refresh(booking)

    logger.info(f"Booking {booking_id} accepted")

    return booking_to_response(booking)


@router.post("/{booking_id}/deliver", response_model=BookingResponse)
async def deliver_booking(
    booking_id: UUID,
    request: BookingDeliveryRequest,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """Performer delivers a take for the booking."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.performer))
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Verify take exists and belongs to performer
    take_stmt = select(PerformanceTake).where(PerformanceTake.id == request.take_id)
    take_result = await session.execute(take_stmt)
    take = take_result.scalar_one_or_none()

    if not take:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Take not found",
        )

    if take.performer_id != booking.performer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Take does not belong to the booking's performer",
        )

    if booking.status not in [BookingStatus.ACCEPTED, BookingStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot deliver in {booking.status.value} status",
        )

    booking.status = BookingStatus.DELIVERED
    booking.take_id = take.id
    booking.duration_delivered_seconds = take.duration_seconds
    booking.delivered_at = datetime.now(UTC)

    # Increment take usage
    take.increment_usage()

    await session.commit()
    await session.refresh(booking)

    logger.info(f"Booking {booking_id} delivered with take {take.id}")

    return booking_to_response(booking)


@router.post("/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """Director approves the delivered take."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.performer))
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if not booking.can_transition_to(BookingStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve booking in {booking.status.value} status",
        )

    booking.status = BookingStatus.APPROVED
    booking.approved_at = datetime.now(UTC)

    # Process payout
    payout_service = get_payout_service(session)
    await payout_service.process_booking_payout(booking_id)

    await session.commit()
    await session.refresh(booking)

    logger.info(f"Booking {booking_id} approved")

    return booking_to_response(booking)


@router.post("/{booking_id}/dispute", response_model=BookingResponse)
async def dispute_booking(
    booking_id: UUID,
    request: DisputeRequest,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """Director disputes the delivered take."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.performer))
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if not booking.can_transition_to(BookingStatus.DISPUTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispute booking in {booking.status.value} status",
        )

    booking.status = BookingStatus.DISPUTED
    booking.is_disputed = True
    booking.dispute_reason = request.reason
    booking.disputed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(booking)

    logger.info(f"Booking {booking_id} disputed: {request.reason[:50]}...")

    return booking_to_response(booking)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """Cancel a booking."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.performer))
    )
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel booking in {booking.status.value} status",
        )

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.now(UTC)

    # Refund if escrowed
    if booking.payment_status == PaymentStatus.ESCROWED:
        booking.payment_status = PaymentStatus.REFUNDED

    await session.commit()
    await session.refresh(booking)

    logger.info(f"Booking {booking_id} cancelled")

    return booking_to_response(booking)


@router.post("/{booking_id}/rate")
async def rate_booking(
    booking_id: UUID,
    request: BookingRatingRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Rate the performer after booking completion."""
    stmt = select(Booking).where(Booking.id == booking_id)
    result = await session.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only rate completed bookings",
        )

    # Check if already rated
    existing_stmt = select(PerformerRating).where(PerformerRating.booking_id == booking_id)
    existing_result = await session.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking already rated",
        )

    # Create rating
    rating = PerformerRating(
        booking_id=booking_id,
        performer_id=booking.performer_id,
        rater_user_id=booking.requester_user_id,
        overall_score=request.overall_score,
        motion_quality_score=request.motion_quality_score,
        emotion_accuracy_score=request.emotion_accuracy_score,
        professionalism_score=request.professionalism_score,
        timeliness_score=request.timeliness_score,
        would_rehire=request.would_rehire,
        review_text=request.review_text,
        review_title=request.review_title,
        is_public=request.is_public,
        rated_at=datetime.now(UTC),
    )

    session.add(rating)
    await session.commit()

    logger.info(f"Rated booking {booking_id} with score {request.overall_score}")

    return {
        "message": "Rating submitted successfully",
        "rating_id": str(rating.id),
    }
