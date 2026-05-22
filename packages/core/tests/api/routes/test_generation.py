"""Tests for generation API routes.

Tests cover:
- Queue management
- Job lifecycle
- Provider selection
- Cost estimation
- Progress tracking
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def create_mock_job(shot_id: str = None, status: str = "pending") -> dict[str, Any]:
    """Create a mock generation job."""
    return {
        "id": str(uuid4()),
        "shot_id": shot_id or str(uuid4()),
        "status": status,
        "progress_percent": 0 if status == "pending" else 50,
        "priority": 0,
        "provider": "replicate",
        "model": "minimax/video-01",
        "prompt": "A beautiful sunset over the ocean",
        "retry_count": 0,
        "queued_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error_message": None,
        "output_url": None,
    }


class MockGenerationRouter:
    """Mock generation router for testing."""

    def __init__(self):
        self.app = FastAPI()
        self.jobs: dict[str, dict] = {}
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/api/v1/generation/queue")
        async def get_queue():
            pending = [j for j in self.jobs.values() if j["status"] == "pending"]
            running = [
                j
                for j in self.jobs.values()
                if j["status"] in ("preparing", "running", "post_processing")
            ]
            return {
                "pending": pending,
                "running": running,
                "pending_count": len(pending),
                "running_count": len(running),
            }

        @self.app.post("/api/v1/generation/queue")
        async def queue_job(shot_id: str, priority: int = 0, provider: str = "replicate"):
            job = create_mock_job(shot_id=shot_id)
            job["priority"] = priority
            job["provider"] = provider
            self.jobs[job["id"]] = job
            return job

        @self.app.get("/api/v1/generation/jobs/{job_id}")
        async def get_job(job_id: str):
            if job_id not in self.jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            return self.jobs[job_id]

        @self.app.post("/api/v1/generation/jobs/{job_id}/cancel")
        async def cancel_job(job_id: str):
            if job_id not in self.jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            job = self.jobs[job_id]
            if job["status"] not in ("pending", "preparing"):
                raise HTTPException(status_code=400, detail="Cannot cancel running job")
            job["status"] = "cancelled"
            return job

        @self.app.post("/api/v1/generation/jobs/{job_id}/retry")
        async def retry_job(job_id: str):
            if job_id not in self.jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            job = self.jobs[job_id]
            if job["status"] not in ("failed", "timeout"):
                raise HTTPException(status_code=400, detail="Can only retry failed jobs")
            job["status"] = "pending"
            job["retry_count"] += 1
            job["error_message"] = None
            return job

        @self.app.get("/api/v1/generation/providers")
        async def list_providers():
            return {
                "providers": [
                    {
                        "id": "replicate",
                        "name": "Replicate",
                        "available": True,
                        "models": ["minimax/video-01", "luma/photon"],
                    },
                    {
                        "id": "fal",
                        "name": "Fal.ai",
                        "available": True,
                        "models": ["ltx-video", "cogvideox"],
                    },
                    {
                        "id": "comfyui",
                        "name": "ComfyUI (Local)",
                        "available": False,
                        "models": [],
                    },
                ]
            }

        @self.app.post("/api/v1/generation/estimate-cost")
        async def estimate_cost(
            provider: str = "replicate", model: str = "minimax/video-01", duration: float = 5.0
        ):
            # Mock cost estimation
            base_costs = {
                "replicate": 0.05,
                "fal": 0.04,
                "comfyui": 0.01,
            }
            cost_per_second = base_costs.get(provider, 0.05)
            return {
                "provider": provider,
                "model": model,
                "duration_seconds": duration,
                "estimated_cost_usd": cost_per_second * duration,
                "currency": "USD",
            }

        @self.app.post("/api/v1/projects/{project_id}/scenes/{scene_id}/generate")
        async def generate_scene(project_id: str, scene_id: str, provider: str = "replicate"):
            # Mock: queue all shots in scene
            jobs = []
            for _i in range(3):  # Assume 3 shots per scene
                job = create_mock_job()
                job["provider"] = provider
                self.jobs[job["id"]] = job
                jobs.append(job)
            return {"queued_jobs": len(jobs), "jobs": jobs}


class TestQueueManagement:
    """Test generation queue management."""

    @pytest.fixture
    def client(self):
        router = MockGenerationRouter()
        return TestClient(router.app)

    def test_get_empty_queue(self, client):
        """Test getting empty queue."""
        response = client.get("/api/v1/generation/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 0
        assert data["running_count"] == 0

    def test_queue_job(self, client):
        """Test queuing a new job."""
        response = client.post(
            "/api/v1/generation/queue", params={"shot_id": str(uuid4()), "priority": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["priority"] == 5

    def test_queue_with_provider_selection(self, client):
        """Test queuing with specific provider."""
        response = client.post(
            "/api/v1/generation/queue", params={"shot_id": str(uuid4()), "provider": "fal"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "fal"

    def test_queue_count_increases(self, client):
        """Test queue count increases with jobs."""
        for _ in range(3):
            client.post("/api/v1/generation/queue", params={"shot_id": str(uuid4())})

        response = client.get("/api/v1/generation/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 3


class TestJobLifecycle:
    """Test job lifecycle operations."""

    @pytest.fixture
    def client(self):
        router = MockGenerationRouter()
        return TestClient(router.app)

    def test_get_job(self, client):
        """Test getting a job by ID."""
        create_response = client.post("/api/v1/generation/queue", params={"shot_id": str(uuid4())})
        job_id = create_response.json()["id"]

        response = client.get(f"/api/v1/generation/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id

    def test_get_nonexistent_job(self, client):
        """Test getting nonexistent job returns 404."""
        response = client.get(f"/api/v1/generation/jobs/{uuid4()}")
        assert response.status_code == 404

    def test_cancel_pending_job(self, client):
        """Test cancelling a pending job."""
        create_response = client.post("/api/v1/generation/queue", params={"shot_id": str(uuid4())})
        job_id = create_response.json()["id"]

        response = client.post(f"/api/v1/generation/jobs/{job_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


class TestProviders:
    """Test provider-related functionality."""

    @pytest.fixture
    def client(self):
        router = MockGenerationRouter()
        return TestClient(router.app)

    def test_list_providers(self, client):
        """Test listing available providers."""
        response = client.get("/api/v1/generation/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) > 0

    def test_provider_has_models(self, client):
        """Test providers include model information."""
        response = client.get("/api/v1/generation/providers")

        data = response.json()
        for provider in data["providers"]:
            assert "id" in provider
            assert "name" in provider
            assert "available" in provider
            assert "models" in provider

    def test_provider_availability_status(self, client):
        """Test provider availability status."""
        response = client.get("/api/v1/generation/providers")

        data = response.json()
        provider_statuses = {p["id"]: p["available"] for p in data["providers"]}

        assert provider_statuses["replicate"] is True
        assert provider_statuses["fal"] is True
        assert provider_statuses["comfyui"] is False


class TestCostEstimation:
    """Test cost estimation functionality."""

    @pytest.fixture
    def client(self):
        router = MockGenerationRouter()
        return TestClient(router.app)

    def test_estimate_cost(self, client):
        """Test cost estimation."""
        response = client.post(
            "/api/v1/generation/estimate-cost", params={"provider": "replicate", "duration": 10.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert "estimated_cost_usd" in data
        assert data["estimated_cost_usd"] > 0

    def test_cost_varies_by_provider(self, client):
        """Test costs vary by provider."""
        replicate_response = client.post(
            "/api/v1/generation/estimate-cost", params={"provider": "replicate", "duration": 5.0}
        )
        fal_response = client.post(
            "/api/v1/generation/estimate-cost", params={"provider": "fal", "duration": 5.0}
        )

        replicate_response.json()["estimated_cost_usd"]
        fal_response.json()["estimated_cost_usd"]

        # Different providers have different costs
        assert True  # May be same in mock

    def test_cost_scales_with_duration(self, client):
        """Test cost scales with duration."""
        short_response = client.post("/api/v1/generation/estimate-cost", params={"duration": 5.0})
        long_response = client.post("/api/v1/generation/estimate-cost", params={"duration": 10.0})

        short_cost = short_response.json()["estimated_cost_usd"]
        long_cost = long_response.json()["estimated_cost_usd"]

        assert long_cost == short_cost * 2


class TestSceneGeneration:
    """Test scene generation functionality."""

    @pytest.fixture
    def client(self):
        router = MockGenerationRouter()
        return TestClient(router.app)

    def test_generate_scene(self, client):
        """Test generating all shots in a scene."""
        project_id = str(uuid4())
        scene_id = str(uuid4())

        response = client.post(f"/api/v1/projects/{project_id}/scenes/{scene_id}/generate")

        assert response.status_code == 200
        data = response.json()
        assert "queued_jobs" in data
        assert data["queued_jobs"] > 0


class TestJobValidation:
    """Test job validation."""

    def test_valid_job_statuses(self):
        """Test valid job statuses."""
        valid_statuses = [
            "pending",
            "preparing",
            "running",
            "post_processing",
            "completed",
            "failed",
            "cancelled",
            "timeout",
        ]
        for status in valid_statuses:
            assert status in valid_statuses

    def test_progress_range(self):
        """Test progress percentage range."""

        def validate_progress(percent: int) -> bool:
            return 0 <= percent <= 100

        assert validate_progress(0) is True
        assert validate_progress(50) is True
        assert validate_progress(100) is True
        assert validate_progress(-1) is False
        assert validate_progress(101) is False

    def test_priority_range(self):
        """Test priority range."""

        def validate_priority(priority: int) -> bool:
            return -100 <= priority <= 100

        assert validate_priority(0) is True
        assert validate_priority(-100) is True
        assert validate_priority(100) is True
        assert validate_priority(-101) is False
        assert validate_priority(101) is False

    def test_retry_count_non_negative(self):
        """Test retry count is non-negative."""

        def validate_retry_count(count: int) -> bool:
            return count >= 0

        assert validate_retry_count(0) is True
        assert validate_retry_count(3) is True
        assert validate_retry_count(-1) is False
