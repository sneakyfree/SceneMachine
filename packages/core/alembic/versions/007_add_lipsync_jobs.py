"""Add lipsync_jobs table.

Revision ID: 007_lipsync_jobs
Revises: 006_accessibility
Create Date: 2026-05-24

The LipsyncJob model existed at packages/core/scenemachine/models/lipsync_job.py
but no migration created its table. Fresh DBs failed with "relation lipsync_jobs
does not exist" the moment any IPC lipsync handler ran. Migrations 001-006
predated the model; this migration closes that gap. See P0 entry in
docs/INVENTORY_DEFECTS.md under "Stage 1 IPC fuzz + DB migration".
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_lipsync_jobs"
down_revision: Union[str, None] = "006_accessibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum values mirror scenemachine.models.lipsync_job.LipsyncJobStatus.
LIPSYNC_JOB_STATUS_VALUES = (
    "queued",
    "processing",
    "completed",
    "failed",
    "cancelled",
)


def upgrade() -> None:
    """Create the lipsync_jobs table and its status enum."""
    lipsync_status = postgresql.ENUM(
        *LIPSYNC_JOB_STATUS_VALUES,
        name="lipsync_job_status",
        create_type=False,
    )
    lipsync_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lipsync_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "shot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "video_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "audio_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "output_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            lipsync_status,
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "progress_percent",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "progress_message",
            sa.String(255),
            nullable=False,
            server_default="Job queued",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            server_default="mock",
        ),
        sa.Column("output_path", sa.String(512), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_lipsync_jobs_shot_id",
        "lipsync_jobs",
        ["shot_id"],
    )
    op.create_index(
        "ix_lipsync_jobs_video_asset_id",
        "lipsync_jobs",
        ["video_asset_id"],
    )
    op.create_index(
        "ix_lipsync_jobs_audio_asset_id",
        "lipsync_jobs",
        ["audio_asset_id"],
    )
    op.create_index(
        "ix_lipsync_jobs_status",
        "lipsync_jobs",
        ["status"],
    )


def downgrade() -> None:
    """Drop the lipsync_jobs table and its status enum."""
    op.drop_index("ix_lipsync_jobs_status", table_name="lipsync_jobs")
    op.drop_index("ix_lipsync_jobs_audio_asset_id", table_name="lipsync_jobs")
    op.drop_index("ix_lipsync_jobs_video_asset_id", table_name="lipsync_jobs")
    op.drop_index("ix_lipsync_jobs_shot_id", table_name="lipsync_jobs")
    op.drop_table("lipsync_jobs")

    lipsync_status = postgresql.ENUM(
        *LIPSYNC_JOB_STATUS_VALUES,
        name="lipsync_job_status",
        create_type=False,
    )
    lipsync_status.drop(op.get_bind(), checkfirst=True)
