"""
Billing API Routes

REST endpoints for Stripe billing and subscriptions.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.dependencies import CurrentActiveUser
from scenemachine.database import get_session
from scenemachine.services.billing_service import (
    BillingService,
    BillingServiceError,
)

router = APIRouter(prefix="/billing", tags=["billing"])


# Schemas
class CheckoutRequest(BaseModel):
    """Request to create checkout session."""

    price_id: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Checkout session response."""

    session_id: str
    url: str


class PortalRequest(BaseModel):
    """Request to create portal session."""

    return_url: str


class PortalResponse(BaseModel):
    """Portal session response."""

    url: str


class SubscriptionResponse(BaseModel):
    """Subscription status response."""

    tier: str
    status: str
    features: list
    limits: dict
    current_period_end: str | None
    cancel_at_period_end: bool


class PlanResponse(BaseModel):
    """Plan details."""

    tier: str
    name: str
    price_monthly: int
    price_yearly: int
    features: list
    limits: dict


class PlansResponse(BaseModel):
    """All plans response."""

    plans: list[PlanResponse]


class WebhookResponse(BaseModel):
    """Webhook processing response."""

    received: bool
    event_type: str | None = None


# Dependencies
def get_billing_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingService:
    """Get billing service instance."""
    return BillingService(session)


# Routes
@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
)
async def create_checkout(
    data: CheckoutRequest,
    current_user: CurrentActiveUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> CheckoutResponse:
    """Create Stripe checkout session for subscription."""
    try:
        result = await service.create_checkout_session(
            user_id=current_user.id,
            price_id=data.price_id,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
        return CheckoutResponse(**result)
    except BillingServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Create customer portal session",
)
async def create_portal(
    data: PortalRequest,
    current_user: CurrentActiveUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> PortalResponse:
    """Create Stripe customer portal session for managing subscription."""
    try:
        result = await service.create_portal_session(
            user_id=current_user.id,
            return_url=data.return_url,
        )
        return PortalResponse(**result)
    except BillingServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get subscription status",
)
async def get_subscription(
    current_user: CurrentActiveUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> SubscriptionResponse:
    """Get current user's subscription status."""
    result = await service.get_subscription_status(current_user.id)
    return SubscriptionResponse(**result)


@router.get(
    "/plans",
    response_model=PlansResponse,
    summary="Get available plans",
)
async def get_plans(
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> PlansResponse:
    """Get all available subscription plans."""
    plans = service.get_plans()
    return PlansResponse(plans=plans)


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Stripe webhook handler",
)
async def webhook(
    request: Request,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> WebhookResponse:
    """Handle Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        result = await service.handle_webhook(payload, signature)
        return WebhookResponse(**result)
    except BillingServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
