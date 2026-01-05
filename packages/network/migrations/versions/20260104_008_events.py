"""Events tables - CoreCast, Badges, Performers Association.

Revision ID: 008
Revises: 007
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE eventstatus AS ENUM (
            'upcoming', 'submissions_open', 'voting', 'judging',
            'completed', 'cancelled'
        )
    """)

    op.execute("""
        CREATE TYPE submissionphase AS ENUM (
            'submitted', 'qualified', 'top_100', 'top_50', 'top_25',
            'top_10', 'finalist', 'winner', 'eliminated'
        )
    """)

    op.execute("""
        CREATE TYPE badgetype AS ENUM (
            'gold', 'silver', 'bronze', 'finalist', 'top_25', 'top_50',
            'top_100', 'participant', 'peoples_choice', 'rising_star',
            'innovation', 'technical', 'storytelling', 'visual',
            'emerging', 'established', 'professional', 'elite', 'legend'
        )
    """)

    op.execute("""
        CREATE TYPE votetype AS ENUM (
            'public', 'judge', 'peer'
        )
    """)

    op.execute("""
        CREATE TYPE performersassociationtier AS ENUM (
            'emerging', 'established', 'professional', 'elite', 'legend'
        )
    """)

    # =========================================================================
    # CORECAST TABLES
    # =========================================================================

    # CoreCast Events
    op.create_table(
        'corecast_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('theme', sa.String(200), nullable=True),
        sa.Column('banner_url', sa.String(500), nullable=True),
        sa.Column('month', sa.Integer, nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('status', sa.Enum('upcoming', 'submissions_open', 'voting', 'judging',
                                    'completed', 'cancelled', name='eventstatus',
                                    create_type=False), nullable=False,
                  server_default="'upcoming'"),
        sa.Column('submissions_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submissions_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('voting_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('voting_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('results_announcement', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_prize_pool', sa.Numeric(12, 2), nullable=False,
                  server_default='100000.00'),
        sa.Column('prize_distribution', postgresql.JSONB, nullable=False,
                  server_default='{}'),
        sa.Column('max_submissions_per_user', sa.Integer, nullable=False,
                  server_default='3'),
        sa.Column('min_duration_seconds', sa.Integer, nullable=False,
                  server_default='30'),
        sa.Column('max_duration_seconds', sa.Integer, nullable=False,
                  server_default='600'),
        sa.Column('requires_studio_content', sa.Boolean, nullable=False,
                  server_default='true'),
        sa.Column('submission_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('vote_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('unique_voters', sa.Integer, nullable=False, server_default='0'),
        sa.Column('sponsors', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
        sa.UniqueConstraint('month', 'year', name='uq_corecast_month_year'),
    )

    # CoreCast Submissions
    op.create_table(
        'corecast_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('corecast_events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('phase', sa.Enum('submitted', 'qualified', 'top_100', 'top_50',
                                   'top_25', 'top_10', 'finalist', 'winner', 'eliminated',
                                   name='submissionphase', create_type=False),
                  nullable=False, server_default="'submitted'"),
        sa.Column('is_qualified', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('disqualification_reason', sa.Text, nullable=True),
        sa.Column('public_votes', sa.Integer, nullable=False, server_default='0'),
        sa.Column('judge_score', sa.Float, nullable=True),
        sa.Column('peer_votes', sa.Integer, nullable=False, server_default='0'),
        sa.Column('combined_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('final_rank', sa.Integer, nullable=True),
        sa.Column('prize_amount', sa.Numeric(10, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('prize_paid', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('special_badges', postgresql.ARRAY(sa.String(50)), nullable=False,
                  server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
        sa.UniqueConstraint('event_id', 'video_id', name='uq_corecast_event_video'),
    )

    # CoreCast Votes
    op.create_table(
        'corecast_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('corecast_submissions.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('voter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vote_type', sa.Enum('public', 'judge', 'peer', name='votetype',
                                       create_type=False), nullable=False,
                  server_default="'public'"),
        sa.Column('score', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
        sa.UniqueConstraint('submission_id', 'voter_id', 'vote_type',
                           name='uq_corecast_vote_unique'),
    )

    # =========================================================================
    # BADGE TABLES
    # =========================================================================

    # User Badges
    op.create_table(
        'user_badges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('badge_type', sa.Enum('gold', 'silver', 'bronze', 'finalist',
                                        'top_25', 'top_50', 'top_100', 'participant',
                                        'peoples_choice', 'rising_star', 'innovation',
                                        'technical', 'storytelling', 'visual',
                                        'emerging', 'established', 'professional',
                                        'elite', 'legend', name='badgetype',
                                        create_type=False), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('corecast_events.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('awarded_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('is_featured', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('award_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # Prize Distributions
    op.create_table(
        'prize_distributions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('corecast_events.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('corecast_submissions.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default="'USD'"),
        sa.Column('final_rank', sa.Integer, nullable=False),
        sa.Column('badge_awarded', sa.Enum('gold', 'silver', 'bronze', 'finalist',
                                           'top_25', 'top_50', 'top_100', 'participant',
                                           'peoples_choice', 'rising_star', 'innovation',
                                           'technical', 'storytelling', 'visual',
                                           'emerging', 'established', 'professional',
                                           'elite', 'legend', name='badgetype',
                                           create_type=False), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default="'pending'"),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payment_reference', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # =========================================================================
    # PERFORMERS ASSOCIATION TABLE
    # =========================================================================

    op.create_table(
        'performers_association_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
                  unique=True),
        sa.Column('tier', sa.Enum('emerging', 'established', 'professional',
                                  'elite', 'legend',
                                  name='performersassociationtier',
                                  create_type=False), nullable=False,
                  server_default="'emerging'"),
        sa.Column('total_videos', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_views', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('total_earnings', sa.Numeric(12, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('corecast_wins', sa.Integer, nullable=False, server_default='0'),
        sa.Column('corecast_participations', sa.Integer, nullable=False,
                  server_default='0'),
        sa.Column('tier_achieved_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('previous_tier', sa.Enum('emerging', 'established', 'professional',
                                           'elite', 'legend',
                                           name='performersassociationtier',
                                           create_type=False), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suspension_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # =========================================================================
    # INDEXES
    # =========================================================================

    # CoreCast indexes
    op.create_index('ix_corecast_events_status', 'corecast_events', ['status'])
    op.create_index('ix_corecast_events_dates', 'corecast_events',
                    ['submissions_start', 'voting_end'])
    op.create_index('ix_corecast_submissions_scores', 'corecast_submissions',
                    ['combined_score', 'public_votes'])
    op.create_index('ix_corecast_submissions_phase', 'corecast_submissions',
                    ['event_id', 'phase'])
    op.create_index('ix_corecast_submissions_creator', 'corecast_submissions',
                    ['creator_id'])
    op.create_index('ix_corecast_votes_submission', 'corecast_votes',
                    ['submission_id'])

    # Badge indexes
    op.create_index('ix_user_badges_user', 'user_badges', ['user_id', 'badge_type'])
    op.create_index('ix_user_badges_featured', 'user_badges',
                    ['user_id', 'is_featured'])
    op.create_index('ix_prize_distributions_event', 'prize_distributions',
                    ['event_id', 'final_rank'])

    # Performers Association indexes
    op.create_index('ix_performers_association_tier', 'performers_association_memberships',
                    ['tier', 'is_active'])
    op.create_index('ix_performers_association_earnings', 'performers_association_memberships',
                    ['total_earnings'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_performers_association_earnings')
    op.drop_index('ix_performers_association_tier')
    op.drop_index('ix_prize_distributions_event')
    op.drop_index('ix_user_badges_featured')
    op.drop_index('ix_user_badges_user')
    op.drop_index('ix_corecast_votes_submission')
    op.drop_index('ix_corecast_submissions_creator')
    op.drop_index('ix_corecast_submissions_phase')
    op.drop_index('ix_corecast_submissions_scores')
    op.drop_index('ix_corecast_events_dates')
    op.drop_index('ix_corecast_events_status')

    # Drop tables
    op.drop_table('performers_association_memberships')
    op.drop_table('prize_distributions')
    op.drop_table('user_badges')
    op.drop_table('corecast_votes')
    op.drop_table('corecast_submissions')
    op.drop_table('corecast_events')

    # Drop enum types
    op.execute('DROP TYPE performersassociationtier')
    op.execute('DROP TYPE votetype')
    op.execute('DROP TYPE badgetype')
    op.execute('DROP TYPE submissionphase')
    op.execute('DROP TYPE eventstatus')
