"""Add monetization tables

Revision ID: 005_monetization
Revises: 004_social
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_monetization"
down_revision: Union[str, None] = "004_social"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    transaction_type = postgresql.ENUM(
        "ad_revenue", "ticket_sale", "tip", "subscription",
        name="transactiontype",
        create_type=True,
    )
    transaction_type.create(op.get_bind())

    transaction_status = postgresql.ENUM(
        "pending", "completed", "failed", "refunded",
        name="transactionstatus",
        create_type=True,
    )
    transaction_status.create(op.get_bind())

    payout_status = postgresql.ENUM(
        "pending", "processing", "completed", "failed",
        name="payoutstatus",
        create_type=True,
    )
    payout_status.create(op.get_bind())

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", transaction_type, nullable=False),
        sa.Column("status", transaction_status, nullable=False),
        sa.Column("amount_gross", sa.Numeric(10, 2), nullable=False),
        sa.Column("platform_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("processing_fee", sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column("amount_net", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("stripe_payment_id", sa.String(100), nullable=True),
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
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_creator_id", "transactions", ["creator_id"])
    op.create_index("ix_transactions_video_id", "transactions", ["video_id"])
    op.create_index("ix_transactions_creator_date", "transactions", ["creator_id", "created_at"])
    op.create_index("ix_transactions_type_date", "transactions", ["transaction_type", "created_at"])

    # Create payouts table
    op.create_table(
        "payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", payout_status, nullable=False),
        sa.Column("stripe_transfer_id", sa.String(100), nullable=True),
        sa.Column("stripe_payout_id", sa.String(100), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
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
    op.create_index("ix_payouts_creator_id", "payouts", ["creator_id"])
    op.create_index("ix_payouts_creator_status", "payouts", ["creator_id", "status"])
    op.create_index("ix_payouts_status", "payouts", ["status"])

    # Create ad_impressions table
    op.create_table(
        "ad_impressions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("viewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ad_type", sa.String(50), nullable=False),
        sa.Column("ad_provider", sa.String(50), nullable=False),
        sa.Column("ad_campaign_id", sa.String(100), nullable=True),
        sa.Column("cpm_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("revenue", sa.Numeric(10, 6), nullable=False),
        sa.Column("was_skipped", sa.Boolean(), nullable=False, default=False),
        sa.Column("watch_duration_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("country_code", sa.String(2), nullable=True),
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
        sa.ForeignKeyConstraint(["session_id"], ["watch_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["viewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_impressions_video_id", "ad_impressions", ["video_id"])
    op.create_index("ix_ad_impressions_video_date", "ad_impressions", ["video_id", "created_at"])

    # Create ticket_purchases table
    op.create_table(
        "ticket_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, default="USD"),
        sa.Column("stripe_payment_intent_id", sa.String(100), nullable=True),
        sa.Column("stripe_charge_id", sa.String(100), nullable=True),
        sa.Column("status", transaction_status, nullable=False),
        sa.Column("access_granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_refunded", sa.Boolean(), nullable=False, default=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_purchases_video_id", "ticket_purchases", ["video_id"])
    op.create_index("ix_ticket_purchases_buyer_id", "ticket_purchases", ["buyer_id"])
    op.create_index(
        "ix_ticket_purchases_buyer_video",
        "ticket_purchases",
        ["buyer_id", "video_id"],
        unique=True,
    )

    # Create tips table
    op.create_table(
        "tips",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipper_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, default="USD"),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, default=True),
        sa.Column("stripe_payment_intent_id", sa.String(100), nullable=True),
        sa.Column("status", transaction_status, nullable=False),
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
        sa.ForeignKeyConstraint(["tipper_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tips_creator_id", "tips", ["creator_id"])
    op.create_index("ix_tips_creator_date", "tips", ["creator_id", "created_at"])


def downgrade() -> None:
    # Drop tables
    op.drop_index("ix_tips_creator_date", table_name="tips")
    op.drop_index("ix_tips_creator_id", table_name="tips")
    op.drop_table("tips")

    op.drop_index("ix_ticket_purchases_buyer_video", table_name="ticket_purchases")
    op.drop_index("ix_ticket_purchases_buyer_id", table_name="ticket_purchases")
    op.drop_index("ix_ticket_purchases_video_id", table_name="ticket_purchases")
    op.drop_table("ticket_purchases")

    op.drop_index("ix_ad_impressions_video_date", table_name="ad_impressions")
    op.drop_index("ix_ad_impressions_video_id", table_name="ad_impressions")
    op.drop_table("ad_impressions")

    op.drop_index("ix_payouts_status", table_name="payouts")
    op.drop_index("ix_payouts_creator_status", table_name="payouts")
    op.drop_index("ix_payouts_creator_id", table_name="payouts")
    op.drop_table("payouts")

    op.drop_index("ix_transactions_type_date", table_name="transactions")
    op.drop_index("ix_transactions_creator_date", table_name="transactions")
    op.drop_index("ix_transactions_video_id", table_name="transactions")
    op.drop_index("ix_transactions_creator_id", table_name="transactions")
    op.drop_table("transactions")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS payoutstatus")
    op.execute("DROP TYPE IF EXISTS transactionstatus")
    op.execute("DROP TYPE IF EXISTS transactiontype")
