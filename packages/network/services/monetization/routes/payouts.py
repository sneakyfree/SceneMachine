"""
Payout routes for monetization service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    CreatorProfile,
    Payout,
    PayoutStatus,
    Transaction,
    TransactionStatus,
    User,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    PayoutRequestRequest,
    PayoutResponse,
    PayoutListResponse,
    StripeConnectStatusResponse,
    StripeConnectOnboardingRequest,
)
from ..stripe_service import stripe_service

router = APIRouter(prefix="/payouts", tags=["payouts"])

MINIMUM_PAYOUT = Decimal("25.00")


@router.get("/available")
async def get_available_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get available balance for payout."""
    # Get creator profile
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile or not profile.stripe_account_id:
        return {
            "available": Decimal("0"),
            "pending": Decimal("0"),
            "can_request_payout": False,
            "reason": "Stripe Connect not set up",
        }

    # Get Stripe balance
    balance = await stripe_service.get_balance(profile.stripe_account_id)

    can_request = balance["available"] >= MINIMUM_PAYOUT

    return {
        "available": balance["available"],
        "pending": balance["pending"],
        "minimum_payout": MINIMUM_PAYOUT,
        "can_request_payout": can_request,
        "reason": None if can_request else f"Minimum payout is ${MINIMUM_PAYOUT}",
    }


@router.post("/request", response_model=PayoutResponse)
async def request_payout(
    request: PayoutRequestRequest = PayoutRequestRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PayoutResponse:
    """Request a payout of available balance."""
    # Get creator profile
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile or not profile.stripe_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe Connect not set up",
        )

    # Get available balance
    balance = await stripe_service.get_balance(profile.stripe_account_id)
    available = balance["available"]

    # Determine amount
    amount = request.amount if request.amount else available

    if amount < MINIMUM_PAYOUT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum payout is ${MINIMUM_PAYOUT}",
        )

    if amount > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested amount exceeds available balance of ${available}",
        )

    # Check for pending payout
    result = await db.execute(
        select(Payout).where(
            and_(
                Payout.creator_id == current_user.id,
                Payout.status.in_([PayoutStatus.PENDING, PayoutStatus.PROCESSING]),
            )
        )
    )
    pending = result.scalar_one_or_none()
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending payout",
        )

    now = datetime.now(timezone.utc)

    # Create payout record
    payout = Payout(
        creator_id=current_user.id,
        amount=amount,
        status=PayoutStatus.PENDING,
        period_start=now - timedelta(days=30),  # Last 30 days
        period_end=now,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)

    # Initiate Stripe payout
    try:
        payout_result = await stripe_service.create_payout(
            amount_cents=int(amount * 100),
            connected_account_id=profile.stripe_account_id,
        )
        payout.stripe_payout_id = payout_result["payout_id"]
        payout.status = PayoutStatus.PROCESSING
        await db.commit()
    except Exception as e:
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = str(e)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate payout: {str(e)}",
        )

    return PayoutResponse.model_validate(payout)


@router.get("/history", response_model=PayoutListResponse)
async def get_payout_history(
    status_filter: PayoutStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PayoutListResponse:
    """Get payout history."""
    query = select(Payout).where(Payout.creator_id == current_user.id)

    if status_filter:
        query = query.where(Payout.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get payouts
    offset = (page - 1) * per_page
    query = query.order_by(Payout.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    payouts = result.scalars().all()

    return PayoutListResponse(
        payouts=[PayoutResponse.model_validate(p) for p in payouts],
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + len(payouts)) < total,
    )


@router.get("/{payout_id}", response_model=PayoutResponse)
async def get_payout(
    payout_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PayoutResponse:
    """Get a specific payout."""
    result = await db.execute(
        select(Payout).where(
            and_(
                Payout.id == payout_id,
                Payout.creator_id == current_user.id,
            )
        )
    )
    payout = result.scalar_one_or_none()

    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payout not found",
        )

    return PayoutResponse.model_validate(payout)


# Stripe Connect onboarding
@router.get("/connect/status", response_model=StripeConnectStatusResponse)
async def get_stripe_connect_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StripeConnectStatusResponse:
    """Get Stripe Connect account status."""
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile or not profile.stripe_account_id:
        return StripeConnectStatusResponse(
            is_connected=False,
            account_id=None,
            charges_enabled=False,
            payouts_enabled=False,
            details_submitted=False,
            onboarding_url=None,
        )

    # Get account status from Stripe
    account_status = await stripe_service.get_account_status(profile.stripe_account_id)

    return StripeConnectStatusResponse(
        is_connected=True,
        account_id=account_status["account_id"],
        charges_enabled=account_status["charges_enabled"],
        payouts_enabled=account_status["payouts_enabled"],
        details_submitted=account_status["details_submitted"],
        onboarding_url=None,
    )


@router.post("/connect/onboard")
async def start_stripe_onboarding(
    request: StripeConnectOnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start or continue Stripe Connect onboarding."""
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # Create creator profile
        profile = CreatorProfile(
            user_id=current_user.id,
            channel_name=current_user.display_name,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    if not profile.stripe_account_id:
        # Create Stripe Connect account
        account = await stripe_service.create_connect_account(
            user_email=current_user.email,
            user_id=str(current_user.id),
        )
        profile.stripe_account_id = account["account_id"]
        await db.commit()

    # Create account link for onboarding
    onboarding_url = await stripe_service.create_account_link(
        account_id=profile.stripe_account_id,
        return_url=request.return_url,
        refresh_url=request.refresh_url,
    )

    return {"onboarding_url": onboarding_url}
