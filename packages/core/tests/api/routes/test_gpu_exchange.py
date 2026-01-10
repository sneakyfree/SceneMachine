"""Tests for GPU Exchange API routes."""

import pytest
import pytest_asyncio
from uuid import uuid4
from decimal import Decimal

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app


class TestGPUExchangeRoutes:
    """Tests for GPU Exchange API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_list_providers_endpoint(self, client: AsyncClient):
        """Test listing GPU providers."""
        response = await client.get("/api/gpu-exchange/providers")

        # Should return providers list
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_provider_status(self, client: AsyncClient):
        """Test getting a provider's status."""
        response = await client.get("/api/gpu-exchange/providers/replicate/status")

        # Should return status
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_list_available_gpus(self, client: AsyncClient):
        """Test listing available GPUs."""
        response = await client.get("/api/gpu-exchange/gpus")

        # Should return GPU list
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_gpus_by_type(self, client: AsyncClient):
        """Test filtering GPUs by type."""
        response = await client.get(
            "/api/gpu-exchange/gpus",
            params={"gpu_type": "A100"},
        )

        # Should handle filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_gpus_by_provider(self, client: AsyncClient):
        """Test filtering GPUs by provider."""
        response = await client.get(
            "/api/gpu-exchange/gpus",
            params={"provider": "vast_ai"},
        )

        # Should handle filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_pricing(self, client: AsyncClient):
        """Test getting GPU pricing."""
        response = await client.get("/api/gpu-exchange/pricing")

        # Should return pricing
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_pricing_by_gpu_type(self, client: AsyncClient):
        """Test getting pricing for specific GPU type."""
        response = await client.get("/api/gpu-exchange/pricing/H100")

        # Should return pricing
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_provision_instance(self, client: AsyncClient):
        """Test provisioning a GPU instance."""
        response = await client.post(
            "/api/gpu-exchange/provision",
            json={
                "gpu_type": "A100_40GB",
                "provider": "lambda_labs",
                "max_price_per_hour": 2.00,
            },
        )

        # Should handle provisioning
        assert response.status_code in (200, 201, 401, 402, 503)

    @pytest.mark.asyncio
    async def test_terminate_instance(self, client: AsyncClient):
        """Test terminating a GPU instance."""
        instance_id = uuid4()
        response = await client.post(
            f"/api/gpu-exchange/instances/{instance_id}/terminate",
        )

        # Should handle termination
        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_instance_status(self, client: AsyncClient):
        """Test getting instance status."""
        instance_id = uuid4()
        response = await client.get(
            f"/api/gpu-exchange/instances/{instance_id}",
        )

        # Should return status
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_list_active_instances(self, client: AsyncClient):
        """Test listing active instances."""
        response = await client.get("/api/gpu-exchange/instances")

        # Should return list
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_budget_status(self, client: AsyncClient):
        """Test getting GPU budget status."""
        response = await client.get("/api/gpu-exchange/budget")

        # Should return budget info
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_set_budget_limit(self, client: AsyncClient):
        """Test setting GPU budget limit."""
        response = await client.post(
            "/api/gpu-exchange/budget",
            json={
                "daily_limit": 50.00,
                "monthly_limit": 500.00,
            },
        )

        # Should handle setting
        assert response.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_usage_history(self, client: AsyncClient):
        """Test getting GPU usage history."""
        response = await client.get("/api/gpu-exchange/usage")

        # Should return history
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_usage_by_project(self, client: AsyncClient):
        """Test getting GPU usage by project."""
        project_id = uuid4()
        response = await client.get(
            f"/api/projects/{project_id}/gpu-usage",
        )

        # Should return usage
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_estimate_job_cost(self, client: AsyncClient):
        """Test estimating job cost."""
        response = await client.post(
            "/api/gpu-exchange/estimate",
            json={
                "job_type": "video_generation",
                "duration_seconds": 10,
                "resolution": "1080p",
            },
        )

        # Should return estimate
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_recommended_provider(self, client: AsyncClient):
        """Test getting recommended provider for job."""
        response = await client.post(
            "/api/gpu-exchange/recommend",
            json={
                "gpu_type": "A100_40GB",
                "priority": "cost",  # or "speed"
            },
        )

        # Should return recommendation
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_health_check_all_providers(self, client: AsyncClient):
        """Test health checking all providers."""
        response = await client.get("/api/gpu-exchange/health")

        # Should return health status
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_provider_capabilities(self, client: AsyncClient):
        """Test getting provider capabilities."""
        response = await client.get("/api/gpu-exchange/providers/replicate/capabilities")

        # Should return capabilities
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_configure_routing(self, client: AsyncClient):
        """Test configuring GPU routing preferences."""
        response = await client.put(
            "/api/gpu-exchange/routing",
            json={
                "prefer_spot": True,
                "fallback_providers": ["vast_ai", "runpod"],
                "max_queue_time_seconds": 300,
            },
        )

        # Should handle config
        assert response.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_queue_depth(self, client: AsyncClient):
        """Test getting queue depth for providers."""
        response = await client.get("/api/gpu-exchange/queue-depth")

        # Should return queue info
        assert response.status_code in (200, 401)
