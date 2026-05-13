"""Add accessibility settings to user_settings table.

Revision ID: 006_accessibility
Revises: 005_actcore
Create Date: 2026-01-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_accessibility"
down_revision: Union[str, None] = "005_actcore"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add accessibility settings columns."""
    # Add font_size_scale column
    op.add_column(
        "user_settings",
        sa.Column(
            "font_size_scale",
            sa.String(20),
            nullable=False,
            server_default="medium",
        ),
    )

    # Add high_contrast_enabled column
    op.add_column(
        "user_settings",
        sa.Column(
            "high_contrast_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Add reduce_motion_enabled column
    op.add_column(
        "user_settings",
        sa.Column(
            "reduce_motion_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Add large_click_targets_enabled column
    op.add_column(
        "user_settings",
        sa.Column(
            "large_click_targets_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    """Remove accessibility settings columns."""
    op.drop_column("user_settings", "large_click_targets_enabled")
    op.drop_column("user_settings", "reduce_motion_enabled")
    op.drop_column("user_settings", "high_contrast_enabled")
    op.drop_column("user_settings", "font_size_scale")
