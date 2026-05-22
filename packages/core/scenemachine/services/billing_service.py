"""
Billing Service

Stripe integration for subscriptions and payments.
"""

import logging
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.user import User

logger = logging.getLogger(__name__)


class SubscriptionTier(StrEnum):
    """Available subscription tiers."""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class PlanConfig:
    """Stripe plan configuration."""
    PLANS = {
        SubscriptionTier.FREE: {
            "name": "Free",
            "price_monthly": 0,
            "price_yearly": 0,
            "stripe_price_monthly": None,
            "stripe_price_yearly": None,
            "features": [
                "5 projects",
                "720p export",
                "Community support",
                "Basic AI features",
            ],
            "limits": {
                "projects": 5,
                "exports_per_month": 10,
                "max_export_resolution": "1280x720",
                "ai_generations_per_day": 10,
            },
        },
        SubscriptionTier.PRO: {
            "name": "Pro",
            "price_monthly": 2900,  # $29.00
            "price_yearly": 29000,  # $290.00 (2 months free)
            "stripe_price_monthly": "price_pro_monthly",
            "stripe_price_yearly": "price_pro_yearly",
            "features": [
                "Unlimited projects",
                "4K export",
                "Priority support",
                "Full AI suite",
                "Cloud storage 100GB",
            ],
            "limits": {
                "projects": -1,  # Unlimited
                "exports_per_month": -1,
                "max_export_resolution": "3840x2160",
                "ai_generations_per_day": 100,
                "storage_gb": 100,
            },
        },
        SubscriptionTier.TEAM: {
            "name": "Team",
            "price_monthly": 9900,  # $99.00
            "price_yearly": 99000,  # $990.00 (2 months free)
            "stripe_price_monthly": "price_team_monthly",
            "stripe_price_yearly": "price_team_yearly",
            "features": [
                "Everything in Pro",
                "8K export",
                "Dedicated support",
                "Team collaboration",
                "Cloud storage 1TB",
                "Custom branding",
            ],
            "limits": {
                "projects": -1,
                "exports_per_month": -1,
                "max_export_resolution": "7680x4320",
                "ai_generations_per_day": -1,
                "storage_gb": 1000,
                "team_members": 10,
            },
        },
    }


class BillingServiceError(Exception):
    """Base exception for billing service."""
    def __init__(self, message: str, code: str = "billing_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class BillingService:
    """Service for Stripe billing and subscriptions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self._stripe = None

    def _get_stripe(self):
        """Get or initialize Stripe client."""
        if self._stripe is None:
            try:
                import stripe
                stripe.api_key = self.settings.stripe_secret_key
                self._stripe = stripe
            except ImportError:
                raise BillingServiceError(
                    "Stripe library not installed",
                    code="stripe_not_installed"
                )
        return self._stripe

    async def create_checkout_session(
        self,
        user_id: UUID,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        """Create Stripe checkout session for subscription.

        Args:
            user_id: User UUID
            price_id: Stripe price ID
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel

        Returns:
            Checkout session details including URL
        """
        stripe = self._get_stripe()

        # Get user
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise BillingServiceError("User not found", code="user_not_found")

        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email=user.email,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"user_id": str(user_id)},
                subscription_data={
                    "metadata": {"user_id": str(user_id)},
                },
            )

            return {
                "session_id": checkout_session.id,
                "url": checkout_session.url,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout: {e}")
            raise BillingServiceError(str(e), code="stripe_error")

    async def create_portal_session(
        self,
        user_id: UUID,
        return_url: str,
    ) -> dict:
        """Create Stripe customer portal session.

        Args:
            user_id: User UUID
            return_url: URL to return to after portal

        Returns:
            Portal session URL
        """
        stripe = self._get_stripe()

        # Get user's customer ID (would be stored in user model)
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise BillingServiceError("User not found", code="user_not_found")

        # TODO: Store stripe_customer_id on user model
        # For now, search by email
        try:
            customers = stripe.Customer.list(email=user.email, limit=1)
            if not customers.data:
                raise BillingServiceError(
                    "No billing profile found",
                    code="no_customer"
                )

            portal_session = stripe.billing_portal.Session.create(
                customer=customers.data[0].id,
                return_url=return_url,
            )

            return {"url": portal_session.url}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal: {e}")
            raise BillingServiceError(str(e), code="stripe_error")

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """Handle Stripe webhook events.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            Processing result
        """
        stripe = self._get_stripe()

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.settings.stripe_webhook_secret,
            )
        except stripe.error.SignatureVerificationError:
            raise BillingServiceError(
                "Invalid webhook signature",
                code="invalid_signature"
            )

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Processing Stripe webhook: {event_type}")

        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(data)

        return {"received": True, "event_type": event_type}

    async def _handle_checkout_completed(self, data: dict) -> None:
        """Handle successful checkout."""
        user_id = data.get("metadata", {}).get("user_id")
        if not user_id:
            logger.warning("Checkout completed without user_id metadata")
            return

        subscription_id = data.get("subscription")
        data.get("customer")

        logger.info(
            f"Checkout completed for user {user_id}, "
            f"subscription {subscription_id}"
        )

        # TODO: Update user's subscription status in database

    async def _handle_subscription_updated(self, data: dict) -> None:
        """Handle subscription update."""
        user_id = data.get("metadata", {}).get("user_id")
        status = data.get("status")
        data.get("current_period_end")

        logger.info(
            f"Subscription updated for user {user_id}: {status}"
        )

        # TODO: Update user's subscription status in database

    async def _handle_subscription_deleted(self, data: dict) -> None:
        """Handle subscription cancellation."""
        user_id = data.get("metadata", {}).get("user_id")

        logger.info(f"Subscription deleted for user {user_id}")

        # TODO: Downgrade user to free tier

    async def _handle_invoice_paid(self, data: dict) -> None:
        """Handle successful invoice payment."""
        subscription_id = data.get("subscription")
        amount_paid = data.get("amount_paid")

        logger.info(
            f"Invoice paid for subscription {subscription_id}: "
            f"${amount_paid / 100:.2f}"
        )

    async def _handle_payment_failed(self, data: dict) -> None:
        """Handle failed payment."""
        subscription_id = data.get("subscription")

        logger.warning(f"Payment failed for subscription {subscription_id}")

        # TODO: Send notification to user, potentially downgrade

    async def get_subscription_status(self, user_id: UUID) -> dict:
        """Get user's current subscription status.

        Args:
            user_id: User UUID

        Returns:
            Subscription details
        """
        # TODO: Fetch from database once user model extended
        # For now return free tier
        return {
            "tier": SubscriptionTier.FREE.value,
            "status": "active",
            "features": PlanConfig.PLANS[SubscriptionTier.FREE]["features"],
            "limits": PlanConfig.PLANS[SubscriptionTier.FREE]["limits"],
            "current_period_end": None,
            "cancel_at_period_end": False,
        }

    def get_plans(self) -> list:
        """Get all available plans."""
        return [
            {
                "tier": tier.value,
                **config,
            }
            for tier, config in PlanConfig.PLANS.items()
        ]
