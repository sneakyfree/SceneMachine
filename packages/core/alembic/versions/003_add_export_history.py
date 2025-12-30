"""Add export history table.

Revision ID: 003_export_history
Revises: 002_sharing
Create Date: 2024-12-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_export_history"
down_revision: Union[str, None] = "002_sharing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_history",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Foreign key to project
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Export settings
        sa.Column("format", sa.String(50), nullable=False, server_default="mp4_h264"),
        sa.Column("quality", sa.String(50), nullable=False, server_default="high"),
        sa.Column("resolution", sa.String(20), nullable=False, server_default="1920x1080"),
        sa.Column("frame_rate", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("video_bitrate", sa.String(20), nullable=True),
        sa.Column("audio_bitrate", sa.String(20), nullable=True),
        # Status tracking
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("progress_message", sa.String(255), nullable=True),
        # Output information
        sa.Column("output_filename", sa.String(255), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        # Verified metadata from FFmpeg probe
        sa.Column("actual_duration_seconds", sa.Float(), nullable=True),
        sa.Column("actual_resolution", sa.String(20), nullable=True),
        sa.Column("actual_fps", sa.Float(), nullable=True),
        sa.Column("video_codec", sa.String(50), nullable=True),
        sa.Column("audio_codec", sa.String(50), nullable=True),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encoding_duration_seconds", sa.Float(), nullable=True),
        # Error tracking
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        # Additional metadata as JSON
        sa.Column("export_settings", postgresql.JSONB(), nullable=True),
        sa.Column("verification_result", postgresql.JSONB(), nullable=True),
        # Feature flags
        sa.Column("include_subtitles", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("include_audio", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("has_watermark", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_color_grade", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Indexes
    op.create_index("ix_export_history_project_id", "export_history", ["project_id"])
    op.create_index("ix_export_history_status", "export_history", ["status"])
    op.create_index("ix_export_history_created_at", "export_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_export_history_created_at", table_name="export_history")
    op.drop_index("ix_export_history_status", table_name="export_history")
    op.drop_index("ix_export_history_project_id", table_name="export_history")
    op.drop_table("export_history")
