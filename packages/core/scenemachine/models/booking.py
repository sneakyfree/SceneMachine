"""
Booking Model

Represents talent bookings in the ActForge marketplace.
Tracks the full lifecycle from request to completion.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin, JSONType, ArrayType


if TYPE_CHECKING:
    from scenemachine.models.performer import Performer
    from scenemachine.models.performance_take import PerformanceTake
    from scenemachine.models.performer_rating import PerformerRating


class BookingMode(str, Enum):
    """Types of bookings in ActForge."""
    BLINK = "blink"  # 10-second auto-match
    DEEP = "deep"  # 120-second method acting
    EPIC = "epic"  # 5-20 minute continuous
    AUCTION = "auction"  # Bidding on top-tier talent


class BookingStatus(str, Enum):
    """Booking lifecycle status."""
    REQUESTED = "requested"  # Initial request created
    MATCHING = "matching"  # Auto-matching in progress (Blink mode)
    MATCHED = "matched"  # Performer matched (Blink) or selected
    ACCEPTED = "accepted"  # Performer accepted the booking
    IN_PROGRESS = "in_progress"  # Performer is recording
    DELIVERED = "delivered"  # Take delivered, awaiting approval
    APPROVED = "approved"  # Director approved the take
    DISPUTED = "disputed"  # Director disputed the delivery
    COMPLETED = "completed"  # Booking finalized, payment released
    CANCELLED = "cancelled"  # Booking cancelled
    EXPIRED = "expired"  # Booking expired without completion


class PaymentStatus(str, Enum):
    """Payment status for booking."""
    PENDING = "pending"  # Awaiting payment
    ESCROWED = "escrowed"  # Payment held in escrow
    RELEASED = "released"  # Payment released to performer
    REFUNDED = "refunded"  # Payment refunded to director
    FAILED = "failed"  # Payment failed


class Booking(Base, UUIDMixin, TimestampMixin):
    """
    A talent booking in the ActForge marketplace.

    Bookings track the full lifecycle of hiring a performer,
    from initial request through delivery and payment.

    State Machine:
        REQUESTED -> MATCHING -> MATCHED -> ACCEPTED -> IN_PROGRESS
        -> DELIVERED -> APPROVED -> COMPLETED

        Alternative paths:
        - DELIVERED -> DISPUTED -> (resolution) -> COMPLETED/CANCELLED
        - Any state -> CANCELLED
        - REQUESTED/MATCHED -> EXPIRED (if not acted upon)

    Attributes:
        project_id: Foreign key to project
        shot_id: Optional foreign key to shot
        performer_id: Foreign key to performer
        requester_user_id: User who made the booking
        booking_mode: Type of booking (blink, deep, epic, auction)
        status: Current booking status
        price_usd: Agreed price in USD
        payment_status: Current payment status
    """

    __tablename__ = "bookings"

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    performer_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("performers.id", ondelete="SET NULL"),
        nullable=True,  # Null during matching phase
        index=True,
    )
    requester_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Take reference (set on delivery)
    take_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("performance_takes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Booking type and status
    booking_mode: Mapped[BookingMode] = mapped_column(
        SAEnum(BookingMode, name="booking_mode"),
        nullable=False,
        index=True,
    )
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status"),
        default=BookingStatus.REQUESTED,
        nullable=False,
        index=True,
    )

    # Requirements
    duration_requested_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    duration_delivered_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    emotion_requirements: Mapped[Optional[list]] = mapped_column(ArrayType(String), nullable=True)
    # Example: ["grief", "subtle", "tearful"]

    motion_requirements: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "intensity": "high",
    #     "pace": "slow",
    #     "style": "naturalistic",
    #     "reference_urls": ["..."]
    # }

    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    character_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scene_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pricing
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    performer_payout_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Max price is used for Blink auto-matching

    # Payment
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    escrowed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Retry handling
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    retry_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timeline
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    matched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Dispute handling
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispute_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispute_resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disputed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notes
    director_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    performer: Mapped[Optional["Performer"]] = relationship(
        "Performer",
        back_populates="bookings",
        foreign_keys=[performer_id],
    )
    take: Mapped[Optional["PerformanceTake"]] = relationship(
        "PerformanceTake",
        back_populates="bookings",
        foreign_keys=[take_id],
    )
    rating: Mapped[Optional["PerformerRating"]] = relationship(
        "PerformerRating",
        back_populates="booking",
        uselist=False,
    )

    # Valid state transitions
    VALID_TRANSITIONS = {
        BookingStatus.REQUESTED: [
            BookingStatus.MATCHING,
            BookingStatus.MATCHED,
            BookingStatus.CANCELLED,
            BookingStatus.EXPIRED,
        ],
        BookingStatus.MATCHING: [
            BookingStatus.MATCHED,
            BookingStatus.CANCELLED,
            BookingStatus.EXPIRED,
        ],
        BookingStatus.MATCHED: [
            BookingStatus.ACCEPTED,
            BookingStatus.CANCELLED,
            BookingStatus.EXPIRED,
        ],
        BookingStatus.ACCEPTED: [
            BookingStatus.IN_PROGRESS,
            BookingStatus.CANCELLED,
        ],
        BookingStatus.IN_PROGRESS: [
            BookingStatus.DELIVERED,
            BookingStatus.CANCELLED,
        ],
        BookingStatus.DELIVERED: [
            BookingStatus.APPROVED,
            BookingStatus.DISPUTED,
        ],
        BookingStatus.APPROVED: [
            BookingStatus.COMPLETED,
        ],
        BookingStatus.DISPUTED: [
            BookingStatus.APPROVED,  # Resolved in favor of performer
            BookingStatus.CANCELLED,  # Resolved in favor of director
            BookingStatus.IN_PROGRESS,  # Retry granted
        ],
        BookingStatus.COMPLETED: [],  # Terminal state
        BookingStatus.CANCELLED: [],  # Terminal state
        BookingStatus.EXPIRED: [],  # Terminal state
    }

    @property
    def is_active(self) -> bool:
        """Check if booking is currently active."""
        return self.status not in (
            BookingStatus.COMPLETED,
            BookingStatus.CANCELLED,
            BookingStatus.EXPIRED,
        )

    @property
    def is_terminal(self) -> bool:
        """Check if booking is in a terminal state."""
        return self.status in (
            BookingStatus.COMPLETED,
            BookingStatus.CANCELLED,
            BookingStatus.EXPIRED,
        )

    @property
    def can_retry(self) -> bool:
        """Check if booking allows retry."""
        return (
            self.status == BookingStatus.DISPUTED
            and self.retry_count < self.max_retries
        )

    @property
    def turnaround_seconds(self) -> Optional[float]:
        """Calculate total turnaround time."""
        if self.requested_at and self.completed_at:
            delta = self.completed_at - self.requested_at
            return delta.total_seconds()
        return None

    def can_transition_to(self, new_status: BookingStatus) -> bool:
        """Check if transition to new status is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def calculate_payout(self, performer_split_percent: float) -> tuple[float, float]:
        """
        Calculate platform fee and performer payout.

        Returns:
            (platform_fee_usd, performer_payout_usd)
        """
        performer_payout = self.price_usd * (performer_split_percent / 100)
        platform_fee = self.price_usd - performer_payout
        return (platform_fee, performer_payout)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Booking(id={self.id}, "
            f"mode={self.booking_mode.value}, "
            f"status={self.status.value}, "
            f"price=${self.price_usd:.2f})>"
        )
