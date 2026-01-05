"""Initial user tables

Revision ID: 001_initial_users
Revises:
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_creator", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        sa.Column("oauth_id", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for users
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_oauth", "users", ["oauth_provider", "oauth_id"])
    op.create_index(
        "ix_users_email_lower", "users", [sa.text("lower(email)")]
    )
    op.create_index(
        "ix_users_username_lower", "users", [sa.text("lower(username)")]
    )

    # Create creator_profiles table
    op.create_table(
        "creator_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_name", sa.String(100), nullable=False),
        sa.Column("channel_description", sa.Text(), nullable=True),
        sa.Column("channel_banner_url", sa.String(500), nullable=True),
        sa.Column("monetization_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("tax_info_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("stripe_account_id", sa.String(255), nullable=True),
        sa.Column("stripe_onboarding_complete", sa.Boolean(), nullable=False, default=False),
        sa.Column("total_earnings", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("pending_payout", sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column("current_tier", sa.Integer(), nullable=False, default=1),
        sa.Column("subscriber_count", sa.Integer(), nullable=False, default=0),
        sa.Column("total_views", sa.Integer(), nullable=False, default=0),
        sa.Column("video_count", sa.Integer(), nullable=False, default=0),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # Create user_settings table
    op.create_table(
        "user_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notification_preferences",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            default={},
        ),
        sa.Column(
            "privacy_settings",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            default={},
        ),
        sa.Column(
            "display_preferences",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            default={},
        ),
        sa.Column("studio_linked", sa.Boolean(), nullable=False, default=False),
        sa.Column("studio_license_key", sa.String(255), nullable=True),
        sa.Column("studio_linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("two_factor_secret", sa.String(255), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_table("creator_profiles")
    op.drop_index("ix_users_username_lower", table_name="users")
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_index("ix_users_oauth", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
