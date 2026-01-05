"""Distribution tables - StoryHeaven, MovieHeaven, Festivals, Exports.

Revision ID: 007
Revises: 006
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE distributionchannel AS ENUM (
            'story_heaven', 'movie_heaven'
        )
    """)

    op.execute("""
        CREATE TYPE contentformat AS ENUM (
            '9:16', '1:1', '16:9', '2.35:1', '1.43:1'
        )
    """)

    op.execute("""
        CREATE TYPE ppvstatus AS ENUM (
            'pending', 'completed', 'refunded', 'expired'
        )
    """)

    op.execute("""
        CREATE TYPE subscriptiontier AS ENUM (
            'basic', 'premium', 'ultimate'
        )
    """)

    op.execute("""
        CREATE TYPE festivalstatus AS ENUM (
            'upcoming', 'submissions_open', 'submissions_closed',
            'judging', 'completed'
        )
    """)

    op.execute("""
        CREATE TYPE submissionstatus AS ENUM (
            'submitted', 'under_review', 'selected', 'finalist',
            'winner', 'rejected'
        )
    """)

    op.execute("""
        CREATE TYPE premieretype AS ENUM (
            'world_premiere', 'exclusive_preview', 'live_premiere',
            'festival_premiere'
        )
    """)

    # =========================================================================
    # STORYHEAVEN TABLES
    # =========================================================================

    # StoryHeaven Sounds (must be created before posts for FK)
    op.create_table(
        'story_heaven_sounds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('original_video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='SET NULL'), nullable=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('artist', sa.String(200), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=False),
        sa.Column('audio_url', sa.String(500), nullable=False),
        sa.Column('usage_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_trending', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # StoryHeaven Posts
    op.create_table(
        'story_heaven_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False,
                  unique=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('format', sa.Enum('9:16', '1:1', '16:9', '2.35:1', '1.43:1',
                                    name='contentformat', create_type=False),
                  nullable=False, server_default="'9:16'"),
        sa.Column('optimized_for_mobile', sa.Boolean, nullable=False,
                  server_default='true'),
        sa.Column('original_sound_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('story_heaven_sounds.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('uses_trending_sound', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('view_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('like_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('share_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('duet_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('save_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('hashtags', postgresql.ARRAY(sa.String(100)), nullable=False,
                  server_default='{}'),
        sa.Column('trending_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('featured_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('viral_threshold_reached', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('viral_reached_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('allow_duets', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('allow_sound_reuse', sa.Boolean, nullable=False,
                  server_default='true'),
        sa.Column('allow_comments', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # StoryHeaven Duets
    op.create_table(
        'story_heaven_duets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('original_post_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('story_heaven_posts.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('response_post_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('story_heaven_posts.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # =========================================================================
    # MOVIEHEAVEN TABLES
    # =========================================================================

    # MovieHeaven Content
    op.create_table(
        'movie_heaven_content',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False,
                  unique=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('format', sa.Enum('9:16', '1:1', '16:9', '2.35:1', '1.43:1',
                                    name='contentformat', create_type=False),
                  nullable=False, server_default="'16:9'"),
        sa.Column('is_feature_film', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('runtime_minutes', sa.Integer, nullable=False),
        sa.Column('ppv_price', sa.Numeric(8, 2), nullable=True),
        sa.Column('rental_price', sa.Numeric(8, 2), nullable=True),
        sa.Column('rental_duration_hours', sa.Integer, nullable=False,
                  server_default='48'),
        sa.Column('minimum_tier', sa.Enum('basic', 'premium', 'ultimate',
                                          name='subscriptiontier', create_type=False),
                  nullable=True),
        sa.Column('is_free', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('premiere_type', sa.Enum('world_premiere', 'exclusive_preview',
                                           'live_premiere', 'festival_premiere',
                                           name='premieretype', create_type=False),
                  nullable=True),
        sa.Column('premiere_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('premiere_ended', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('festival_circuit_enabled', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('festival_wins', sa.Integer, nullable=False, server_default='0'),
        sa.Column('festival_nominations', sa.Integer, nullable=False,
                  server_default='0'),
        sa.Column('total_ppv_revenue', sa.Numeric(12, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('total_rental_revenue', sa.Numeric(12, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('total_purchases', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_rentals', sa.Integer, nullable=False, server_default='0'),
        sa.Column('available_qualities', postgresql.ARRAY(sa.String(20)),
                  nullable=False, server_default="'{}'"),
        sa.Column('has_4k', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('has_hdr', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('has_dolby_atmos', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('critic_score', sa.Float, nullable=True),
        sa.Column('audience_score', sa.Float, nullable=True),
        sa.Column('review_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('genres', postgresql.ARRAY(sa.String(50)), nullable=False,
                  server_default='{}'),
        sa.Column('cast_names', postgresql.ARRAY(sa.String(100)), nullable=False,
                  server_default='{}'),
        sa.Column('crew_credits', postgresql.JSONB, nullable=False,
                  server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # PPV Purchases
    op.create_table(
        'ppv_purchases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('movie_heaven_content.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('is_rental', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('price_paid', sa.Numeric(8, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default="'USD'"),
        sa.Column('status', sa.Enum('pending', 'completed', 'refunded', 'expired',
                                    name='ppvstatus', create_type=False),
                  nullable=False, server_default="'completed'"),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # MovieHeaven Subscriptions
    op.create_table(
        'movie_heaven_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
                  unique=True),
        sa.Column('tier', sa.Enum('basic', 'premium', 'ultimate',
                                  name='subscriptiontier', create_type=False),
                  nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('monthly_price', sa.Numeric(8, 2), nullable=False),
        sa.Column('billing_cycle_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_billing_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=True),
        sa.Column('stripe_customer_id', sa.String(100), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # =========================================================================
    # FILM FESTIVAL TABLES
    # =========================================================================

    # Film Festivals
    op.create_table(
        'film_festivals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('website_url', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('upcoming', 'submissions_open', 'submissions_closed',
                                    'judging', 'completed', name='festivalstatus',
                                    create_type=False), nullable=False,
                  server_default="'upcoming'"),
        sa.Column('submission_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submission_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submission_fee', sa.Numeric(8, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('max_runtime_minutes', sa.Integer, nullable=True),
        sa.Column('min_runtime_minutes', sa.Integer, nullable=True),
        sa.Column('accepted_genres', postgresql.ARRAY(sa.String(50)), nullable=False,
                  server_default='{}'),
        sa.Column('requires_studio_content', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('grand_prize_amount', sa.Numeric(10, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('total_prize_pool', sa.Numeric(10, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('prize_breakdown', postgresql.JSONB, nullable=False,
                  server_default='{}'),
        sa.Column('submission_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # Festival Submissions
    op.create_table(
        'festival_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('festival_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('film_festivals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('movie_heaven_content.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('submitter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('submitted', 'under_review', 'selected', 'finalist',
                                    'winner', 'rejected', name='submissionstatus',
                                    create_type=False), nullable=False,
                  server_default="'submitted'"),
        sa.Column('fee_paid', sa.Numeric(8, 2), nullable=False, server_default='0.00'),
        sa.Column('director_statement', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('judge_scores', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('average_score', sa.Float, nullable=True),
        sa.Column('judge_notes', sa.Text, nullable=True),
        sa.Column('award_received', sa.String(200), nullable=True),
        sa.Column('prize_amount', sa.Numeric(10, 2), nullable=False,
                  server_default='0.00'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # =========================================================================
    # STUDIO EXPORT TABLE
    # =========================================================================

    op.create_table(
        'studio_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('studio_project_id', sa.String(36), nullable=False),
        sa.Column('studio_user_id', sa.String(36), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('videos.id', ondelete='SET NULL'), nullable=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.Enum('story_heaven', 'movie_heaven',
                                     name='distributionchannel', create_type=False),
                  nullable=False),
        sa.Column('original_format', sa.String(20), nullable=False),
        sa.Column('exported_formats', postgresql.ARRAY(sa.String(20)), nullable=False,
                  server_default='{}'),
        sa.Column('duration_seconds', sa.Integer, nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger, nullable=False),
        sa.Column('auto_formatted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('format_adjustments', postgresql.JSONB, nullable=False,
                  server_default='{}'),
        sa.Column('export_completed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('published', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'),
                  nullable=False),
    )

    # =========================================================================
    # INDEXES
    # =========================================================================

    # StoryHeaven indexes
    op.create_index('ix_story_heaven_posts_trending', 'story_heaven_posts',
                    ['trending_score'])
    op.create_index('ix_story_heaven_posts_created', 'story_heaven_posts',
                    ['created_at'])
    op.create_index('ix_story_heaven_posts_viral', 'story_heaven_posts',
                    ['viral_threshold_reached', 'viral_reached_at'])
    op.create_index('ix_story_heaven_posts_creator', 'story_heaven_posts',
                    ['creator_id'])
    op.create_index('ix_story_heaven_sounds_trending', 'story_heaven_sounds',
                    ['is_trending', 'usage_count'])
    op.create_index('ix_story_heaven_duets_original', 'story_heaven_duets',
                    ['original_post_id'])

    # MovieHeaven indexes
    op.create_index('ix_movie_heaven_content_premiere', 'movie_heaven_content',
                    ['premiere_date'])
    op.create_index('ix_movie_heaven_content_revenue', 'movie_heaven_content',
                    ['total_ppv_revenue'])
    op.create_index('ix_movie_heaven_content_scores', 'movie_heaven_content',
                    ['audience_score', 'critic_score'])
    op.create_index('ix_movie_heaven_content_creator', 'movie_heaven_content',
                    ['creator_id'])
    op.create_index('ix_ppv_purchases_user_content', 'ppv_purchases',
                    ['user_id', 'content_id'])
    op.create_index('ix_ppv_purchases_expires', 'ppv_purchases', ['expires_at'])
    op.create_index('ix_movie_heaven_subs_active', 'movie_heaven_subscriptions',
                    ['is_active', 'tier'])

    # Festival indexes
    op.create_index('ix_film_festivals_status', 'film_festivals', ['status', 'event_start'])
    op.create_index('ix_festival_submissions_festival_status', 'festival_submissions',
                    ['festival_id', 'status'])
    op.create_index('ix_festival_submissions_content', 'festival_submissions',
                    ['content_id'])

    # Export indexes
    op.create_index('ix_studio_exports_project', 'studio_exports', ['studio_project_id'])
    op.create_index('ix_studio_exports_channel', 'studio_exports', ['channel', 'published'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_studio_exports_channel')
    op.drop_index('ix_studio_exports_project')
    op.drop_index('ix_festival_submissions_content')
    op.drop_index('ix_festival_submissions_festival_status')
    op.drop_index('ix_film_festivals_status')
    op.drop_index('ix_movie_heaven_subs_active')
    op.drop_index('ix_ppv_purchases_expires')
    op.drop_index('ix_ppv_purchases_user_content')
    op.drop_index('ix_movie_heaven_content_creator')
    op.drop_index('ix_movie_heaven_content_scores')
    op.drop_index('ix_movie_heaven_content_revenue')
    op.drop_index('ix_movie_heaven_content_premiere')
    op.drop_index('ix_story_heaven_duets_original')
    op.drop_index('ix_story_heaven_sounds_trending')
    op.drop_index('ix_story_heaven_posts_creator')
    op.drop_index('ix_story_heaven_posts_viral')
    op.drop_index('ix_story_heaven_posts_created')
    op.drop_index('ix_story_heaven_posts_trending')

    # Drop tables
    op.drop_table('studio_exports')
    op.drop_table('festival_submissions')
    op.drop_table('film_festivals')
    op.drop_table('movie_heaven_subscriptions')
    op.drop_table('ppv_purchases')
    op.drop_table('movie_heaven_content')
    op.drop_table('story_heaven_duets')
    op.drop_table('story_heaven_posts')
    op.drop_table('story_heaven_sounds')

    # Drop enum types
    op.execute('DROP TYPE premieretype')
    op.execute('DROP TYPE submissionstatus')
    op.execute('DROP TYPE festivalstatus')
    op.execute('DROP TYPE subscriptiontier')
    op.execute('DROP TYPE ppvstatus')
    op.execute('DROP TYPE contentformat')
    op.execute('DROP TYPE distributionchannel')
