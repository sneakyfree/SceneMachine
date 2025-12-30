"""Initial database schema.

Revision ID: 001_initial
Revises:
Create Date: 2024-12-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("state", sa.String(50), nullable=False, server_default="empty"),
        sa.Column("settings", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_state", "projects", ["state"])

    # Screenplays table
    op.create_table(
        "screenplays",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("format", sa.String(50), nullable=False, server_default="fountain"),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("parsed_content", postgresql.JSON(), nullable=True),
        sa.Column("is_parsed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("parse_errors", postgresql.JSON(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_screenplays_project_id", "screenplays", ["project_id"])

    # Characters table
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("screenplay_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("age", sa.String(50), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("appearance", sa.Text(), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("lock_state", sa.String(20), nullable=False, server_default="unlocked"),
        sa.Column("reference_images", postgresql.JSON(), nullable=True),
        sa.Column("generation_settings", postgresql.JSON(), nullable=True),
        sa.Column("scene_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["screenplay_id"], ["screenplays.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"])
    op.create_index("ix_characters_name", "characters", ["name"])

    # Scenes table
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("screenplay_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_number", sa.String(20), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(500), nullable=True),
        sa.Column("scene_type", sa.String(20), nullable=True),
        sa.Column("time_of_day", sa.String(20), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("mood", sa.String(100), nullable=True),
        sa.Column("duration_estimate_seconds", sa.Float(), nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("shot_breakdown_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("analysis", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["screenplay_id"], ["screenplays.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenes_project_id", "scenes", ["project_id"])
    op.create_index("ix_scenes_sequence_number", "scenes", ["sequence_number"])

    # Shots table
    op.create_table(
        "shots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shot_number", sa.String(20), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("shot_type", sa.String(50), nullable=True),
        sa.Column("camera_movement", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dialogue", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True, server_default="3.0"),
        sa.Column("composition_notes", sa.Text(), nullable=True),
        sa.Column("lighting_notes", sa.Text(), nullable=True),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("output_path", sa.String(500), nullable=True),
        sa.Column("thumbnail_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shots_scene_id", "shots", ["scene_id"])
    op.create_index("ix_shots_sequence_number", "shots", ["sequence_number"])

    # Generation jobs table
    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(50), nullable=False, server_default="local"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("generation_params", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_jobs_shot_id", "generation_jobs", ["shot_id"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])

    # Assets table
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("thumbnail_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])

    # User settings table
    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("settings_key", sa.String(50), nullable=False, unique=True),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("video_provider", sa.String(50), nullable=True),
        sa.Column("anthropic_api_key", sa.Text(), nullable=True),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("replicate_api_key", sa.Text(), nullable=True),
        sa.Column("fal_api_key", sa.Text(), nullable=True),
        sa.Column("runwayml_api_key", sa.Text(), nullable=True),
        sa.Column("max_concurrent_generations", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("generation_timeout_seconds", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("default_video_resolution", sa.String(20), nullable=False, server_default="1920x1080"),
        sa.Column("default_video_fps", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("theme_mode", sa.String(20), nullable=False, server_default="dark"),
        sa.Column("auto_save_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_advanced_options", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("auto_cleanup_temp_files", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_cache_size_gb", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("default_export_format", sa.String(20), nullable=False, server_default="mp4_h264"),
        sa.Column("default_export_quality", sa.String(20), nullable=False, server_default="high"),
        sa.Column("additional_settings", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settings_key"),
    )

    # Character-scene association table
    op.create_table(
        "character_scenes",
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id", "scene_id"),
    )


def downgrade() -> None:
    op.drop_table("character_scenes")
    op.drop_table("user_settings")
    op.drop_table("assets")
    op.drop_table("generation_jobs")
    op.drop_table("shots")
    op.drop_table("scenes")
    op.drop_table("characters")
    op.drop_table("screenplays")
    op.drop_table("projects")
