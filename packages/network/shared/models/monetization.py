"""
Monetization models for SceneMachine Network.

Includes Transaction, Payout, AdImpression, TicketPurchase, Tip.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user import User
    from .video import Video


class TransactionType(str, enum.Enum):
    """Types of revenue transactions."""

    AD_REVENUE = "ad_revenue"
    TICKET_SALE = "ticket_sale"
    TIP = "tip"
    SUBSCRIPTION = "subscription"


class TransactionStatus(str, enum.Enum):
    """Transaction processing status."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PayoutStatus(str, enum.Enum):
    """Payout processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transaction(Base, UUIDMixin, TimestampMixin):
    """
    Revenue transaction record.
    """

    __tablename__ = "transactions"

    # References
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # For anonymous tips or ad revenue
    )

    # Transaction type
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        nullable=False,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
    )

    # Amounts
    amount_gross: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    processing_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    amount_net: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Description
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # External reference
    stripe_payment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_transactions_creator_date", "creator_id", "created_at"),
        Index("ix_transactions_type_date", "transaction_type", "created_at"),
        Index("ix_transactions_video", "video_id"),
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id} {self.transaction_type.value} ${self.amount_net}>"


class Payout(Base, UUIDMixin, TimestampMixin):
    """
    Payout to creator.
    """

    __tablename__ = "payouts"

    # Creator
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Status
    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus),
        default=PayoutStatus.PENDING,
        nullable=False,
    )

    # Stripe transfer
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    stripe_payout_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Processing timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Failure info
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Period covered
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_payouts_creator_status", "creator_id", "status"),
        Index("ix_payouts_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Payout {self.id} ${self.amount} {self.status.value}>"


class AdImpression(Base, UUIDMixin, TimestampMixin):
    """
    Ad impression record for revenue tracking.
    """

    __tablename__ = "ad_impressions"

    # References
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watch_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    viewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Ad details
    ad_type: Mapped[str] = mapped_column(
        String(50),  # pre_roll, mid_roll, post_roll, banner
        nullable=False,
    )
    ad_provider: Mapped[str] = mapped_column(
        String(50),  # google_ads, direct, etc.
        nullable=False,
    )
    ad_campaign_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Revenue
    cpm_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),  # $ per 1000 impressions
        nullable=False,
    )
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),  # Micro-amount for this impression
        nullable=False,
    )

    # Engagement
    was_skipped: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    watch_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Geographic
    country_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_ad_impressions_video_date", "video_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AdImpression {self.ad_type} video={self.video_id}>"


class TicketPurchase(Base, UUIDMixin, TimestampMixin):
    """
    Ticket purchase for paid content.
    """

    __tablename__ = "ticket_purchases"

    # References
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Purchase details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )

    # Stripe
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Status
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
    )

    # Access
    access_granted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    access_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # None = permanent access
    )

    # Refund
    is_refunded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Unique constraint: one purchase per user per video
    __table_args__ = (
        Index("ix_ticket_purchases_buyer_video", "buyer_id", "video_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<TicketPurchase ${self.amount} video={self.video_id}>"


class Tip(Base, UUIDMixin, TimestampMixin):
    """
    Tip from viewer to creator.
    """

    __tablename__ = "tips"

    # References
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Anonymous tips allowed
    )
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,  # Can tip on channel, not just video
    )

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )

    # Message
    message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Stripe
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Status
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_tips_creator_date", "creator_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Tip ${self.amount} to creator={self.creator_id}>"


# Revenue tier thresholds and platform cuts
REVENUE_TIERS = [
    (Decimal("0"), Decimal("1000"), Decimal("0.50")),  # 50% cut
    (Decimal("1000.01"), Decimal("10000"), Decimal("0.40")),  # 40% cut
    (Decimal("10000.01"), Decimal("100000"), Decimal("0.30")),  # 30% cut
    (Decimal("100000.01"), Decimal("1000000"), Decimal("0.20")),  # 20% cut
    (Decimal("1000000.01"), Decimal("10000000"), Decimal("0.10")),  # 10% cut
    (Decimal("10000000.01"), Decimal("999999999"), Decimal("0.01")),  # 1% cut
]


def calculate_platform_fee(gross_amount: Decimal, creator_total_earnings: Decimal) -> Decimal:
    """
    Calculate platform fee based on creator's revenue tier.

    Returns the platform fee amount (not the creator's share).
    """
    for tier_min, tier_max, platform_cut in REVENUE_TIERS:
        if tier_min <= creator_total_earnings <= tier_max:
            return gross_amount * platform_cut

    # Default to highest tier if somehow exceeds
    return gross_amount * Decimal("0.01")
