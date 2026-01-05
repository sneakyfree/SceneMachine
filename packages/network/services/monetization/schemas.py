"""
Pydantic schemas for monetization service requests and responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from ...shared.models import TransactionType, TransactionStatus, PayoutStatus


# Transaction schemas
class TransactionResponse(BaseModel):
    """Response for a transaction."""

    id: uuid.UUID
    creator_id: uuid.UUID
    video_id: Optional[uuid.UUID]
    transaction_type: TransactionType
    status: TransactionStatus
    amount_gross: Decimal
    platform_fee: Decimal
    processing_fee: Decimal
    amount_net: Decimal
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Response for transaction list."""

    transactions: list[TransactionResponse]
    total: int
    total_earnings: Decimal
    page: int
    per_page: int
    has_more: bool


# Earnings schemas
class EarningsSummaryResponse(BaseModel):
    """Summary of creator earnings."""

    creator_id: uuid.UUID
    current_tier: int
    platform_cut_percent: float
    creator_cut_percent: float

    # Totals
    total_earnings_all_time: Decimal
    total_earnings_this_month: Decimal
    total_earnings_last_month: Decimal

    # By type this month
    ad_revenue_this_month: Decimal
    ticket_revenue_this_month: Decimal
    tip_revenue_this_month: Decimal

    # Pending payout
    available_for_payout: Decimal
    pending_payout: Decimal

    # Period
    period_start: datetime
    period_end: datetime


class EarningsBreakdownResponse(BaseModel):
    """Detailed earnings breakdown."""

    period: str  # "day", "week", "month"
    ad_revenue: Decimal
    ticket_revenue: Decimal
    tip_revenue: Decimal
    total_gross: Decimal
    platform_fees: Decimal
    processing_fees: Decimal
    total_net: Decimal
    video_count: int
    view_count: int


# Cost tracking schemas
class CostBreakdownResponse(BaseModel):
    """Cost breakdown for a video."""

    video_id: uuid.UUID
    month: str
    storage_gb: float
    storage_cost: Decimal
    bandwidth_gb: float
    bandwidth_cost: Decimal
    processing_cost: Decimal
    total_cost: Decimal
    revenue: Decimal
    net_profit: Decimal
    is_profitable: bool


class CreatorCostSummaryResponse(BaseModel):
    """Summary of creator's costs."""

    creator_id: uuid.UUID
    month: str
    total_storage_gb: float
    total_storage_cost: Decimal
    total_bandwidth_gb: float
    total_bandwidth_cost: Decimal
    total_processing_cost: Decimal
    total_cost: Decimal
    total_revenue: Decimal
    net_profit: Decimal
    video_count: int
    unprofitable_videos: int


# Payout schemas
class PayoutRequestRequest(BaseModel):
    """Request to create a payout."""

    amount: Optional[Decimal] = Field(None, ge=Decimal("25.00"))  # Minimum $25


class PayoutResponse(BaseModel):
    """Response for a payout."""

    id: uuid.UUID
    creator_id: uuid.UUID
    amount: Decimal
    status: PayoutStatus
    stripe_transfer_id: Optional[str]
    requested_at: datetime
    processed_at: Optional[datetime]
    failure_reason: Optional[str]
    period_start: datetime
    period_end: datetime

    class Config:
        from_attributes = True


class PayoutListResponse(BaseModel):
    """Response for payout list."""

    payouts: list[PayoutResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


# Ticket purchase schemas
class TicketPurchaseRequest(BaseModel):
    """Request to purchase a ticket."""

    video_id: uuid.UUID


class TicketPurchaseResponse(BaseModel):
    """Response for ticket purchase."""

    id: uuid.UUID
    video_id: uuid.UUID
    amount: Decimal
    currency: str
    status: TransactionStatus
    access_granted_at: Optional[datetime]
    access_expires_at: Optional[datetime]
    stripe_client_secret: Optional[str]  # For frontend Stripe.js

    class Config:
        from_attributes = True


class UserTicketsResponse(BaseModel):
    """Response for user's purchased tickets."""

    tickets: list[TicketPurchaseResponse]
    total: int


# Tip schemas
class TipRequest(BaseModel):
    """Request to send a tip."""

    creator_id: uuid.UUID
    video_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(..., ge=Decimal("1.00"), le=Decimal("500.00"))
    message: Optional[str] = Field(None, max_length=500)
    is_public: bool = True


class TipResponse(BaseModel):
    """Response for a tip."""

    id: uuid.UUID
    creator_id: uuid.UUID
    video_id: Optional[uuid.UUID]
    amount: Decimal
    message: Optional[str]
    is_public: bool
    status: TransactionStatus
    created_at: datetime
    stripe_client_secret: Optional[str]

    class Config:
        from_attributes = True


class TipListResponse(BaseModel):
    """Response for tip list (received by creator)."""

    tips: list[TipResponse]
    total: int
    total_amount: Decimal
    page: int
    per_page: int
    has_more: bool


# Stripe Connect schemas
class StripeConnectStatusResponse(BaseModel):
    """Status of Stripe Connect onboarding."""

    is_connected: bool
    account_id: Optional[str]
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool
    onboarding_url: Optional[str]  # If not complete


class StripeConnectOnboardingRequest(BaseModel):
    """Request to start Stripe Connect onboarding."""

    return_url: str
    refresh_url: str
