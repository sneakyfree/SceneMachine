"""Add social tables

Revision ID: 004_social
Revises: 003_streaming
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_social"
down_revision: Union[str, None] = "003_streaming"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create follows table
    op.create_table(
        "follows",
        sa.Column("follower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("following_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notify_on_upload", sa.Boolean(), nullable=False, default=True),
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
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["following_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("follower_id", "following_id"),
    )
    op.create_index("ix_follows_follower", "follows", ["follower_id"])
    op.create_index("ix_follows_following", "follows", ["following_id"])

    # Create comments table
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False, default=0),
        sa.Column("is_creator_heart", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, default=False),
        sa.Column("hidden_reason", sa.String(200), nullable=True),
        sa.Column("is_edited", sa.Boolean(), nullable=False, default=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_video_id", "comments", ["video_id"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.create_index("ix_comments_video_created", "comments", ["video_id", "created_at"])
    op.create_index("ix_comments_user_created", "comments", ["user_id", "created_at"])

    # Create comment_likes table
    op.create_table(
        "comment_likes",
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("comment_id", "user_id"),
    )
    op.create_index("ix_comment_likes_comment", "comment_likes", ["comment_id"])
    op.create_index("ix_comment_likes_user", "comment_likes", ["user_id"])

    # Create reactions table
    reaction_type = postgresql.ENUM(
        "like", "love", "fire", "mind_blown", "sad", "laugh",
        name="reactiontype",
        create_type=True,
    )
    reaction_type.create(op.get_bind())

    op.create_table(
        "reactions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "reaction_type",
            reaction_type,
            nullable=False,
        ),
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
    op.create_index("ix_reactions_video", "reactions", ["video_id"])
    op.create_index("ix_reactions_user", "reactions", ["user_id"])
    op.create_index("ix_reactions_video_type", "reactions", ["video_id", "reaction_type"])

    # Create watchlist table
    op.create_table(
        "watchlist",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
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
    op.create_index("ix_watchlist_user_created", "watchlist", ["user_id", "created_at"])
    op.create_index("ix_watchlist_video", "watchlist", ["video_id"])

    # Create shares table
    op.create_table(
        "shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shares_video_id", "shares", ["video_id"])
    op.create_index("ix_shares_user_id", "shares", ["user_id"])
    op.create_index("ix_shares_video_created", "shares", ["video_id", "created_at"])

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, default=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read"])
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_shares_video_created", table_name="shares")
    op.drop_index("ix_shares_user_id", table_name="shares")
    op.drop_index("ix_shares_video_id", table_name="shares")
    op.drop_table("shares")

    op.drop_index("ix_watchlist_video", table_name="watchlist")
    op.drop_index("ix_watchlist_user_created", table_name="watchlist")
    op.drop_table("watchlist")

    op.drop_index("ix_reactions_video_type", table_name="reactions")
    op.drop_index("ix_reactions_user", table_name="reactions")
    op.drop_index("ix_reactions_video", table_name="reactions")
    op.drop_table("reactions")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS reactiontype")

    op.drop_index("ix_comment_likes_user", table_name="comment_likes")
    op.drop_index("ix_comment_likes_comment", table_name="comment_likes")
    op.drop_table("comment_likes")

    op.drop_index("ix_comments_user_created", table_name="comments")
    op.drop_index("ix_comments_video_created", table_name="comments")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_index("ix_comments_user_id", table_name="comments")
    op.drop_index("ix_comments_video_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_follows_following", table_name="follows")
    op.drop_index("ix_follows_follower", table_name="follows")
    op.drop_table("follows")
