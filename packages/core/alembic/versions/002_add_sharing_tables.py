"""Add project sharing tables.

Revision ID: 002_sharing
Revises: 001_initial
Create Date: 2024-12-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_sharing"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Project shares table
    op.create_table(
        "project_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("share_code", sa.String(64), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=True),
        sa.Column("recipient_name", sa.String(255), nullable=True),
        sa.Column("permission", sa.String(20), nullable=False, server_default="view"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_code"),
    )
    op.create_index("ix_project_shares_project_id", "project_shares", ["project_id"])
    op.create_index("ix_project_shares_share_code", "project_shares", ["share_code"])

    # Project comments table
    op.create_table(
        "project_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_name", sa.String(255), nullable=False),
        sa.Column("author_email", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timecode_seconds", sa.Float(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["project_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_comments_project_id", "project_comments", ["project_id"])
    op.create_index("ix_project_comments_shot_id", "project_comments", ["shot_id"])


def downgrade() -> None:
    op.drop_table("project_comments")
    op.drop_table("project_shares")
