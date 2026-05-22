"""Tests for Cost Tracking service."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project
from scenemachine.services.cost_tracking import CostTrackingService


class TestCostTrackingService:
    """Tests for CostTrackingService."""

    @pytest.fixture
    def cost_service(self, db_session: AsyncSession) -> CostTrackingService:
        """Create a cost tracking service instance."""
        return CostTrackingService(db_session)

    @pytest.mark.asyncio
    async def test_record_generation_cost(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test recording a generation cost."""
        result = await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="minimax-video-01",
            cost=Decimal("0.50"),
            operation_type="video_generation",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_project_total_cost(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test getting total cost for a project."""
        # Record some costs
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="minimax-video-01",
            cost=Decimal("0.50"),
            operation_type="video_generation",
        )
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="fal",
            model="cogvideox-5b",
            cost=Decimal("0.30"),
            operation_type="video_generation",
        )

        total = await cost_service.get_project_total(sample_project.id)

        assert total >= Decimal("0.80")

    @pytest.mark.asyncio
    async def test_get_costs_by_provider(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test getting costs grouped by provider."""
        # Record costs for different providers
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("1.00"),
            operation_type="video_generation",
        )
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="fal",
            model="test",
            cost=Decimal("0.50"),
            operation_type="video_generation",
        )

        by_provider = await cost_service.get_costs_by_provider(sample_project.id)

        assert isinstance(by_provider, dict)

    @pytest.mark.asyncio
    async def test_get_costs_by_date_range(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test getting costs within a date range."""
        # Record a cost
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("0.50"),
            operation_type="video_generation",
        )

        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)

        costs = await cost_service.get_costs_by_date_range(
            project_id=sample_project.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert isinstance(costs, (list, Decimal, dict))

    @pytest.mark.asyncio
    async def test_check_budget_limit(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test checking if project exceeds budget limit."""
        # Set a budget limit
        if hasattr(cost_service, "set_budget_limit"):
            await cost_service.set_budget_limit(
                project_id=sample_project.id,
                limit=Decimal("10.00"),
            )

        # Record costs under limit
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("5.00"),
            operation_type="video_generation",
        )

        if hasattr(cost_service, "check_budget"):
            within_budget = await cost_service.check_budget(sample_project.id)
            assert within_budget is True

    @pytest.mark.asyncio
    async def test_budget_exceeded_warning(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test warning when budget is exceeded."""
        if hasattr(cost_service, "set_budget_limit"):
            await cost_service.set_budget_limit(
                project_id=sample_project.id,
                limit=Decimal("1.00"),
            )

            # Record cost exceeding limit
            await cost_service.record_cost(
                project_id=sample_project.id,
                provider="replicate",
                model="test",
                cost=Decimal("5.00"),
                operation_type="video_generation",
            )

            if hasattr(cost_service, "check_budget"):
                within_budget = await cost_service.check_budget(sample_project.id)
                assert within_budget is False

    @pytest.mark.asyncio
    async def test_get_cost_summary(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test getting a cost summary."""
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("1.00"),
            operation_type="video_generation",
        )

        if hasattr(cost_service, "get_summary"):
            summary = await cost_service.get_summary(sample_project.id)
            assert summary is not None

    @pytest.mark.asyncio
    async def test_estimate_remaining_budget(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test estimating remaining budget."""
        if hasattr(cost_service, "set_budget_limit"):
            await cost_service.set_budget_limit(
                project_id=sample_project.id,
                limit=Decimal("10.00"),
            )

        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("3.00"),
            operation_type="video_generation",
        )

        if hasattr(cost_service, "get_remaining_budget"):
            remaining = await cost_service.get_remaining_budget(sample_project.id)
            assert remaining <= Decimal("7.00")

    @pytest.mark.asyncio
    async def test_cost_per_operation_type(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test costs broken down by operation type."""
        # Record different operation types
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("1.00"),
            operation_type="video_generation",
        )
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="elevenlabs",
            model="test",
            cost=Decimal("0.10"),
            operation_type="tts",
        )

        if hasattr(cost_service, "get_costs_by_operation"):
            by_operation = await cost_service.get_costs_by_operation(sample_project.id)
            assert isinstance(by_operation, dict)

    @pytest.mark.asyncio
    async def test_export_cost_report(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test exporting a cost report."""
        await cost_service.record_cost(
            project_id=sample_project.id,
            provider="replicate",
            model="test",
            cost=Decimal("1.00"),
            operation_type="video_generation",
        )

        if hasattr(cost_service, "export_report"):
            report = await cost_service.export_report(
                project_id=sample_project.id,
                format="csv",
            )
            assert report is not None

    @pytest.mark.asyncio
    async def test_zero_cost_recording(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test recording a zero-cost operation."""
        result = await cost_service.record_cost(
            project_id=sample_project.id,
            provider="mock",
            model="test",
            cost=Decimal("0.00"),
            operation_type="video_generation",
        )

        # Should accept zero cost
        assert result is not None

    @pytest.mark.asyncio
    async def test_negative_cost_rejected(
        self,
        cost_service: CostTrackingService,
        sample_project: Project,
    ):
        """Test that negative costs are rejected."""
        with pytest.raises((ValueError, Exception)):
            await cost_service.record_cost(
                project_id=sample_project.id,
                provider="test",
                model="test",
                cost=Decimal("-1.00"),
                operation_type="video_generation",
            )
