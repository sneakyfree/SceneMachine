"""Add video tables

Revision ID: 002_videos
Revises: 001_initial_users
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_videos"
down_revision: Union[str, None] = "001_initial_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE contenttype AS ENUM ('film', 'series', 'short', 'animation', 'music_video', 'clip', 'other')")
    op.execute("CREATE TYPE monetizationtype AS ENUM ('free_ad', 'free_no_ad', 'paid', 'subscriber_only')")
    op.execute("CREATE TYPE videostatus AS ENUM ('uploading', 'processing', 'ready', 'published', 'unlisted', 'private', 'removed', 'failed')")
    op.execute("CREATE TYPE transcodingstatus AS ENUM ('pending', 'in_progress', 'completed', 'failed')")

    # Create series table
    op.create_table(
        "series",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("episode_count", sa.Integer(), nullable=False, default=0),
        sa.Column("total_views", sa.Integer(), nullable=False, default=0),
        sa.Column("is_complete", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_series_creator_id", "series", ["creator_id"])

    # Create videos table
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "content_type",
            postgresql.ENUM("film", "series", "short", "animation", "music_video", "clip", "other", name="contenttype", create_type=False),
            nullable=False,
            default="other",
        ),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("made_with_studio", sa.Boolean(), nullable=False, default=False),
        sa.Column("studio_project_id", sa.String(36), nullable=True),
        sa.Column("source_file_key", sa.String(500), nullable=True),
        sa.Column("transcoded_versions", postgresql.JSON(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, default=0),
        sa.Column(
            "transcoding_status",
            postgresql.ENUM("pending", "in_progress", "completed", "failed", name="transcodingstatus", create_type=False),
            nullable=False,
            default="pending",
        ),
        sa.Column("transcoding_progress", sa.Integer(), nullable=False, default=0),
        sa.Column("transcoding_error", sa.Text(), nullable=True),
        sa.Column(
            "monetization_type",
            postgresql.ENUM("free_ad", "free_no_ad", "paid", "subscriber_only", name="monetizationtype", create_type=False),
            nullable=False,
            default="free_ad",
        ),
        sa.Column("ticket_price", sa.Numeric(8, 2), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("uploading", "processing", "ready", "published", "unlisted", "private", "removed", "failed", name="videostatus", create_type=False),
            nullable=False,
            default="uploading",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, default=0),
        sa.Column("like_count", sa.Integer(), nullable=False, default=0),
        sa.Column("dislike_count", sa.Integer(), nullable=False, default=0),
        sa.Column("comment_count", sa.Integer(), nullable=False, default=0),
        sa.Column("share_count", sa.Integer(), nullable=False, default=0),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False, default=[]),
        sa.Column("quality_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("is_age_restricted", sa.Boolean(), nullable=False, default=False),
        sa.Column("moderation_status", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for videos
    op.create_index("ix_videos_creator_id", "videos", ["creator_id"])
    op.create_index("ix_videos_series_id", "videos", ["series_id"])
    op.create_index("ix_videos_status", "videos", ["status"])
    op.create_index("ix_videos_creator_status", "videos", ["creator_id", "status"])
    op.create_index("ix_videos_published_at", "videos", ["published_at"])
    op.create_index("ix_videos_quality_score", "videos", ["quality_score"])
    op.create_index("ix_videos_view_count", "videos", ["view_count"])

    # Create video_stats table
    op.create_table(
        "video_stats",
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False, default=0),
        sa.Column("unique_viewers", sa.Integer(), nullable=False, default=0),
        sa.Column("watch_time_minutes", sa.Integer(), nullable=False, default=0),
        sa.Column("average_watch_percent", sa.Float(), nullable=False, default=0.0),
        sa.Column("completions", sa.Integer(), nullable=False, default=0),
        sa.Column("likes", sa.Integer(), nullable=False, default=0),
        sa.Column("dislikes", sa.Integer(), nullable=False, default=0),
        sa.Column("comments", sa.Integer(), nullable=False, default=0),
        sa.Column("shares", sa.Integer(), nullable=False, default=0),
        sa.Column("ad_impressions", sa.Integer(), nullable=False, default=0),
        sa.Column("ad_revenue", sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column("ticket_sales", sa.Integer(), nullable=False, default=0),
        sa.Column("ticket_revenue", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("tip_count", sa.Integer(), nullable=False, default=0),
        sa.Column("tip_revenue", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("traffic_sources", postgresql.JSON(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("geography", postgresql.JSON(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("video_id", "date"),
    )
    op.create_index("ix_video_stats_date", "video_stats", ["date"])
    op.create_index("ix_video_stats_video_date", "video_stats", ["video_id", "date"])

    # Create cost_tracking table
    op.create_table(
        "cost_tracking",
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False, default=0),
        sa.Column("storage_cost", sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column("bandwidth_bytes", sa.BigInteger(), nullable=False, default=0),
        sa.Column("bandwidth_cost", sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column("processing_cost", sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("video_id", "month"),
    )


def downgrade() -> None:
    op.drop_table("cost_tracking")
    op.drop_table("video_stats")
    op.drop_index("ix_videos_view_count", table_name="videos")
    op.drop_index("ix_videos_quality_score", table_name="videos")
    op.drop_index("ix_videos_published_at", table_name="videos")
    op.drop_index("ix_videos_creator_status", table_name="videos")
    op.drop_index("ix_videos_status", table_name="videos")
    op.drop_index("ix_videos_series_id", table_name="videos")
    op.drop_index("ix_videos_creator_id", table_name="videos")
    op.drop_table("videos")
    op.drop_index("ix_series_creator_id", table_name="series")
    op.drop_table("series")
    op.execute("DROP TYPE IF EXISTS transcodingstatus")
    op.execute("DROP TYPE IF EXISTS videostatus")
    op.execute("DROP TYPE IF EXISTS monetizationtype")
    op.execute("DROP TYPE IF EXISTS contenttype")
