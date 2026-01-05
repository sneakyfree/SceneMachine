"""
PerformerRating Model

Represents ratings and reviews given to performers after
completing bookings.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin


if TYPE_CHECKING:
    from scenemachine.models.performer import Performer
    from scenemachine.models.booking import Booking


class PerformerRating(Base, UUIDMixin, TimestampMixin):
    """
    A rating given to a performer after completing a booking.

    Ratings contribute to the performer's ACI (ActCast Index) score.

    Attributes:
        booking_id: Foreign key to booking (unique)
        performer_id: Foreign key to performer
        rater_user_id: User who gave the rating
        overall_score: Overall rating (1.0-5.0)
        motion_quality_score: Motion quality rating
        emotion_accuracy_score: Emotion accuracy rating
        professionalism_score: Professionalism rating
        timeliness_score: Delivery timeliness rating
        would_rehire: Boolean for ACI rehire rate
        review_text: Optional text review
        audience_buzz_votes: Community votes for buzz score
    """

    __tablename__ = "performer_ratings"

    # Foreign keys
    booking_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One rating per booking
    )
    performer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("performers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rater_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Overall rating
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    # 1.0 - 5.0 scale (half stars allowed)

    # Detailed scores (all 1.0-5.0)
    motion_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Quality of motion capture data

    emotion_accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # How accurately emotions were portrayed

    professionalism_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Communication, responsiveness, behavior

    timeliness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Delivery within expected timeframe

    # Rehire indicator (important for ACI)
    would_rehire: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # This is weighted heavily in ACI calculation

    # Written review
    review_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Visibility
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Public reviews are shown on performer profile

    # Audience engagement (for ACI buzz score)
    audience_buzz_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Community members can upvote public reviews
    # This contributes to the "Audience Buzz" component of ACI

    helpful_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Votes for "was this review helpful"

    # Moderation
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Verified = from actual completed booking

    # Performer response
    performer_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    rated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    performer: Mapped["Performer"] = relationship(
        "Performer",
        back_populates="ratings",
    )
    booking: Mapped["Booking"] = relationship(
        "Booking",
        back_populates="rating",
    )

    @property
    def average_detailed_score(self) -> Optional[float]:
        """Calculate average of detailed scores."""
        scores = [
            s for s in [
                self.motion_quality_score,
                self.emotion_accuracy_score,
                self.professionalism_score,
                self.timeliness_score,
            ] if s is not None
        ]
        if scores:
            return sum(scores) / len(scores)
        return None

    @property
    def has_detailed_scores(self) -> bool:
        """Check if rating has detailed scores."""
        return any([
            self.motion_quality_score is not None,
            self.emotion_accuracy_score is not None,
            self.professionalism_score is not None,
            self.timeliness_score is not None,
        ])

    @property
    def engagement_score(self) -> float:
        """Calculate engagement score for buzz calculation."""
        # Weight helpful votes more than buzz votes
        return (self.audience_buzz_votes * 1.0) + (self.helpful_votes * 0.5)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<PerformerRating(id={self.id}, "
            f"performer_id={self.performer_id}, "
            f"score={self.overall_score:.1f}, "
            f"rehire={self.would_rehire})>"
        )
