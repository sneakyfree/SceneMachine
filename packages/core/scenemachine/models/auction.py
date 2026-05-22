"""
Auction Model

Represents auctions in the ActForge marketplace where
directors bid on top-tier talent.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import ArrayType, Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from scenemachine.models.performer import Performer


class AuctionStatus(StrEnum):
    """Auction lifecycle status."""

    DRAFT = "draft"  # Being created
    SCHEDULED = "scheduled"  # Scheduled to open
    OPEN = "open"  # Accepting bids
    CLOSED = "closed"  # Bidding closed, selecting winner
    AWARDED = "awarded"  # Winner selected
    CANCELLED = "cancelled"  # Auction cancelled


class BidStatus(StrEnum):
    """Auction bid status."""

    ACTIVE = "active"  # Currently active bid
    OUTBID = "outbid"  # Outbid by another
    WITHDRAWN = "withdrawn"  # Withdrawn by bidder
    ACCEPTED = "accepted"  # Winning bid
    REJECTED = "rejected"  # Not selected


class Auction(Base, UUIDMixin, TimestampMixin):
    """
    An auction for booking top-tier ActCore talent.

    Auctions allow directors to bid on elite performers
    for premium projects.

    Attributes:
        project_id: Foreign key to project
        shot_id: Optional foreign key to shot
        creator_user_id: User who created the auction
        status: Current auction status
        requirements: JSON with detailed requirements
        min_bid_usd: Minimum bid amount
        max_bid_usd: Maximum budget (optional)
        duration_hours: How long auction runs
    """

    __tablename__ = "auctions"

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Auction details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[AuctionStatus] = mapped_column(
        SAEnum(AuctionStatus, name="auction_status"),
        default=AuctionStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Requirements
    requirements: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "duration_seconds": 60,
    #     "emotions": ["grief", "anger"],
    #     "intensity": "high",
    #     "style": "method",
    #     "reference_urls": ["..."],
    #     "scene_description": "...",
    #     "character_context": "..."
    # }

    # Qualification requirements
    min_aci_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    required_specialties: Mapped[list | None] = mapped_column(ArrayType(String), nullable=True)
    performer_type_required: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Bidding parameters
    min_bid_usd: Mapped[float] = mapped_column(Float, nullable=False)
    max_bid_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    reserve_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Reserve price: auction only completes if this price is met

    # Timing
    duration_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Winner
    winning_bid_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auction_bids.id", ondelete="SET NULL"),
        nullable=True,
    )
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Statistics
    total_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_bidders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    highest_bid_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    bids: Mapped[list["AuctionBid"]] = relationship(
        "AuctionBid",
        back_populates="auction",
        cascade="all, delete-orphan",
        foreign_keys="AuctionBid.auction_id",
    )
    winning_bid: Mapped[Optional["AuctionBid"]] = relationship(
        "AuctionBid",
        foreign_keys=[winning_bid_id],
        post_update=True,
    )

    @property
    def is_open(self) -> bool:
        """Check if auction is open for bidding."""
        return self.status == AuctionStatus.OPEN

    @property
    def time_remaining_seconds(self) -> float | None:
        """Calculate time remaining until close."""
        if self.closes_at:
            now = datetime.now(UTC)
            if self.closes_at > now:
                delta = self.closes_at - now
                return delta.total_seconds()
        return None

    @property
    def reserve_met(self) -> bool:
        """Check if reserve price has been met."""
        if not self.reserve_price_usd:
            return True
        if self.highest_bid_usd:
            return self.highest_bid_usd >= self.reserve_price_usd
        return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Auction(id={self.id}, "
            f"title={self.title}, "
            f"status={self.status.value}, "
            f"bids={self.total_bids})>"
        )


class AuctionBid(Base, UUIDMixin, TimestampMixin):
    """
    A bid placed on an auction.

    Attributes:
        auction_id: Foreign key to auction
        performer_id: Foreign key to bidding performer
        bid_amount_usd: Bid amount in USD
        proposed_delivery_hours: Proposed delivery time
        pitch_message: Message to the director
        sample_take_id: Optional sample take
        status: Current bid status
    """

    __tablename__ = "auction_bids"

    # Foreign keys
    auction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    performer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("performers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_take_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("performance_takes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Bid details
    bid_amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    proposed_delivery_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    # Pitch
    pitch_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Performers can pitch why they're right for the role

    # Status
    status: Mapped[BidStatus] = mapped_column(
        SAEnum(BidStatus, name="bid_status"),
        default=BidStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Timing
    bid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Auto-bid settings (optional)
    auto_bid_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_bid_max_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_bid_increment_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    auction: Mapped["Auction"] = relationship(
        "Auction",
        back_populates="bids",
        foreign_keys=[auction_id],
    )
    performer: Mapped["Performer"] = relationship("Performer")

    @property
    def is_active(self) -> bool:
        """Check if bid is currently active."""
        return self.status == BidStatus.ACTIVE

    @property
    def is_winning(self) -> bool:
        """Check if this is currently the winning bid."""
        return self.status == BidStatus.ACCEPTED

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AuctionBid(id={self.id}, "
            f"auction_id={self.auction_id}, "
            f"amount=${self.bid_amount_usd:.2f}, "
            f"status={self.status.value})>"
        )
