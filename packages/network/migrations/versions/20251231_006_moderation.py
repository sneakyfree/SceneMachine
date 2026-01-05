"""Moderation tables - reports, actions, strikes, appeals, flags.

Revision ID: 006
Revises: 005
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE reportreason AS ENUM (
            'spam', 'harassment', 'hate_speech', 'violence',
            'sexual_content', 'child_safety', 'misinformation',
            'copyright', 'impersonation', 'scam', 'self_harm',
            'terrorism', 'other'
        )
    """)

    op.execute("""
        CREATE TYPE reportstatus AS ENUM (
            'pending', 'under_review', 'resolved_valid',
            'resolved_invalid', 'resolved_no_action'
        )
    """)

    op.execute("""
        CREATE TYPE reporttargettype AS ENUM (
            'video', 'comment', 'user', 'channel'
        )
    """)

    op.execute("""
        CREATE TYPE actiontype AS ENUM (
            'warning', 'content_remove', 'age_restrict',
            'monetization_suspend', 'channel_suspend',
            'temp_ban', 'perm_ban'
        )
    """)

    op.execute("""
        CREATE TYPE appealstatus AS ENUM (
            'pending', 'under_review', 'approved',
            'denied', 'partial'
        )
    """)

    op.execute("""
        CREATE TYPE flagcategory AS ENUM (
            'violence', 'nudity', 'hate_speech', 'self_harm',
            'child_safety', 'spam', 'scam', 'copyright',
            'misinformation', 'other'
        )
    """)

    op.execute("""
        CREATE TYPE flagseverity AS ENUM (
            'low', 'medium', 'high', 'critical'
        )
    """)

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_type', sa.Enum('video', 'comment', 'user', 'channel',
                                         name='reporttargettype', create_type=False),
                  nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.Enum('spam', 'harassment', 'hate_speech', 'violence',
                                    'sexual_content', 'child_safety', 'misinformation',
                                    'copyright', 'impersonation', 'scam', 'self_harm',
                                    'terrorism', 'other', name='reportreason',
                                    create_type=False), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('timestamp_seconds', sa.Integer, nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default='5'),
        sa.Column('status', sa.Enum('pending', 'under_review', 'resolved_valid',
                                    'resolved_invalid', 'resolved_no_action',
                                    name='reportstatus', create_type=False),
                  nullable=False, server_default='pending'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # Create moderation_actions table
    op.create_table(
        'moderation_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('moderator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_type', sa.Enum('warning', 'content_remove', 'age_restrict',
                                         'monetization_suspend', 'channel_suspend',
                                         'temp_ban', 'perm_ban', name='actiontype',
                                         create_type=False), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='SET NULL'), nullable=True),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('comments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('reports.id', ondelete='SET NULL'), nullable=True),
        sa.Column('duration_hours', sa.Integer, nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Create strikes table
    op.create_table(
        'strikes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('moderation_actions.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Create appeals table
    op.create_table(
        'appeals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('moderation_actions.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('strike_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strikes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('evidence', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('pending', 'under_review', 'approved',
                                    'denied', 'partial', name='appealstatus',
                                    create_type=False), nullable=False,
                  server_default='pending'),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Create content_flags table
    op.create_table(
        'content_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=True),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('category', sa.Enum('violence', 'nudity', 'hate_speech', 'self_harm',
                                      'child_safety', 'spam', 'scam', 'copyright',
                                      'misinformation', 'other', name='flagcategory',
                                      create_type=False), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical',
                                      name='flagseverity', create_type=False),
                  nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('detection_model', sa.String(100), nullable=True),
        sa.Column('detection_details', postgresql.JSONB, nullable=True),
        sa.Column('timestamp_seconds', sa.Integer, nullable=True),
        sa.Column('auto_action_taken', sa.String(100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('is_accurate', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Add suspension fields to users if not exist
    op.add_column('users', sa.Column('is_suspended', sa.Boolean,
                                     server_default='false', nullable=False))
    op.add_column('users', sa.Column('is_terminated', sa.Boolean,
                                     server_default='false', nullable=False))
    op.add_column('users', sa.Column('suspended_until',
                                     sa.DateTime(timezone=True), nullable=True))

    # Add is_deleted to comments if not exist
    op.add_column('comments', sa.Column('is_deleted', sa.Boolean,
                                        server_default='false', nullable=False))

    # Create indexes
    op.create_index('ix_reports_status', 'reports', ['status'])
    op.create_index('ix_reports_priority_created', 'reports', ['priority', 'created_at'])
    op.create_index('ix_reports_target', 'reports', ['target_type', 'target_id'])
    op.create_index('ix_reports_reporter', 'reports', ['reporter_id'])

    op.create_index('ix_moderation_actions_target_user', 'moderation_actions',
                    ['target_user_id'])
    op.create_index('ix_moderation_actions_type', 'moderation_actions', ['action_type'])

    op.create_index('ix_strikes_user_active', 'strikes', ['user_id', 'is_active'])

    op.create_index('ix_appeals_status', 'appeals', ['status'])
    op.create_index('ix_appeals_user', 'appeals', ['user_id'])

    op.create_index('ix_content_flags_reviewed', 'content_flags', ['reviewed_at'])
    op.create_index('ix_content_flags_severity', 'content_flags', ['severity'])
    op.create_index('ix_content_flags_video', 'content_flags', ['video_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_content_flags_video')
    op.drop_index('ix_content_flags_severity')
    op.drop_index('ix_content_flags_reviewed')
    op.drop_index('ix_appeals_user')
    op.drop_index('ix_appeals_status')
    op.drop_index('ix_strikes_user_active')
    op.drop_index('ix_moderation_actions_type')
    op.drop_index('ix_moderation_actions_target_user')
    op.drop_index('ix_reports_reporter')
    op.drop_index('ix_reports_target')
    op.drop_index('ix_reports_priority_created')
    op.drop_index('ix_reports_status')

    # Drop columns from users
    op.drop_column('users', 'suspended_until')
    op.drop_column('users', 'is_terminated')
    op.drop_column('users', 'is_suspended')

    # Drop columns from comments
    op.drop_column('comments', 'is_deleted')

    # Drop tables
    op.drop_table('content_flags')
    op.drop_table('appeals')
    op.drop_table('strikes')
    op.drop_table('moderation_actions')
    op.drop_table('reports')

    # Drop enum types
    op.execute('DROP TYPE flagseverity')
    op.execute('DROP TYPE flagcategory')
    op.execute('DROP TYPE appealstatus')
    op.execute('DROP TYPE actiontype')
    op.execute('DROP TYPE reporttargettype')
    op.execute('DROP TYPE reportstatus')
    op.execute('DROP TYPE reportreason')
