"""Add streaming tables

Revision ID: 003_streaming
Revises: 002_videos
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_streaming"
down_revision: Union[str, None] = "002_videos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create watch_history table
    op.create_table(
        "watch_history",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("progress_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("watch_percent", sa.Float(), nullable=False, default=0.0),
        sa.Column("completed", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "last_watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "first_watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("watch_count", sa.Integer(), nullable=False, default=1),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "video_id"),
    )
    op.create_index("ix_watch_history_user_last", "watch_history", ["user_id", "last_watched_at"])
    op.create_index("ix_watch_history_video", "watch_history", ["video_id"])

    # Create watch_sessions table
    op.create_table(
        "watch_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        sa.Column("browser", sa.String(50), nullable=True),
        sa.Column("os", sa.String(50), nullable=True),
        sa.Column("current_position_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("quality_level", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("watch_time_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("referrer", sa.String(500), nullable=True),
        sa.Column("traffic_source", sa.String(50), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watch_sessions_user_id", "watch_sessions", ["user_id"])
    op.create_index("ix_watch_sessions_video_id", "watch_sessions", ["video_id"])
    op.create_index("ix_watch_sessions_token", "watch_sessions", ["session_token"], unique=True)
    op.create_index("ix_watch_sessions_active", "watch_sessions", ["video_id", "is_active"])
    op.create_index("ix_watch_sessions_heartbeat", "watch_sessions", ["last_heartbeat_at"])

    # Create view_events table
    op.create_table(
        "view_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("watch_time_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("watch_percent", sa.Float(), nullable=False, default=0.0),
        sa.Column("completed", sa.Boolean(), nullable=False, default=False),
        sa.Column("average_quality", sa.String(20), nullable=True),
        sa.Column("quality_changes", sa.Integer(), nullable=False, default=0),
        sa.Column("buffering_events", sa.Integer(), nullable=False, default=0),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        sa.Column("is_valid_view", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["watch_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_view_events_video_id", "view_events", ["video_id"])
    op.create_index("ix_view_events_user_id", "view_events", ["user_id"])
    op.create_index("ix_view_events_ip_hash", "view_events", ["ip_hash"])
    op.create_index("ix_view_events_viewed_at", "view_events", ["viewed_at"])
    op.create_index("ix_view_events_video_date", "view_events", ["video_id", "viewed_at"])
    op.create_index("ix_view_events_dedup", "view_events", ["video_id", "ip_hash", "viewed_at"])


def downgrade() -> None:
    op.drop_index("ix_view_events_dedup", table_name="view_events")
    op.drop_index("ix_view_events_video_date", table_name="view_events")
    op.drop_index("ix_view_events_viewed_at", table_name="view_events")
    op.drop_index("ix_view_events_ip_hash", table_name="view_events")
    op.drop_index("ix_view_events_user_id", table_name="view_events")
    op.drop_index("ix_view_events_video_id", table_name="view_events")
    op.drop_table("view_events")

    op.drop_index("ix_watch_sessions_heartbeat", table_name="watch_sessions")
    op.drop_index("ix_watch_sessions_active", table_name="watch_sessions")
    op.drop_index("ix_watch_sessions_token", table_name="watch_sessions")
    op.drop_index("ix_watch_sessions_video_id", table_name="watch_sessions")
    op.drop_index("ix_watch_sessions_user_id", table_name="watch_sessions")
    op.drop_table("watch_sessions")

    op.drop_index("ix_watch_history_video", table_name="watch_history")
    op.drop_index("ix_watch_history_user_last", table_name="watch_history")
    op.drop_table("watch_history")
