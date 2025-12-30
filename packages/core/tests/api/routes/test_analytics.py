"""Tests for analytics API routes."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.routes import analytics
from scenemachine.models import Project, ProjectState
from scenemachine.services.analytics import (
    AnalyticsService,
    GenerationStats,
    CostStats,
    ProjectStats,
    PerformanceStats,
    DailyStats,
)


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(analytics.router, prefix="/api/v1/analytics")
    return app


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(
        name="Analytics Test Project",
        description="A test project for analytics tests",
        state=ProjectState.GENERATING,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestDashboardEndpoint:
    """Tests for the dashboard endpoint."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_default_range(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting dashboard stats with default time range."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Override dependency
            app.dependency_overrides = {}
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/dashboard")

            assert response.status_code == 200
            data = response.json()
            assert "totalProjects" in data
            assert "activeProjects" in data
            assert "totalScenes" in data
            assert "totalShots" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_with_time_range(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting dashboard stats with specified time range."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/dashboard?time_range=30d")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_dashboard_invalid_time_range(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting dashboard stats with invalid time range."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/dashboard?time_range=invalid")

            assert response.status_code == 422


class TestGenerationStatsEndpoint:
    """Tests for generation stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_generation_stats(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting generation statistics."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/generation-stats")

            assert response.status_code == 200
            data = response.json()
            assert "totalGenerations" in data
            assert "successRate" in data

    @pytest.mark.asyncio
    async def test_get_generation_stats_by_project(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test getting generation stats for a specific project."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get(
                f"/api/v1/analytics/generation-stats?project_id={project.id}"
            )

            assert response.status_code == 200


class TestCostStatsEndpoint:
    """Tests for cost stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_cost_stats(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting cost statistics."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/cost-stats")

            assert response.status_code == 200
            data = response.json()
            assert "totalCostUsd" in data


class TestDailyStatsEndpoint:
    """Tests for daily stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_daily_stats(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting daily statistics."""
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get(
                f"/api/v1/analytics/daily-stats?start_date={start}&end_date={end}"
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_daily_stats_missing_dates(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting daily stats without required dates."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/daily-stats")

            assert response.status_code == 422


class TestProviderUsageEndpoint:
    """Tests for provider usage endpoint."""

    @pytest.mark.asyncio
    async def test_get_provider_usage(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting provider usage statistics."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/provider-usage")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestProjectStatsEndpoint:
    """Tests for project stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_project_stats(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test getting project statistics."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get(
                f"/api/v1/analytics/project-stats/{project.id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["projectId"] == str(project.id)


class TestPerformanceStatsEndpoint:
    """Tests for performance stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_performance_stats(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting performance statistics."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/analytics/performance-stats")

            assert response.status_code == 200
            data = response.json()
            assert "averageGenerationTimeSeconds" in data
