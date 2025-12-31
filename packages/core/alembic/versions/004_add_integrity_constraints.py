"""Add integrity constraints and indexes for data validation.

Revision ID: 004_integrity_constraints
Revises: 003_export_history
Create Date: 2024-12-30

This migration adds:
- Check constraints for status validation
- Check constraints for numeric ranges
- Unique constraints where appropriate
- Composite indexes for common queries
- Partial indexes for filtered queries
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_integrity_constraints"
down_revision: Union[str, None] = "003_export_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add integrity constraints."""

    # ============================================================================
    # Projects Table Constraints
    # ============================================================================

    # Valid project states
    op.create_check_constraint(
        "ck_projects_state",
        "projects",
        "state IN ('draft', 'screenplay_uploaded', 'planning', 'generating', 'assembly_in_progress', 'complete', 'exported', 'archived')"
    )

    # Unique project name per user (for future multi-user support)
    op.create_index(
        "ix_projects_name_unique",
        "projects",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ============================================================================
    # Scenes Table Constraints
    # ============================================================================

    # Positive sequence number
    op.create_check_constraint(
        "ck_scenes_sequence_positive",
        "scenes",
        "sequence_number > 0"
    )

    # Valid time of day
    op.create_check_constraint(
        "ck_scenes_time_of_day",
        "scenes",
        "time_of_day IN ('day', 'night', 'dawn', 'dusk', 'morning', 'afternoon', 'evening', 'unspecified')"
    )

    # Unique scene number within project
    op.create_index(
        "ix_scenes_project_scene_number",
        "scenes",
        ["project_id", "scene_number"],
        unique=True,
    )

    # Composite index for scene ordering
    op.create_index(
        "ix_scenes_project_sequence",
        "scenes",
        ["project_id", "sequence_number"],
    )

    # ============================================================================
    # Shots Table Constraints
    # ============================================================================

    # Valid shot states
    op.create_check_constraint(
        "ck_shots_state",
        "shots",
        "state IN ('planned', 'queued', 'generating', 'generated', 'review', 'approved', 'rejected', 'failed')"
    )

    # Positive duration
    op.create_check_constraint(
        "ck_shots_duration_positive",
        "shots",
        "duration_seconds > 0 AND duration_seconds <= 60"  # Max 1 minute per shot
    )

    # Positive sequence number
    op.create_check_constraint(
        "ck_shots_sequence_positive",
        "shots",
        "sequence_number > 0"
    )

    # Unique shot number within scene
    op.create_index(
        "ix_shots_scene_shot_number",
        "shots",
        ["scene_id", "shot_number"],
        unique=True,
    )

    # Composite index for shot ordering
    op.create_index(
        "ix_shots_scene_sequence",
        "shots",
        ["scene_id", "sequence_number"],
    )

    # Partial index for active shots (not rejected)
    op.create_index(
        "ix_shots_active",
        "shots",
        ["scene_id", "state"],
        postgresql_where=sa.text("state != 'rejected' AND state != 'failed'"),
    )

    # ============================================================================
    # Characters Table Constraints
    # ============================================================================

    # Unique character name within project
    op.create_index(
        "ix_characters_project_name",
        "characters",
        ["project_id", "name"],
        unique=True,
    )

    # ============================================================================
    # Generation Jobs Table Constraints
    # ============================================================================

    # Valid job statuses
    op.create_check_constraint(
        "ck_generation_jobs_status",
        "generation_jobs",
        "status IN ('pending', 'preparing', 'running', 'post_processing', 'completed', 'failed', 'cancelled', 'timeout')"
    )

    # Progress percentage range
    op.create_check_constraint(
        "ck_generation_jobs_progress",
        "generation_jobs",
        "progress_percent >= 0 AND progress_percent <= 100"
    )

    # Priority range
    op.create_check_constraint(
        "ck_generation_jobs_priority",
        "generation_jobs",
        "priority >= -100 AND priority <= 100"
    )

    # Positive retry count
    op.create_check_constraint(
        "ck_generation_jobs_retry_positive",
        "generation_jobs",
        "retry_count >= 0"
    )

    # Index for queue ordering
    op.create_index(
        "ix_generation_jobs_queue",
        "generation_jobs",
        ["status", "priority", "queued_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # Index for active jobs
    op.create_index(
        "ix_generation_jobs_active",
        "generation_jobs",
        ["status", "started_at"],
        postgresql_where=sa.text("status IN ('preparing', 'running', 'post_processing')"),
    )

    # ============================================================================
    # Export History Constraints
    # ============================================================================

    # Valid export statuses
    op.create_check_constraint(
        "ck_export_history_status",
        "export_history",
        "status IN ('pending', 'in_progress', 'encoding', 'verifying', 'completed', 'failed', 'cancelled')"
    )

    # Progress range
    op.create_check_constraint(
        "ck_export_history_progress",
        "export_history",
        "progress_percent >= 0 AND progress_percent <= 100"
    )

    # Valid frame rate
    op.create_check_constraint(
        "ck_export_history_frame_rate",
        "export_history",
        "frame_rate > 0 AND frame_rate <= 120"
    )

    # Positive file size
    op.create_check_constraint(
        "ck_export_history_file_size",
        "export_history",
        "file_size_bytes IS NULL OR file_size_bytes >= 0"
    )

    # ============================================================================
    # Assets Table Constraints (if exists)
    # ============================================================================

    try:
        # Valid asset types
        op.create_check_constraint(
            "ck_assets_type",
            "assets",
            "asset_type IN ('video', 'image', 'audio', 'thumbnail', 'lut', 'subtitle', 'final_movie')"
        )

        # Valid asset status
        op.create_check_constraint(
            "ck_assets_status",
            "assets",
            "status IN ('pending', 'processing', 'ready', 'failed', 'deleted')"
        )

        # Positive file size
        op.create_check_constraint(
            "ck_assets_file_size",
            "assets",
            "file_size_bytes IS NULL OR file_size_bytes >= 0"
        )
    except Exception:
        # Assets table may not exist
        pass

    # ============================================================================
    # Project Shares Constraints (if exists)
    # ============================================================================

    try:
        # Valid permission levels
        op.create_check_constraint(
            "ck_project_shares_permission",
            "project_shares",
            "permission IN ('view', 'comment', 'edit', 'admin')"
        )

        # Unique share per email per project
        op.create_index(
            "ix_project_shares_unique",
            "project_shares",
            ["project_id", "shared_with_email"],
            unique=True,
            postgresql_where=sa.text("revoked_at IS NULL"),
        )
    except Exception:
        # Shares table may not exist
        pass


def downgrade() -> None:
    """Remove integrity constraints."""

    # Project Shares
    try:
        op.drop_index("ix_project_shares_unique", table_name="project_shares")
        op.drop_constraint("ck_project_shares_permission", "project_shares", type_="check")
    except Exception:
        pass

    # Assets
    try:
        op.drop_constraint("ck_assets_file_size", "assets", type_="check")
        op.drop_constraint("ck_assets_status", "assets", type_="check")
        op.drop_constraint("ck_assets_type", "assets", type_="check")
    except Exception:
        pass

    # Export History
    op.drop_constraint("ck_export_history_file_size", "export_history", type_="check")
    op.drop_constraint("ck_export_history_frame_rate", "export_history", type_="check")
    op.drop_constraint("ck_export_history_progress", "export_history", type_="check")
    op.drop_constraint("ck_export_history_status", "export_history", type_="check")

    # Generation Jobs
    op.drop_index("ix_generation_jobs_active", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_queue", table_name="generation_jobs")
    op.drop_constraint("ck_generation_jobs_retry_positive", "generation_jobs", type_="check")
    op.drop_constraint("ck_generation_jobs_priority", "generation_jobs", type_="check")
    op.drop_constraint("ck_generation_jobs_progress", "generation_jobs", type_="check")
    op.drop_constraint("ck_generation_jobs_status", "generation_jobs", type_="check")

    # Characters
    op.drop_index("ix_characters_project_name", table_name="characters")

    # Shots
    op.drop_index("ix_shots_active", table_name="shots")
    op.drop_index("ix_shots_scene_sequence", table_name="shots")
    op.drop_index("ix_shots_scene_shot_number", table_name="shots")
    op.drop_constraint("ck_shots_sequence_positive", "shots", type_="check")
    op.drop_constraint("ck_shots_duration_positive", "shots", type_="check")
    op.drop_constraint("ck_shots_state", "shots", type_="check")

    # Scenes
    op.drop_index("ix_scenes_project_sequence", table_name="scenes")
    op.drop_index("ix_scenes_project_scene_number", table_name="scenes")
    op.drop_constraint("ck_scenes_time_of_day", "scenes", type_="check")
    op.drop_constraint("ck_scenes_sequence_positive", "scenes", type_="check")

    # Projects
    op.drop_index("ix_projects_name_unique", table_name="projects")
    op.drop_constraint("ck_projects_state", "projects", type_="check")
