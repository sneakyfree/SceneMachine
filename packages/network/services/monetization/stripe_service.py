"""
Stripe integration for monetization.
"""

from decimal import Decimal
from typing import Optional

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from ...shared.config import settings

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Service for Stripe operations."""

    @staticmethod
    async def create_connect_account(user_email: str, user_id: str) -> dict:
        """Create a Stripe Connect account for a creator."""
        account = stripe.Account.create(
            type="express",
            email=user_email,
            metadata={"user_id": user_id},
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )
        return {"account_id": account.id}

    @staticmethod
    async def create_account_link(
        account_id: str,
        return_url: str,
        refresh_url: str,
    ) -> str:
        """Create an account link for Connect onboarding."""
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return account_link.url

    @staticmethod
    async def get_account_status(account_id: str) -> dict:
        """Get Stripe Connect account status."""
        account = stripe.Account.retrieve(account_id)
        return {
            "account_id": account.id,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
            "details_submitted": account.details_submitted,
        }

    @staticmethod
    async def create_payment_intent(
        amount_cents: int,
        currency: str = "usd",
        metadata: Optional[dict] = None,
        connected_account_id: Optional[str] = None,
        application_fee_cents: Optional[int] = None,
    ) -> dict:
        """Create a payment intent for a purchase."""
        params = {
            "amount": amount_cents,
            "currency": currency,
            "metadata": metadata or {},
            "automatic_payment_methods": {"enabled": True},
        }

        # If paying to a connected account (creator)
        if connected_account_id and application_fee_cents:
            params["transfer_data"] = {"destination": connected_account_id}
            params["application_fee_amount"] = application_fee_cents

        payment_intent = stripe.PaymentIntent.create(**params)
        return {
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
        }

    @staticmethod
    async def confirm_payment_intent(payment_intent_id: str) -> dict:
        """Get the status of a payment intent."""
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            "id": payment_intent.id,
            "status": payment_intent.status,
            "amount": payment_intent.amount,
            "amount_received": payment_intent.amount_received,
        }

    @staticmethod
    async def create_transfer(
        amount_cents: int,
        destination_account_id: str,
        transfer_group: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a transfer to a connected account."""
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency="usd",
            destination=destination_account_id,
            transfer_group=transfer_group,
            metadata=metadata or {},
        )
        return {
            "transfer_id": transfer.id,
            "amount": transfer.amount,
        }

    @staticmethod
    async def create_payout(
        amount_cents: int,
        connected_account_id: str,
    ) -> dict:
        """Create a payout from a connected account to their bank."""
        payout = stripe.Payout.create(
            amount=amount_cents,
            currency="usd",
            stripe_account=connected_account_id,
        )
        return {
            "payout_id": payout.id,
            "status": payout.status,
        }

    @staticmethod
    async def refund_payment(payment_intent_id: str, amount_cents: Optional[int] = None) -> dict:
        """Refund a payment (full or partial)."""
        params = {"payment_intent": payment_intent_id}
        if amount_cents:
            params["amount"] = amount_cents

        refund = stripe.Refund.create(**params)
        return {
            "refund_id": refund.id,
            "status": refund.status,
            "amount": refund.amount,
        }

    @staticmethod
    async def get_balance(connected_account_id: Optional[str] = None) -> dict:
        """Get Stripe balance."""
        if connected_account_id:
            balance = stripe.Balance.retrieve(stripe_account=connected_account_id)
        else:
            balance = stripe.Balance.retrieve()

        # Extract available and pending amounts
        available = sum(b.amount for b in balance.available) / 100 if balance.available else 0
        pending = sum(b.amount for b in balance.pending) / 100 if balance.pending else 0

        return {
            "available": Decimal(str(available)),
            "pending": Decimal(str(pending)),
        }


# Singleton instance
stripe_service = StripeService()
