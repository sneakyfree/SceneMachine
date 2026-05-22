"""
Performer Model

Represents ActCore performers (human or synthetic) who provide
motion/emotion data for performance-driven video generation.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import ArrayType, Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from scenemachine.models.booking import Booking
    from scenemachine.models.performance_take import PerformanceTake
    from scenemachine.models.performer_rating import PerformerRating


class PerformerType(StrEnum):
    """Type of performer."""
    HUMAN = "human"  # Human glove actor with motion capture
    SYNTHETIC = "synthetic"  # AI-generated synthetic performer


class PerformerAvailability(StrEnum):
    """Performer availability status."""
    AVAILABLE = "available"  # Ready for bookings
    BUSY = "busy"  # Currently fulfilling a booking
    OFFLINE = "offline"  # Not accepting bookings
    ON_LEAVE = "on_leave"  # Temporarily unavailable


class PerformerVerification(StrEnum):
    """Performer verification status."""
    UNVERIFIED = "unverified"  # Not yet verified
    PENDING = "pending"  # Verification in progress
    VERIFIED = "verified"  # Identity verified
    ELITE = "elite"  # Elite verified performer


class Performer(Base, UUIDMixin, TimestampMixin):
    """
    An ActCore performer who provides motion/emotion data.

    Performers can be human actors using motion capture gloves or
    synthetic AI performers. They provide raw motion data that gets
    retargeted onto AI-generated characters.

    Attributes:
        stage_name: Public display name
        legal_name: Legal name (encrypted at rest)
        performer_type: Human or synthetic
        profile_image_path: Path to profile image
        bio: Biography text
        specialties: List of motion specialties (dramatic, comedic, action)
        availability_status: Current availability
        verification_status: Identity verification level
        aci_score: ActCast Index score (0-100)
        total_bookings: Number of completed bookings
        total_earnings_usd: Total earnings in USD
        lifetime_earnings_usd: Lifetime earnings for tier calculation
        revenue_split_percent: Current revenue split percentage
        motion_capabilities: JSON with supported motion features
    """

    __tablename__ = "performers"

    # Identity
    stage_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Type and status
    performer_type: Mapped[PerformerType] = mapped_column(
        SAEnum(PerformerType, name="performer_type"),
        default=PerformerType.HUMAN,
        nullable=False,
    )
    availability_status: Mapped[PerformerAvailability] = mapped_column(
        SAEnum(PerformerAvailability, name="performer_availability"),
        default=PerformerAvailability.OFFLINE,
        nullable=False,
        index=True,
    )
    verification_status: Mapped[PerformerVerification] = mapped_column(
        SAEnum(PerformerVerification, name="performer_verification"),
        default=PerformerVerification.UNVERIFIED,
        nullable=False,
    )

    # Profile
    profile_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    specialties: Mapped[list | None] = mapped_column(ArrayType(String), nullable=True)
    # Example specialties: ["dramatic", "comedic", "action", "romantic", "horror"]

    # Rating and performance
    aci_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False, index=True)
    # ACI = (Placement Rate x 0.4) + (Rehire Rate x 0.3) + (Audience Buzz x 0.2) + (MotionScore x 0.1)

    # Statistics
    total_bookings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_bookings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earnings_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    lifetime_earnings_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Revenue split (starts at 50%, increases with lifetime earnings)
    revenue_split_percent: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    # Tiers:
    # $0-$999: 50%
    # $1k-$9,999: 60%
    # $10k-$99,999: 70%
    # $100k-$999,999: 80%
    # $1M-$9.99M: 90%
    # $10M+: 99%

    # Motion capabilities
    motion_capabilities: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "supports_liveportrait": true,
    #     "supports_roop_gs_anim": true,
    #     "supported_resolutions": ["480p", "720p", "1080p"],
    #     "max_take_duration_seconds": 1200,
    #     "face_tracking_quality": "high",
    #     "body_tracking": false,
    #     "hand_tracking": true
    # }

    # Pricing (USD per mode)
    pricing: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "blink": 5.0,
    #     "deep": 25.0,
    #     "epic_per_minute": 10.0,
    #     "auction_minimum": 50.0
    # }

    # Banking and legal (encrypted at rest)
    banking_info: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    consent_documents: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    # Activity
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    takes: Mapped[list["PerformanceTake"]] = relationship(
        "PerformanceTake",
        back_populates="performer",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="performer",
        foreign_keys="Booking.performer_id",
    )
    ratings: Mapped[list["PerformerRating"]] = relationship(
        "PerformerRating",
        back_populates="performer",
        cascade="all, delete-orphan",
    )

    @property
    def placement_rate(self) -> float:
        """Calculate placement rate for ACI."""
        if self.total_bookings == 0:
            return 50.0  # Default for new performers
        return (self.completed_bookings / self.total_bookings) * 100

    @property
    def average_rating(self) -> float | None:
        """Calculate average rating from reviews."""
        if not self.ratings:
            return None
        return sum(r.overall_score for r in self.ratings) / len(self.ratings)

    @property
    def is_available(self) -> bool:
        """Check if performer is available for booking."""
        return (
            self.is_active
            and self.availability_status == PerformerAvailability.AVAILABLE
        )

    def get_price_for_mode(self, mode: str) -> float | None:
        """Get pricing for a specific booking mode."""
        if not self.pricing:
            return None
        return self.pricing.get(mode.lower())

    def update_revenue_tier(self) -> None:
        """Update revenue split based on lifetime earnings."""
        earnings = self.lifetime_earnings_usd
        if earnings >= 10_000_000:
            self.revenue_split_percent = 99.0
        elif earnings >= 1_000_000:
            self.revenue_split_percent = 90.0
        elif earnings >= 100_000:
            self.revenue_split_percent = 80.0
        elif earnings >= 10_000:
            self.revenue_split_percent = 70.0
        elif earnings >= 1_000:
            self.revenue_split_percent = 60.0
        else:
            self.revenue_split_percent = 50.0

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Performer(id={self.id}, "
            f"stage_name={self.stage_name}, "
            f"type={self.performer_type.value}, "
            f"aci={self.aci_score:.1f})>"
        )
