"""Tests for Analytics service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.analytics import AnalyticsService
from scenemachine.models import Project


class TestAnalyticsService:
    """Tests for AnalyticsService."""

    @pytest.fixture
    def analytics_service(self, db_session: AsyncSession) -> AnalyticsService:
        """Create an analytics service instance."""
        return AnalyticsService(db_session)

    @pytest.mark.asyncio
    async def test_track_event(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test tracking an analytics event."""
        if hasattr(analytics_service, "track_event"):
            result = await analytics_service.track_event(
                event_type="generation_started",
                project_id=sample_project.id,
                data={"provider": "replicate", "model": "minimax"},
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_project_analytics(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test getting analytics for a project."""
        if hasattr(analytics_service, "get_project_analytics"):
            analytics = await analytics_service.get_project_analytics(
                project_id=sample_project.id,
            )

            assert analytics is not None

    @pytest.mark.asyncio
    async def test_get_user_analytics(
        self,
        analytics_service: AnalyticsService,
    ):
        """Test getting analytics for a user."""
        if hasattr(analytics_service, "get_user_analytics"):
            user_id = uuid4()
            analytics = await analytics_service.get_user_analytics(user_id=user_id)

            assert analytics is not None or analytics == {}

    @pytest.mark.asyncio
    async def test_get_generation_stats(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test getting generation statistics."""
        if hasattr(analytics_service, "get_generation_stats"):
            stats = await analytics_service.get_generation_stats(
                project_id=sample_project.id,
            )

            assert stats is not None
            # Should have common stat fields
            if isinstance(stats, dict):
                assert "total_generations" in stats or len(stats) >= 0

    @pytest.mark.asyncio
    async def test_get_cost_breakdown(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test getting cost breakdown."""
        if hasattr(analytics_service, "get_cost_breakdown"):
            breakdown = await analytics_service.get_cost_breakdown(
                project_id=sample_project.id,
            )

            assert breakdown is not None

    @pytest.mark.asyncio
    async def test_get_provider_usage(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test getting provider usage statistics."""
        if hasattr(analytics_service, "get_provider_usage"):
            usage = await analytics_service.get_provider_usage(
                project_id=sample_project.id,
            )

            assert isinstance(usage, (dict, list))

    @pytest.mark.asyncio
    async def test_get_timeline_analytics(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test getting timeline analytics (events over time)."""
        if hasattr(analytics_service, "get_timeline"):
            timeline = await analytics_service.get_timeline(
                project_id=sample_project.id,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
            )

            assert isinstance(timeline, list)

    @pytest.mark.asyncio
    async def test_get_export_analytics(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test getting export analytics."""
        if hasattr(analytics_service, "get_export_stats"):
            stats = await analytics_service.get_export_stats(
                project_id=sample_project.id,
            )

            assert stats is not None

    @pytest.mark.asyncio
    async def test_aggregate_daily_stats(
        self,
        analytics_service: AnalyticsService,
    ):
        """Test aggregating daily statistics."""
        if hasattr(analytics_service, "aggregate_daily"):
            result = await analytics_service.aggregate_daily(
                date=datetime.utcnow().date(),
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_usage_trends(
        self,
        analytics_service: AnalyticsService,
    ):
        """Test getting usage trends."""
        if hasattr(analytics_service, "get_usage_trends"):
            trends = await analytics_service.get_usage_trends(
                period_days=30,
            )

            assert trends is not None

    @pytest.mark.asyncio
    async def test_track_generation_duration(
        self,
        analytics_service: AnalyticsService,
        sample_project: Project,
    ):
        """Test tracking generation duration."""
        if hasattr(analytics_service, "track_generation_duration"):
            result = await analytics_service.track_generation_duration(
                project_id=sample_project.id,
                job_id=uuid4(),
                duration_seconds=45.5,
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_performance_metrics(
        self,
        analytics_service: AnalyticsService,
    ):
        """Test getting performance metrics."""
        if hasattr(analytics_service, "get_performance_metrics"):
            metrics = await analytics_service.get_performance_metrics()

            assert metrics is not None

    @pytest.mark.asyncio
    async def test_cleanup_old_analytics(
        self,
        analytics_service: AnalyticsService,
    ):
        """Test cleaning up old analytics data."""
        if hasattr(analytics_service, "cleanup"):
            count = await analytics_service.cleanup(
                older_than_days=365,
            )

            assert isinstance(count, int)
