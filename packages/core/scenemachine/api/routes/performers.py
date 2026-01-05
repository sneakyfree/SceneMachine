"""Performer API routes for ActForge marketplace."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.database import get_session
from scenemachine.models import (
    Performer,
    PerformerType,
    PerformerAvailability,
    PerformerVerification,
    PerformanceTake,
    TakeStatus,
)
from scenemachine.services.aci import get_aci_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performers", tags=["performers"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class PerformerPricingSchema(BaseModel):
    """Performer pricing schema."""

    blink: Optional[float] = None
    deep: Optional[float] = None
    epic_per_minute: Optional[float] = None
    auction_minimum: Optional[float] = None


class MotionCapabilitiesSchema(BaseModel):
    """Motion capabilities schema."""

    supports_liveportrait: bool = True
    supports_roop_gs_anim: bool = True
    supported_resolutions: List[str] = Field(default_factory=lambda: ["480p", "720p", "1080p"])
    max_take_duration_seconds: int = 1200
    face_tracking_quality: str = "high"
    body_tracking: bool = False
    hand_tracking: bool = True


class PerformerCreateRequest(BaseModel):
    """Request to create a performer profile."""

    stage_name: str = Field(..., min_length=1, max_length=255)
    performer_type: PerformerType = PerformerType.HUMAN
    bio: Optional[str] = None
    specialties: List[str] = Field(default_factory=list)
    pricing: Optional[PerformerPricingSchema] = None
    motion_capabilities: Optional[MotionCapabilitiesSchema] = None


class PerformerUpdateRequest(BaseModel):
    """Request to update a performer profile."""

    stage_name: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[List[str]] = None
    pricing: Optional[PerformerPricingSchema] = None
    motion_capabilities: Optional[MotionCapabilitiesSchema] = None
    availability_status: Optional[PerformerAvailability] = None


class PerformerListItemResponse(BaseModel):
    """Performer list item response."""

    id: str
    stage_name: str
    performer_type: str
    profile_image_url: Optional[str]
    specialties: List[str]
    aci_score: float
    availability_status: str
    verification_status: str
    total_bookings: int
    average_rating: Optional[float]
    pricing: Optional[dict]


class PerformerDetailResponse(PerformerListItemResponse):
    """Detailed performer response."""

    bio: Optional[str]
    motion_capabilities: Optional[dict]
    demo_reel_takes: List[dict]
    revenue_split_percent: float
    completed_bookings: int
    joined_at: str
    last_active_at: Optional[str]


class PerformerListResponse(BaseModel):
    """List of performers response."""

    performers: List[PerformerListItemResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class TakeResponse(BaseModel):
    """Performance take response."""

    id: str
    take_name: str
    mode: str
    duration_seconds: float
    emotion_tags: List[str]
    motion_score: float
    status: str
    is_demo_reel: bool
    thumbnail_url: Optional[str]
    preview_video_url: Optional[str]
    usage_count: int
    recording_date: str


class ACIBreakdownResponse(BaseModel):
    """ACI score breakdown response."""

    placement_rate: float
    placement_rate_weighted: float
    rehire_rate: float
    rehire_rate_weighted: float
    audience_buzz: float
    audience_buzz_weighted: float
    motion_score: float
    motion_score_weighted: float
    total_score: float
    is_reliable: bool
    data_quality: str
    total_bookings: int
    total_ratings: int
    total_takes: int


class LeaderboardEntryResponse(BaseModel):
    """Leaderboard entry response."""

    rank: int
    performer_id: str
    stage_name: str
    aci_score: float
    performer_type: str
    total_bookings: int
    specialties: List[str]


# =============================================================================
# Helper Functions
# =============================================================================


def performer_to_list_response(performer: Performer) -> PerformerListItemResponse:
    """Convert performer model to list response."""
    return PerformerListItemResponse(
        id=str(performer.id),
        stage_name=performer.stage_name,
        performer_type=performer.performer_type.value,
        profile_image_url=performer.profile_image_path,
        specialties=performer.specialties or [],
        aci_score=performer.aci_score,
        availability_status=performer.availability_status.value,
        verification_status=performer.verification_status.value,
        total_bookings=performer.total_bookings,
        average_rating=performer.average_rating,
        pricing=performer.pricing,
    )


def performer_to_detail_response(performer: Performer) -> PerformerDetailResponse:
    """Convert performer model to detail response."""
    # Get demo reel takes
    demo_takes = []
    if performer.takes:
        for take in performer.takes:
            if take.is_demo_reel and take.status == TakeStatus.AVAILABLE:
                demo_takes.append({
                    "id": str(take.id),
                    "take_name": take.take_name,
                    "duration_seconds": take.duration_seconds,
                    "emotion_tags": take.emotion_tags or [],
                    "thumbnail_url": take.thumbnail_path,
                    "preview_video_url": take.preview_video_path,
                })

    return PerformerDetailResponse(
        id=str(performer.id),
        stage_name=performer.stage_name,
        performer_type=performer.performer_type.value,
        profile_image_url=performer.profile_image_path,
        specialties=performer.specialties or [],
        aci_score=performer.aci_score,
        availability_status=performer.availability_status.value,
        verification_status=performer.verification_status.value,
        total_bookings=performer.total_bookings,
        average_rating=performer.average_rating,
        pricing=performer.pricing,
        bio=performer.bio,
        motion_capabilities=performer.motion_capabilities,
        demo_reel_takes=demo_takes,
        revenue_split_percent=performer.revenue_split_percent,
        completed_bookings=performer.completed_bookings,
        joined_at=performer.joined_at.isoformat() if performer.joined_at else "",
        last_active_at=performer.last_active_at.isoformat() if performer.last_active_at else None,
    )


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=PerformerListResponse)
async def list_performers(
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    specialties: Optional[List[str]] = Query(None),
    min_aci: Optional[float] = Query(None, ge=0, le=100),
    max_price: Optional[float] = Query(None, ge=0),
    availability: Optional[PerformerAvailability] = None,
    performer_type: Optional[PerformerType] = None,
    sort_by: str = Query("aci", regex="^(aci|price|availability|rating)$"),
    search: Optional[str] = None,
) -> PerformerListResponse:
    """
    List performers with filtering and pagination.

    Query Parameters:
        - page: Page number (default 1)
        - page_size: Results per page (default 20, max 100)
        - specialties: Filter by specialties (e.g., dramatic, comedic)
        - min_aci: Minimum ACI score
        - max_price: Maximum price (for blink mode)
        - availability: Filter by availability status
        - performer_type: Filter by human/synthetic
        - sort_by: Sort field (aci, price, availability, rating)
        - search: Search by stage name
    """
    # Build base query
    stmt = select(Performer).where(Performer.is_active == True)  # noqa: E712

    # Apply filters
    if specialties:
        # Check if any specialty matches
        for specialty in specialties:
            stmt = stmt.where(Performer.specialties.contains([specialty]))

    if min_aci is not None:
        stmt = stmt.where(Performer.aci_score >= min_aci)

    if availability:
        stmt = stmt.where(Performer.availability_status == availability)

    if performer_type:
        stmt = stmt.where(Performer.performer_type == performer_type)

    if search:
        stmt = stmt.where(Performer.stage_name.ilike(f"%{search}%"))

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply sorting
    if sort_by == "aci":
        stmt = stmt.order_by(Performer.aci_score.desc())
    elif sort_by == "rating":
        stmt = stmt.order_by(Performer.aci_score.desc())  # Use ACI as proxy for rating
    elif sort_by == "availability":
        stmt = stmt.order_by(Performer.availability_status.asc())
    else:
        stmt = stmt.order_by(Performer.aci_score.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # Execute query
    result = await session.execute(stmt)
    performers = result.scalars().all()

    # Convert to response
    return PerformerListResponse(
        performers=[performer_to_list_response(p) for p in performers],
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(performers) < total,
    )


@router.get("/featured", response_model=List[PerformerListItemResponse])
async def get_featured_performers(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(10, ge=1, le=50),
) -> List[PerformerListItemResponse]:
    """
    Get featured/top performers.

    Returns top performers by ACI score who are currently available.
    """
    stmt = (
        select(Performer)
        .where(
            and_(
                Performer.is_active == True,  # noqa: E712
                Performer.availability_status == PerformerAvailability.AVAILABLE,
                Performer.verification_status.in_([
                    PerformerVerification.VERIFIED,
                    PerformerVerification.ELITE,
                ]),
            )
        )
        .order_by(Performer.aci_score.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    performers = result.scalars().all()

    return [performer_to_list_response(p) for p in performers]


@router.get("/leaderboard", response_model=List[LeaderboardEntryResponse])
async def get_leaderboard(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=500),
    min_bookings: int = Query(5, ge=0),
) -> List[LeaderboardEntryResponse]:
    """
    Get ACI leaderboard.

    Returns performers ranked by ACI score with minimum booking requirement.
    """
    aci_service = get_aci_service(session)
    leaderboard = await aci_service.get_leaderboard(limit=limit, min_bookings=min_bookings)

    return [LeaderboardEntryResponse(**entry) for entry in leaderboard]


@router.get("/{performer_id}", response_model=PerformerDetailResponse)
async def get_performer(
    performer_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PerformerDetailResponse:
    """Get detailed performer profile."""
    stmt = (
        select(Performer)
        .where(Performer.id == performer_id)
        .options(selectinload(Performer.takes))
    )
    result = await session.execute(stmt)
    performer = result.scalar_one_or_none()

    if not performer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performer not found",
        )

    return performer_to_detail_response(performer)


@router.get("/{performer_id}/takes", response_model=List[TakeResponse])
async def get_performer_takes(
    performer_id: UUID,
    session: AsyncSession = Depends(get_session),
    demo_only: bool = Query(False),
) -> List[TakeResponse]:
    """Get performer's available takes."""
    # Verify performer exists
    performer_stmt = select(Performer.id).where(Performer.id == performer_id)
    performer_result = await session.execute(performer_stmt)
    if not performer_result.scalar():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performer not found",
        )

    # Get takes
    stmt = (
        select(PerformanceTake)
        .where(
            and_(
                PerformanceTake.performer_id == performer_id,
                PerformanceTake.status == TakeStatus.AVAILABLE,
            )
        )
        .order_by(PerformanceTake.created_at.desc())
    )

    if demo_only:
        stmt = stmt.where(PerformanceTake.is_demo_reel == True)  # noqa: E712

    result = await session.execute(stmt)
    takes = result.scalars().all()

    return [
        TakeResponse(
            id=str(take.id),
            take_name=take.take_name,
            mode=take.mode.value,
            duration_seconds=take.duration_seconds,
            emotion_tags=take.emotion_tags or [],
            motion_score=take.motion_score,
            status=take.status.value,
            is_demo_reel=take.is_demo_reel,
            thumbnail_url=take.thumbnail_path,
            preview_video_url=take.preview_video_path,
            usage_count=take.usage_count,
            recording_date=take.recording_date.isoformat(),
        )
        for take in takes
    ]


@router.get("/{performer_id}/stats", response_model=ACIBreakdownResponse)
async def get_performer_stats(
    performer_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ACIBreakdownResponse:
    """Get performer's ACI breakdown and statistics."""
    aci_service = get_aci_service(session)

    try:
        breakdown = await aci_service.calculate_aci(performer_id, update_performer=False)
        return ACIBreakdownResponse(**breakdown.to_dict())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("", response_model=PerformerDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_performer(
    request: PerformerCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> PerformerDetailResponse:
    """Create a new performer profile."""
    # Create performer
    performer = Performer(
        stage_name=request.stage_name,
        performer_type=request.performer_type,
        bio=request.bio,
        specialties=request.specialties,
        pricing=request.pricing.model_dump() if request.pricing else None,
        motion_capabilities=request.motion_capabilities.model_dump() if request.motion_capabilities else None,
        availability_status=PerformerAvailability.OFFLINE,
        verification_status=PerformerVerification.UNVERIFIED,
        joined_at=datetime.now(timezone.utc),
    )

    session.add(performer)
    await session.commit()
    await session.refresh(performer)

    logger.info(f"Created performer: {performer.id} ({performer.stage_name})")

    return performer_to_detail_response(performer)


@router.patch("/{performer_id}", response_model=PerformerDetailResponse)
async def update_performer(
    performer_id: UUID,
    request: PerformerUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> PerformerDetailResponse:
    """Update performer profile."""
    stmt = (
        select(Performer)
        .where(Performer.id == performer_id)
        .options(selectinload(Performer.takes))
    )
    result = await session.execute(stmt)
    performer = result.scalar_one_or_none()

    if not performer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performer not found",
        )

    # Update fields
    if request.stage_name is not None:
        performer.stage_name = request.stage_name
    if request.bio is not None:
        performer.bio = request.bio
    if request.specialties is not None:
        performer.specialties = request.specialties
    if request.pricing is not None:
        performer.pricing = request.pricing.model_dump()
    if request.motion_capabilities is not None:
        performer.motion_capabilities = request.motion_capabilities.model_dump()
    if request.availability_status is not None:
        performer.availability_status = request.availability_status
        if request.availability_status == PerformerAvailability.AVAILABLE:
            performer.last_active_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(performer)

    logger.info(f"Updated performer: {performer.id}")

    return performer_to_detail_response(performer)


@router.post("/{performer_id}/availability")
async def set_availability(
    performer_id: UUID,
    availability: PerformerAvailability,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Set performer availability status."""
    stmt = select(Performer).where(Performer.id == performer_id)
    result = await session.execute(stmt)
    performer = result.scalar_one_or_none()

    if not performer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performer not found",
        )

    performer.availability_status = availability
    if availability == PerformerAvailability.AVAILABLE:
        performer.last_active_at = datetime.now(timezone.utc)

    await session.commit()

    return {
        "performer_id": str(performer_id),
        "availability_status": availability.value,
    }
