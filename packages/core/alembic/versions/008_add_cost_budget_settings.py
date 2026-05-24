"""Add cost budget persistence columns to user_settings.

Revision ID: 008_cost_budget
Revises: 007_lipsync_jobs
Create Date: 2026-05-24

Before this migration, `CostTrackingService.set_budget_limit()` only mutated
`self._budget_limit` — an instance attribute. A new service instance per
session means the budget is lost on every IPC call. The desktop cost
dashboard's "Set Budget" button effectively did nothing once the renderer
disconnected. This is P0-8 in docs/INVENTORY_DEFECTS.md.

Adds two columns to the singleton `user_settings` row:
- cost_budget_limit_usd  (Float, nullable so "no budget set" is encodable)
- cost_budget_period_days (Integer, defaults to 30 — the existing
  CostTrackingService default)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_cost_budget"
down_revision: Union[str, None] = "007_lipsync_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cost-budget persistence columns to user_settings."""
    op.add_column(
        "user_settings",
        sa.Column(
            "cost_budget_limit_usd",
            sa.Float(),
            nullable=True,
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "cost_budget_period_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("30"),
        ),
    )


def downgrade() -> None:
    """Drop cost-budget persistence columns."""
    op.drop_column("user_settings", "cost_budget_period_days")
    op.drop_column("user_settings", "cost_budget_limit_usd")
