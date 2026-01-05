"""
Payment routes for monetization service.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    CreatorProfile,
    MonetizationType,
    TicketPurchase,
    Tip,
    Transaction,
    TransactionType,
    TransactionStatus,
    User,
    Video,
    calculate_platform_fee,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    TicketPurchaseRequest,
    TicketPurchaseResponse,
    UserTicketsResponse,
    TipRequest,
    TipResponse,
    TipListResponse,
)
from ..stripe_service import stripe_service

router = APIRouter(tags=["payments"])


# Processing fee (2.9% + 30 cents)
STRIPE_PERCENT_FEE = Decimal("0.029")
STRIPE_FIXED_FEE = Decimal("0.30")


def calculate_processing_fee(amount: Decimal) -> Decimal:
    """Calculate Stripe processing fee."""
    return (amount * STRIPE_PERCENT_FEE + STRIPE_FIXED_FEE).quantize(Decimal("0.01"))


# Ticket purchases
@router.post("/tickets/purchase", response_model=TicketPurchaseResponse)
async def purchase_ticket(
    request: TicketPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketPurchaseResponse:
    """Purchase access to a paid video."""
    # Get video
    result = await db.execute(select(Video).where(Video.id == request.video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.monetization_type != MonetizationType.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not a paid video",
        )

    if not video.ticket_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video has no ticket price set",
        )

    # Check if already purchased
    result = await db.execute(
        select(TicketPurchase).where(
            and_(
                TicketPurchase.video_id == request.video_id,
                TicketPurchase.buyer_id == current_user.id,
                TicketPurchase.status == TransactionStatus.COMPLETED,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return TicketPurchaseResponse.model_validate(existing)

    # Get creator's Stripe account
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == video.creator_id)
    )
    creator_profile = result.scalar_one_or_none()

    if not creator_profile or not creator_profile.stripe_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator has not set up payments",
        )

    # Calculate fees
    amount = video.ticket_price
    amount_cents = int(amount * 100)
    processing_fee = calculate_processing_fee(amount)
    platform_fee = calculate_platform_fee(amount, creator_profile.total_earnings)
    application_fee_cents = int((platform_fee + processing_fee) * 100)

    # Create payment intent
    payment_result = await stripe_service.create_payment_intent(
        amount_cents=amount_cents,
        metadata={
            "type": "ticket",
            "video_id": str(request.video_id),
            "buyer_id": str(current_user.id),
        },
        connected_account_id=creator_profile.stripe_account_id,
        application_fee_cents=application_fee_cents,
    )

    # Create ticket purchase record
    ticket = TicketPurchase(
        video_id=request.video_id,
        buyer_id=current_user.id,
        amount=amount,
        stripe_payment_intent_id=payment_result["payment_intent_id"],
        status=TransactionStatus.PENDING,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    response = TicketPurchaseResponse.model_validate(ticket)
    response.stripe_client_secret = payment_result["client_secret"]
    return response


@router.get("/tickets/my-purchases", response_model=UserTicketsResponse)
async def get_my_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserTicketsResponse:
    """Get all tickets purchased by current user."""
    result = await db.execute(
        select(TicketPurchase)
        .where(
            and_(
                TicketPurchase.buyer_id == current_user.id,
                TicketPurchase.status == TransactionStatus.COMPLETED,
            )
        )
        .order_by(TicketPurchase.created_at.desc())
    )
    tickets = result.scalars().all()

    return UserTicketsResponse(
        tickets=[TicketPurchaseResponse.model_validate(t) for t in tickets],
        total=len(tickets),
    )


@router.get("/tickets/check/{video_id}")
async def check_ticket_access(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if user has access to a paid video."""
    result = await db.execute(
        select(TicketPurchase).where(
            and_(
                TicketPurchase.video_id == video_id,
                TicketPurchase.buyer_id == current_user.id,
                TicketPurchase.status == TransactionStatus.COMPLETED,
            )
        )
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        return {"has_access": False}

    # Check if expired
    if ticket.access_expires_at and ticket.access_expires_at < datetime.now(timezone.utc):
        return {"has_access": False, "expired": True}

    return {
        "has_access": True,
        "purchased_at": ticket.access_granted_at,
        "expires_at": ticket.access_expires_at,
    }


# Tips
@router.post("/tips", response_model=TipResponse)
async def send_tip(
    request: TipRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TipResponse:
    """Send a tip to a creator."""
    # Get creator's profile
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == request.creator_id)
    )
    creator_profile = result.scalar_one_or_none()

    if not creator_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator not found",
        )

    if not creator_profile.stripe_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator has not set up payments",
        )

    # Calculate fees
    amount = request.amount
    amount_cents = int(amount * 100)
    processing_fee = calculate_processing_fee(amount)
    platform_fee = calculate_platform_fee(amount, creator_profile.total_earnings)
    application_fee_cents = int((platform_fee + processing_fee) * 100)

    # Create payment intent
    metadata = {
        "type": "tip",
        "creator_id": str(request.creator_id),
        "tipper_id": str(current_user.id),
    }
    if request.video_id:
        metadata["video_id"] = str(request.video_id)

    payment_result = await stripe_service.create_payment_intent(
        amount_cents=amount_cents,
        metadata=metadata,
        connected_account_id=creator_profile.stripe_account_id,
        application_fee_cents=application_fee_cents,
    )

    # Create tip record
    tip = Tip(
        creator_id=request.creator_id,
        tipper_id=current_user.id,
        video_id=request.video_id,
        amount=amount,
        message=request.message,
        is_public=request.is_public,
        stripe_payment_intent_id=payment_result["payment_intent_id"],
        status=TransactionStatus.PENDING,
    )
    db.add(tip)
    await db.commit()
    await db.refresh(tip)

    response = TipResponse.model_validate(tip)
    response.stripe_client_secret = payment_result["client_secret"]
    return response


@router.get("/tips/received", response_model=TipListResponse)
async def get_received_tips(
    video_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TipListResponse:
    """Get tips received by current user."""
    query = select(Tip).where(
        and_(
            Tip.creator_id == current_user.id,
            Tip.status == TransactionStatus.COMPLETED,
        )
    )

    if video_id:
        query = query.where(Tip.video_id == video_id)

    # Count total and sum
    count_query = select(func.count(), func.sum(Tip.amount)).select_from(query.subquery())
    result = await db.execute(count_query)
    row = result.first()
    total = row[0] or 0
    total_amount = row[1] or Decimal("0")

    # Get tips
    offset = (page - 1) * per_page
    query = query.order_by(Tip.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    tips = result.scalars().all()

    return TipListResponse(
        tips=[TipResponse.model_validate(t) for t in tips],
        total=total,
        total_amount=total_amount,
        page=page,
        per_page=per_page,
        has_more=(offset + len(tips)) < total,
    )


# Webhook handler for payment confirmations
@router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    # In production, verify webhook signature
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Stripe webhook events."""
    # This would be implemented with proper webhook verification
    # For now, it's a placeholder

    # On payment_intent.succeeded:
    # 1. Find the TicketPurchase or Tip by payment_intent_id
    # 2. Update status to COMPLETED
    # 3. Create Transaction record
    # 4. Update creator's total_earnings and tier

    return {"received": True}
