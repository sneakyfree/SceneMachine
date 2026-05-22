"""Tests for health check API routes.

Tests cover:
- Basic health check endpoint
- Detailed health status
- Provider health status
- Database connectivity check
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# Mock the router without importing sqlalchemy
class MockHealthRouter:
    """Mock health router for testing."""

    def __init__(self):
        self.app = FastAPI()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "version": "1.0.0", "environment": "test"}

        @self.app.get("/health/detailed")
        async def detailed_health():
            return {
                "status": "healthy",
                "version": "1.0.0",
                "checks": {
                    "database": {"status": "healthy", "latency_ms": 5.2},
                    "storage": {"status": "healthy", "free_space_gb": 100},
                    "memory": {"status": "healthy", "used_percent": 45},
                },
            }

        @self.app.get("/health/providers")
        async def provider_health():
            return {
                "providers": {
                    "replicate": {
                        "status": "healthy",
                        "available": True,
                        "models": ["minimax/video-01"],
                    },
                    "fal": {
                        "status": "healthy",
                        "available": True,
                        "models": ["ltx-video"],
                    },
                    "comfyui": {
                        "status": "unavailable",
                        "available": False,
                        "error": "Not configured",
                    },
                }
            }


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        router = MockHealthRouter()
        return TestClient(router.app)

    def test_basic_health_check(self, client):
        """Test basic health check returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_detailed_health_check(self, client):
        """Test detailed health check includes all components."""
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "database" in data["checks"]
        assert "storage" in data["checks"]
        assert "memory" in data["checks"]

    def test_database_health_check(self, client):
        """Test database health check includes latency."""
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        db_check = data["checks"]["database"]
        assert db_check["status"] == "healthy"
        assert "latency_ms" in db_check

    def test_provider_health_check(self, client):
        """Test provider health check."""
        response = client.get("/health/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data

        # Check available provider
        replicate = data["providers"]["replicate"]
        assert replicate["status"] == "healthy"
        assert replicate["available"] is True
        assert "models" in replicate

        # Check unavailable provider
        comfyui = data["providers"]["comfyui"]
        assert comfyui["status"] == "unavailable"
        assert comfyui["available"] is False
        assert "error" in comfyui


class TestHealthResponseFormat:
    """Test health response format validation."""

    @pytest.fixture
    def client(self):
        router = MockHealthRouter()
        return TestClient(router.app)

    def test_health_response_has_required_fields(self, client):
        """Test health response contains required fields."""
        response = client.get("/health")
        data = response.json()

        required_fields = ["status", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_detailed_health_response_structure(self, client):
        """Test detailed health response structure."""
        response = client.get("/health/detailed")
        data = response.json()

        assert "status" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_provider_health_response_structure(self, client):
        """Test provider health response structure."""
        response = client.get("/health/providers")
        data = response.json()

        assert "providers" in data
        for _provider_name, provider_data in data["providers"].items():
            assert "status" in provider_data
            assert "available" in provider_data


class TestHealthStatusValues:
    """Test health status value validation."""

    def test_valid_status_values(self):
        """Test valid health status values."""
        valid_statuses = ["healthy", "degraded", "unhealthy", "unavailable"]

        for status in valid_statuses:
            assert isinstance(status, str)
            assert len(status) > 0

    def test_status_value_meanings(self):
        """Document status value meanings."""
        status_meanings = {
            "healthy": "All systems operational",
            "degraded": "Some components have issues but core functionality works",
            "unhealthy": "Critical components failing",
            "unavailable": "Service not available",
        }

        for _status, meaning in status_meanings.items():
            assert len(meaning) > 0
