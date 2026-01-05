"""
Pydantic schemas for analytics service.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Creator dashboard summary."""

    # Overview
    total_videos: int
    total_views: int
    total_watch_time_hours: float
    total_subscribers: int
    subscriber_change_30d: int

    # Revenue
    total_revenue_30d: Decimal
    revenue_change_percent: float
    estimated_revenue_mtd: Decimal

    # Engagement
    average_watch_percent: float
    average_ctr: float  # Click-through rate
    like_rate: float

    # Top performing
    top_video_id: Optional[uuid.UUID]
    top_video_title: Optional[str]
    top_video_views_30d: int


class VideoAnalytics(BaseModel):
    """Analytics for a single video."""

    video_id: uuid.UUID
    title: str
    thumbnail_url: Optional[str]

    # Views
    total_views: int
    views_30d: int
    views_7d: int
    views_today: int

    # Watch time
    total_watch_time_hours: float
    average_view_duration_seconds: float
    average_view_percent: float

    # Engagement
    like_count: int
    dislike_count: int
    comment_count: int
    share_count: int
    like_rate: float

    # Audience retention
    retention_curve: list[float]  # Percentage at each 10% mark

    # Traffic sources
    traffic_sources: dict[str, float]  # source -> percentage

    # Demographics
    age_distribution: dict[str, float]
    gender_distribution: dict[str, float]
    top_countries: list[dict]  # [{country_code, views, percent}]

    # Device breakdown
    device_distribution: dict[str, float]

    # Revenue
    revenue_30d: Decimal
    rpm: Decimal  # Revenue per mille (1000 views)


class VideoAnalyticsListResponse(BaseModel):
    """List of video analytics."""

    videos: list[VideoAnalytics]
    total: int
    page: int
    per_page: int


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""

    date: date
    value: float


class TimeSeriesResponse(BaseModel):
    """Time series data response."""

    metric: str
    period: str
    data: list[TimeSeriesDataPoint]
    total: float
    average: float
    change_percent: float


class AudienceInsights(BaseModel):
    """Audience demographic insights."""

    # Age groups
    age_13_17: float
    age_18_24: float
    age_25_34: float
    age_35_44: float
    age_45_54: float
    age_55_plus: float

    # Gender
    male: float
    female: float
    other: float

    # Top locations
    top_countries: list[dict]
    top_cities: list[dict]

    # Viewing time
    peak_viewing_hours: list[int]  # Hours in UTC
    peak_viewing_days: list[str]  # Day names

    # Subscriber info
    new_subscribers_30d: int
    returning_viewers_percent: float
    subscriber_views_percent: float


class RealTimeMetrics(BaseModel):
    """Real-time streaming metrics."""

    current_viewers: int
    views_last_hour: int
    views_last_48_hours: int

    # Active videos
    active_videos: list[dict]  # [{video_id, title, current_viewers}]

    # Recent activity
    recent_comments: int
    recent_likes: int
    recent_subscribers: int


class ContentPerformanceResponse(BaseModel):
    """Content performance overview."""

    # Video performance tiers
    top_performers: list[dict]  # Top 10%
    average_performers: list[dict]  # Middle 80%
    underperformers: list[dict]  # Bottom 10%

    # Content type breakdown
    by_content_type: dict[str, dict]  # type -> {count, views, revenue}

    # Optimal patterns
    optimal_video_length: str  # "5-10 minutes"
    optimal_publish_time: str  # "Tuesday 3-5 PM"
    best_thumbnail_style: str  # Based on CTR analysis


class RevenueAnalytics(BaseModel):
    """Revenue analytics."""

    # Summary
    total_revenue: Decimal
    revenue_change_percent: float

    # Breakdown
    ad_revenue: Decimal
    ticket_revenue: Decimal
    tip_revenue: Decimal
    subscription_revenue: Decimal

    # Per-video metrics
    average_rpm: Decimal  # Revenue per mille
    highest_rpm_video: Optional[uuid.UUID]
    lowest_rpm_video: Optional[uuid.UUID]

    # Trends
    revenue_by_day: list[TimeSeriesDataPoint]
    revenue_by_source: dict[str, Decimal]

    # Predictions
    estimated_monthly_revenue: Decimal
    projected_annual_revenue: Decimal


class NotificationPreferences(BaseModel):
    """Creator notification preferences."""

    email_new_subscriber: bool = True
    email_milestone_reached: bool = True
    email_weekly_summary: bool = True
    email_revenue_payout: bool = True

    push_new_comment: bool = True
    push_new_subscriber: bool = False
    push_video_milestone: bool = True
    push_tip_received: bool = True

    alert_threshold_views: int = 1000
    alert_threshold_subscribers: int = 100
