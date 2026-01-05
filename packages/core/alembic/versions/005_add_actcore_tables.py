"""Add ActCore tables for performer marketplace.

Revision ID: 005_actcore
Revises: 004_integrity_constraints
Create Date: 2026-01-04

Tables created:
- performers: ActCore performers (human/synthetic)
- performance_takes: Recorded performance takes with motion data
- bookings: Talent booking management
- auctions: Auction system for top-tier talent
- auction_bids: Bids on auctions
- performer_ratings: Rating and review system
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_actcore"
down_revision: Union[str, None] = "004_integrity_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # ENUM TYPES
    # ==========================================================================

    # Performer type enum
    performer_type_enum = postgresql.ENUM(
        'human', 'synthetic',
        name='performer_type',
        create_type=True,
    )
    performer_type_enum.create(op.get_bind(), checkfirst=True)

    # Performer availability enum
    performer_availability_enum = postgresql.ENUM(
        'available', 'busy', 'offline', 'on_leave',
        name='performer_availability',
        create_type=True,
    )
    performer_availability_enum.create(op.get_bind(), checkfirst=True)

    # Performer verification enum
    performer_verification_enum = postgresql.ENUM(
        'unverified', 'pending', 'verified', 'elite',
        name='performer_verification',
        create_type=True,
    )
    performer_verification_enum.create(op.get_bind(), checkfirst=True)

    # Take mode enum
    take_mode_enum = postgresql.ENUM(
        'blink', 'deep', 'epic', 'demo',
        name='take_mode',
        create_type=True,
    )
    take_mode_enum.create(op.get_bind(), checkfirst=True)

    # Take status enum
    take_status_enum = postgresql.ENUM(
        'uploading', 'processing', 'available', 'archived', 'flagged', 'deleted',
        name='take_status',
        create_type=True,
    )
    take_status_enum.create(op.get_bind(), checkfirst=True)

    # Booking mode enum
    booking_mode_enum = postgresql.ENUM(
        'blink', 'deep', 'epic', 'auction',
        name='booking_mode',
        create_type=True,
    )
    booking_mode_enum.create(op.get_bind(), checkfirst=True)

    # Booking status enum
    booking_status_enum = postgresql.ENUM(
        'requested', 'matching', 'matched', 'accepted', 'in_progress',
        'delivered', 'approved', 'disputed', 'completed', 'cancelled', 'expired',
        name='booking_status',
        create_type=True,
    )
    booking_status_enum.create(op.get_bind(), checkfirst=True)

    # Payment status enum
    payment_status_enum = postgresql.ENUM(
        'pending', 'escrowed', 'released', 'refunded', 'failed',
        name='payment_status',
        create_type=True,
    )
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    # Auction status enum
    auction_status_enum = postgresql.ENUM(
        'draft', 'scheduled', 'open', 'closed', 'awarded', 'cancelled',
        name='auction_status',
        create_type=True,
    )
    auction_status_enum.create(op.get_bind(), checkfirst=True)

    # Bid status enum
    bid_status_enum = postgresql.ENUM(
        'active', 'outbid', 'withdrawn', 'accepted', 'rejected',
        name='bid_status',
        create_type=True,
    )
    bid_status_enum.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # PERFORMERS TABLE
    # ==========================================================================
    op.create_table(
        "performers",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),

        # Identity
        sa.Column("stage_name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Type and status
        sa.Column("performer_type", performer_type_enum, nullable=False, server_default="human"),
        sa.Column("availability_status", performer_availability_enum, nullable=False, server_default="offline"),
        sa.Column("verification_status", performer_verification_enum, nullable=False, server_default="unverified"),

        # Profile
        sa.Column("profile_image_path", sa.String(500), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("specialties", postgresql.ARRAY(sa.String), nullable=True),

        # Rating and performance
        sa.Column("aci_score", sa.Float(), nullable=False, server_default="50.0"),

        # Statistics
        sa.Column("total_bookings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_bookings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_earnings_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("lifetime_earnings_usd", sa.Float(), nullable=False, server_default="0.0"),

        # Revenue split
        sa.Column("revenue_split_percent", sa.Float(), nullable=False, server_default="50.0"),

        # Motion capabilities and pricing (JSON)
        sa.Column("motion_capabilities", postgresql.JSONB(), nullable=True),
        sa.Column("pricing", postgresql.JSONB(), nullable=True),

        # Banking and legal (encrypted at rest)
        sa.Column("banking_info", postgresql.JSONB(), nullable=True),
        sa.Column("consent_documents", postgresql.JSONB(), nullable=True),

        # Activity
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for performers
    op.create_index("ix_performers_stage_name", "performers", ["stage_name"])
    op.create_index("ix_performers_user_id", "performers", ["user_id"])
    op.create_index("ix_performers_availability_status", "performers", ["availability_status"])
    op.create_index("ix_performers_aci_score", "performers", ["aci_score"])
    op.create_index("ix_performers_is_active", "performers", ["is_active"])

    # ==========================================================================
    # PERFORMANCE_TAKES TABLE
    # ==========================================================================
    op.create_table(
        "performance_takes",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),

        # Foreign key
        sa.Column("performer_id", postgresql.UUID(as_uuid=True), nullable=False),

        # Take identification
        sa.Column("take_name", sa.String(255), nullable=False),
        sa.Column("mode", take_mode_enum, nullable=False, server_default="blink"),

        # Duration and timing
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("recording_date", sa.DateTime(timezone=True), nullable=False),

        # Content classification
        sa.Column("emotion_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("scene_context", sa.Text(), nullable=True),

        # Motion data paths (JSON)
        sa.Column("motion_profile", postgresql.JSONB(), nullable=True),

        # Quality metrics (JSON)
        sa.Column("quality_metrics", postgresql.JSONB(), nullable=True),

        # Status
        sa.Column("status", take_status_enum, nullable=False, server_default="processing"),

        # Demo reel flag
        sa.Column("is_demo_reel", sa.Boolean(), nullable=False, server_default="false"),

        # Usage statistics
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),

        # Storage
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("thumbnail_path", sa.String(500), nullable=True),
        sa.Column("preview_video_path", sa.String(500), nullable=True),

        # Processing info
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(["performer_id"], ["performers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for performance_takes
    op.create_index("ix_performance_takes_performer_id", "performance_takes", ["performer_id"])
    op.create_index("ix_performance_takes_mode", "performance_takes", ["mode"])
    op.create_index("ix_performance_takes_status", "performance_takes", ["status"])

    # ==========================================================================
    # BOOKINGS TABLE
    # ==========================================================================
    op.create_table(
        "bookings",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),

        # Foreign keys
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("performer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requester_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("take_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Booking type and status
        sa.Column("booking_mode", booking_mode_enum, nullable=False),
        sa.Column("status", booking_status_enum, nullable=False, server_default="requested"),

        # Requirements
        sa.Column("duration_requested_seconds", sa.Float(), nullable=False),
        sa.Column("duration_delivered_seconds", sa.Float(), nullable=True),
        sa.Column("emotion_requirements", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("motion_requirements", postgresql.JSONB(), nullable=True),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("character_context", sa.Text(), nullable=True),
        sa.Column("scene_description", sa.Text(), nullable=True),

        # Pricing
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("platform_fee_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("performer_payout_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_price_usd", sa.Float(), nullable=True),

        # Payment
        sa.Column("payment_status", payment_status_enum, nullable=False, server_default="pending"),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("escrowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),

        # Retry handling
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("retry_reason", sa.Text(), nullable=True),

        # Timeline
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),

        # Dispute handling
        sa.Column("is_disputed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("dispute_reason", sa.Text(), nullable=True),
        sa.Column("dispute_resolution", sa.Text(), nullable=True),
        sa.Column("disputed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),

        # Notes
        sa.Column("director_notes", sa.Text(), nullable=True),
        sa.Column("performer_notes", sa.Text(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["performer_id"], ["performers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["take_id"], ["performance_takes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for bookings
    op.create_index("ix_bookings_project_id", "bookings", ["project_id"])
    op.create_index("ix_bookings_shot_id", "bookings", ["shot_id"])
    op.create_index("ix_bookings_performer_id", "bookings", ["performer_id"])
    op.create_index("ix_bookings_requester_user_id", "bookings", ["requester_user_id"])
    op.create_index("ix_bookings_booking_mode", "bookings", ["booking_mode"])
    op.create_index("ix_bookings_status", "bookings", ["status"])

    # ==========================================================================
    # AUCTIONS TABLE
    # ==========================================================================
    op.create_table(
        "auctions",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),

        # Foreign keys
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("creator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("winning_bid_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Auction details
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        # Status
        sa.Column("status", auction_status_enum, nullable=False, server_default="draft"),

        # Requirements (JSON)
        sa.Column("requirements", postgresql.JSONB(), nullable=True),

        # Qualification requirements
        sa.Column("min_aci_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("required_specialties", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("performer_type_required", sa.String(50), nullable=True),

        # Bidding parameters
        sa.Column("min_bid_usd", sa.Float(), nullable=False),
        sa.Column("max_bid_usd", sa.Float(), nullable=True),
        sa.Column("reserve_price_usd", sa.Float(), nullable=True),

        # Timing
        sa.Column("duration_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True),

        # Cancellation
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),

        # Statistics
        sa.Column("total_bids", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_bidders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("highest_bid_usd", sa.Float(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for auctions
    op.create_index("ix_auctions_project_id", "auctions", ["project_id"])
    op.create_index("ix_auctions_creator_user_id", "auctions", ["creator_user_id"])
    op.create_index("ix_auctions_status", "auctions", ["status"])

    # ==========================================================================
    # AUCTION_BIDS TABLE
    # ==========================================================================
    op.create_table(
        "auction_bids",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),

        # Foreign keys
        sa.Column("auction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("performer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_take_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Bid details
        sa.Column("bid_amount_usd", sa.Float(), nullable=False),
        sa.Column("proposed_delivery_hours", sa.Integer(), nullable=False, server_default="24"),

        # Pitch
        sa.Column("pitch_message", sa.Text(), nullable=True),

        # Status
        sa.Column("status", bid_status_enum, nullable=False, server_default="active"),

        # Timing
        sa.Column("bid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),

        # Auto-bid settings
        sa.Column("auto_bid_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("auto_bid_max_usd", sa.Float(), nullable=True),
        sa.Column("auto_bid_increment_usd", sa.Float(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(["auction_id"], ["auctions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performer_id"], ["performers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sample_take_id"], ["performance_takes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for auction_bids
    op.create_index("ix_auction_bids_auction_id", "auction_bids", ["auction_id"])
    op.create_index("ix_auction_bids_performer_id", "auction_bids", ["performer_id"])
    op.create_index("ix_auction_bids_status", "auction_bids", ["status"])

    # Add foreign key for winning_bid_id in auctions (must be added after auction_bids exists)
    op.create_foreign_key(
        "fk_auctions_winning_bid_id",
        "auctions",
        "auction_bids",
        ["winning_bid_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ==========================================================================
    # PERFORMER_RATINGS TABLE
    # ==========================================================================
    op.create_table(
        "performer_ratings",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),

        # Foreign keys
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("performer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rater_user_id", postgresql.UUID(as_uuid=True), nullable=False),

        # Overall rating
        sa.Column("overall_score", sa.Float(), nullable=False),

        # Detailed scores
        sa.Column("motion_quality_score", sa.Float(), nullable=True),
        sa.Column("emotion_accuracy_score", sa.Float(), nullable=True),
        sa.Column("professionalism_score", sa.Float(), nullable=True),
        sa.Column("timeliness_score", sa.Float(), nullable=True),

        # Rehire indicator
        sa.Column("would_rehire", sa.Boolean(), nullable=False),

        # Written review
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("review_title", sa.String(255), nullable=True),

        # Visibility
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),

        # Audience engagement
        sa.Column("audience_buzz_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("helpful_votes", sa.Integer(), nullable=False, server_default="0"),

        # Moderation
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flag_reason", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="true"),

        # Performer response
        sa.Column("performer_response", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),

        # Rated at
        sa.Column("rated_at", sa.DateTime(timezone=True), nullable=False),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performer_id"], ["performers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for performer_ratings
    op.create_index("ix_performer_ratings_performer_id", "performer_ratings", ["performer_id"])
    op.create_index("ix_performer_ratings_rater_user_id", "performer_ratings", ["rater_user_id"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_performer_ratings_rater_user_id", table_name="performer_ratings")
    op.drop_index("ix_performer_ratings_performer_id", table_name="performer_ratings")
    op.drop_table("performer_ratings")

    op.drop_constraint("fk_auctions_winning_bid_id", "auctions", type_="foreignkey")

    op.drop_index("ix_auction_bids_status", table_name="auction_bids")
    op.drop_index("ix_auction_bids_performer_id", table_name="auction_bids")
    op.drop_index("ix_auction_bids_auction_id", table_name="auction_bids")
    op.drop_table("auction_bids")

    op.drop_index("ix_auctions_status", table_name="auctions")
    op.drop_index("ix_auctions_creator_user_id", table_name="auctions")
    op.drop_index("ix_auctions_project_id", table_name="auctions")
    op.drop_table("auctions")

    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_booking_mode", table_name="bookings")
    op.drop_index("ix_bookings_requester_user_id", table_name="bookings")
    op.drop_index("ix_bookings_performer_id", table_name="bookings")
    op.drop_index("ix_bookings_shot_id", table_name="bookings")
    op.drop_index("ix_bookings_project_id", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("ix_performance_takes_status", table_name="performance_takes")
    op.drop_index("ix_performance_takes_mode", table_name="performance_takes")
    op.drop_index("ix_performance_takes_performer_id", table_name="performance_takes")
    op.drop_table("performance_takes")

    op.drop_index("ix_performers_is_active", table_name="performers")
    op.drop_index("ix_performers_aci_score", table_name="performers")
    op.drop_index("ix_performers_availability_status", table_name="performers")
    op.drop_index("ix_performers_user_id", table_name="performers")
    op.drop_index("ix_performers_stage_name", table_name="performers")
    op.drop_table("performers")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS bid_status")
    op.execute("DROP TYPE IF EXISTS auction_status")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS booking_status")
    op.execute("DROP TYPE IF EXISTS booking_mode")
    op.execute("DROP TYPE IF EXISTS take_status")
    op.execute("DROP TYPE IF EXISTS take_mode")
    op.execute("DROP TYPE IF EXISTS performer_verification")
    op.execute("DROP TYPE IF EXISTS performer_availability")
    op.execute("DROP TYPE IF EXISTS performer_type")
