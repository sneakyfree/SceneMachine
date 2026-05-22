"""Locust-based Load Test Suite for SceneMachine.

Comprehensive HTTP load testing for API endpoints.
Supports profiles: smoke, load, stress, spike.

Run with:
    locust -f tests/performance/load_test_suite.py --headless \
        -u 50 -r 5 -t 5m --html=load_report.html

Or with config:
    locust -f tests/performance/load_test_suite.py \
        --config tests/performance/load_test_config.yaml
"""

import random
from typing import Any
from uuid import uuid4

try:
    from locust import (  # noqa: F401 — events imported for downstream usage; F401 doesn't see the dynamic re-export
        HttpUser,
        LoadTestShape,
        between,
        events,
        task,
    )
    from locust.env import (
        Environment,  # noqa: F401 — Environment reserved for programmatic test runners
    )
    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False
    # Provide stubs for when Locust isn't installed
    class HttpUser:
        pass
    def task(weight=1):
        def decorator(func):
            return func
        return decorator
    def between(min_wait, max_wait):
        return min_wait


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CONFIG = {
    "base_url": "http://localhost:8000",
    "auth_token": None,
    "test_project_id": None,
    "profiles": {
        "smoke": {"users": 5, "spawn_rate": 1, "duration": "1m"},
        "load": {"users": 25, "spawn_rate": 5, "duration": "5m"},
        "stress": {"users": 50, "spawn_rate": 10, "duration": "10m"},
        "spike": {"users": 100, "spawn_rate": 50, "duration": "2m"},
    },
    "thresholds": {
        "response_time_p95_ms": 2000,
        "error_rate_percent": 5,
        "requests_per_second": 50,
    },
}


# =============================================================================
# Base User Behavior
# =============================================================================

class SceneMachineUser(HttpUser):
    """Base user behavior for SceneMachine load testing."""

    wait_time = between(1, 3)

    def on_start(self):
        """Setup before tests - authenticate and create test data."""
        self.auth_token = None
        self.project_id = None
        self.character_ids: list[str] = []
        self.scene_ids: list[str] = []

        # Attempt authentication
        self._login()

        # Get or create test project
        self._setup_project()

    def _login(self):
        """Authenticate with test credentials."""
        try:
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@scenemachine.ai",
                    "password": "test123",
                },
                name="/auth/login",
            )
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
        except Exception:
            pass  # Continue without auth for public endpoints

    def _setup_project(self):
        """Get or create a test project."""
        headers = self._get_headers()
        try:
            # Try to get existing projects
            response = self.client.get(
                "/api/v1/projects",
                headers=headers,
                name="/projects [list]",
            )
            if response.status_code == 200:
                projects = response.json()
                if projects:
                    self.project_id = projects[0].get("id")
                    return

            # Create new project if none exists
            response = self.client.post(
                "/api/v1/projects",
                json={
                    "name": f"Load Test Project {uuid4().hex[:8]}",
                    "description": "Created by load tests",
                },
                headers=headers,
                name="/projects [create]",
            )
            if response.status_code in (200, 201):
                self.project_id = response.json().get("id")
        except Exception:
            pass

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers


# =============================================================================
# API Endpoint Tests
# =============================================================================

class HealthCheckUser(SceneMachineUser):
    """User that tests health and basic endpoints."""

    weight = 3

    @task(10)
    def check_health(self):
        """Test health endpoint (most frequent)."""
        self.client.get("/health", name="/health")

    @task(5)
    def check_api_health(self):
        """Test API v1 health."""
        self.client.get("/api/v1/health", name="/api/v1/health")


class ProjectUser(SceneMachineUser):
    """User that interacts with projects."""

    weight = 5

    @task(5)
    def list_projects(self):
        """List all projects."""
        self.client.get(
            "/api/v1/projects",
            headers=self._get_headers(),
            name="/projects [list]",
        )

    @task(3)
    def get_project(self):
        """Get project details."""
        if self.project_id:
            self.client.get(
                f"/api/v1/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/projects/{id}",
            )

    @task(1)
    def get_project_settings(self):
        """Get project settings."""
        if self.project_id:
            self.client.get(
                f"/api/v1/projects/{self.project_id}/settings",
                headers=self._get_headers(),
                name="/projects/{id}/settings",
            )


class CharacterLabUser(SceneMachineUser):
    """User that interacts with Character Lab."""

    weight = 4

    @task(5)
    def list_characters(self):
        """List characters in project."""
        if self.project_id:
            response = self.client.get(
                f"/api/v1/character-lab/projects/{self.project_id}/characters",
                headers=self._get_headers(),
                name="/character-lab/characters [list]",
            )
            if response.status_code == 200:
                chars = response.json()
                self.character_ids = [c.get("id") for c in chars if c.get("id")]

    @task(3)
    def get_character(self):
        """Get character details."""
        if self.character_ids:
            char_id = random.choice(self.character_ids)
            self.client.get(
                f"/api/v1/character-lab/characters/{char_id}",
                headers=self._get_headers(),
                name="/character-lab/characters/{id}",
            )

    @task(1)
    def create_character(self):
        """Create a new character."""
        if self.project_id:
            self.client.post(
                f"/api/v1/character-lab/projects/{self.project_id}/characters",
                json={
                    "name": f"LoadTest_{uuid4().hex[:6]}",
                    "description": "Created by load test",
                    "physical_description": {"height": "tall"},
                },
                headers=self._get_headers(),
                name="/character-lab/characters [create]",
            )


class GenerationUser(SceneMachineUser):
    """User that interacts with generation APIs."""

    weight = 3

    @task(5)
    def get_queue_status(self):
        """Check generation queue status."""
        self.client.get(
            "/api/v1/generation/queue",
            headers=self._get_headers(),
            name="/generation/queue",
        )

    @task(3)
    def get_job_status(self):
        """Get status of a generation job."""
        if self.project_id:
            self.client.get(
                f"/api/v1/generation/projects/{self.project_id}/jobs",
                headers=self._get_headers(),
                name="/generation/jobs [list]",
            )

    @task(1)
    def get_cost_estimate(self):
        """Get cost estimate for generation."""
        if self.project_id:
            self.client.post(
                f"/api/v1/generation/projects/{self.project_id}/estimate",
                json={
                    "quality": "standard",
                    "shot_count": 10,
                },
                headers=self._get_headers(),
                name="/generation/estimate",
            )


class TimelineUser(SceneMachineUser):
    """User that interacts with timeline APIs."""

    weight = 4

    @task(5)
    def get_timeline(self):
        """Get project timeline."""
        if self.project_id:
            self.client.get(
                f"/api/v1/timeline/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/timeline/{project_id}",
            )

    @task(3)
    def get_scenes(self):
        """List scenes in project."""
        if self.project_id:
            self.client.get(
                f"/api/v1/scenes/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/scenes [list]",
            )


class ExplainabilityUser(SceneMachineUser):
    """User that interacts with explainability/audit APIs."""

    weight = 2

    @task(5)
    def get_pipeline_status(self):
        """Get pipeline status."""
        if self.project_id:
            self.client.get(
                f"/api/v1/pipeline/projects/{self.project_id}/status",
                headers=self._get_headers(),
                name="/pipeline/status",
            )

    @task(3)
    def list_snapshots(self):
        """List project snapshots."""
        if self.project_id:
            self.client.get(
                f"/api/v1/snapshots/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/snapshots [list]",
            )


# =============================================================================
# Combined Load Test User
# =============================================================================

class MixedWorkloadUser(SceneMachineUser):
    """Combined user simulating real-world mixed workload."""

    weight = 10

    @task(10)
    def health_check(self):
        """Quick health check."""
        self.client.get("/health", name="/health")

    @task(8)
    def browse_projects(self):
        """Browse projects."""
        self.client.get(
            "/api/v1/projects",
            headers=self._get_headers(),
            name="/projects [list]",
        )

    @task(6)
    def view_project(self):
        """View project details."""
        if self.project_id:
            self.client.get(
                f"/api/v1/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/projects/{id}",
            )

    @task(5)
    def view_characters(self):
        """View characters."""
        if self.project_id:
            self.client.get(
                f"/api/v1/character-lab/projects/{self.project_id}/characters",
                headers=self._get_headers(),
                name="/character-lab/characters [list]",
            )

    @task(4)
    def view_timeline(self):
        """View timeline."""
        if self.project_id:
            self.client.get(
                f"/api/v1/timeline/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/timeline/{project_id}",
            )

    @task(3)
    def check_queue(self):
        """Check generation queue."""
        self.client.get(
            "/api/v1/generation/queue",
            headers=self._get_headers(),
            name="/generation/queue",
        )

    @task(2)
    def view_analytics(self):
        """View analytics."""
        if self.project_id:
            self.client.get(
                f"/api/v1/analytics/projects/{self.project_id}",
                headers=self._get_headers(),
                name="/analytics/{project_id}",
            )

    @task(1)
    def update_settings(self):
        """Update settings (less frequent)."""
        if self.project_id:
            self.client.patch(
                f"/api/v1/projects/{self.project_id}/settings",
                json={"visual_style": "cinematic"},
                headers=self._get_headers(),
                name="/projects/{id}/settings [update]",
            )


# =============================================================================
# Load Test Shapes
# =============================================================================

class SmokeTestShape(LoadTestShape if LOCUST_AVAILABLE else object):
    """Quick smoke test - minimal load."""

    stages = [
        {"duration": 30, "users": 5, "spawn_rate": 1},
        {"duration": 60, "users": 5, "spawn_rate": 1},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None


class StressTestShape(LoadTestShape if LOCUST_AVAILABLE else object):
    """Stress test - ramp up to find breaking point."""

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},
        {"duration": 120, "users": 25, "spawn_rate": 5},
        {"duration": 180, "users": 50, "spawn_rate": 10},
        {"duration": 240, "users": 75, "spawn_rate": 15},
        {"duration": 300, "users": 100, "spawn_rate": 20},
        {"duration": 360, "users": 50, "spawn_rate": 10},
        {"duration": 420, "users": 25, "spawn_rate": 5},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None


class SpikeTestShape(LoadTestShape if LOCUST_AVAILABLE else object):
    """Spike test - sudden traffic surge."""

    stages = [
        {"duration": 30, "users": 10, "spawn_rate": 2},
        {"duration": 60, "users": 100, "spawn_rate": 50},  # Spike!
        {"duration": 90, "users": 100, "spawn_rate": 50},
        {"duration": 120, "users": 10, "spawn_rate": 10},  # Drop
        {"duration": 180, "users": 10, "spawn_rate": 2},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None


# =============================================================================
# Event Hooks for Reporting
# =============================================================================

class LoadTestReporter:
    """Collects and reports load test metrics."""

    def __init__(self):
        self.request_count = 0
        self.failure_count = 0
        self.response_times: list[float] = []
        self.start_time: float | None = None

    def on_request(self, request_type, name, response_time, response_length, **kwargs):
        """Record successful request."""
        self.request_count += 1
        self.response_times.append(response_time)

    def on_failure(self, request_type, name, response_time, exception, **kwargs):
        """Record failed request."""
        self.failure_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Get test summary."""
        if not self.response_times:
            return {"error": "No data collected"}

        sorted_times = sorted(self.response_times)
        p50_idx = int(len(sorted_times) * 0.50)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)

        return {
            "total_requests": self.request_count,
            "failed_requests": self.failure_count,
            "success_rate": f"{(1 - self.failure_count/max(1, self.request_count)) * 100:.1f}%",
            "response_time_avg_ms": f"{sum(self.response_times)/len(self.response_times):.1f}",
            "response_time_p50_ms": f"{sorted_times[p50_idx]:.1f}",
            "response_time_p95_ms": f"{sorted_times[p95_idx]:.1f}",
            "response_time_p99_ms": f"{sorted_times[p99_idx]:.1f}",
        }


# =============================================================================
# Standalone Test Runner (for pytest integration)
# =============================================================================

def run_load_test_standalone(
    host: str = "http://localhost:8000",
    users: int = 10,
    spawn_rate: int = 2,
    duration_seconds: int = 60,
) -> dict[str, Any]:
    """Run load test standalone (without Locust CLI).

    Useful for CI/CD integration.
    """
    if not LOCUST_AVAILABLE:
        return {"error": "Locust not installed. Run: pip install locust"}

    import gevent
    from locust.env import Environment
    from locust.log import setup_logging
    from locust.stats import stats_printer

    setup_logging("WARNING", None)

    # Create environment
    env = Environment(user_classes=[MixedWorkloadUser], host=host)

    # Create runner
    runner = env.create_local_runner()

    # Start stats printer
    gevent.spawn(stats_printer(env.stats))

    # Start the test
    runner.start(users, spawn_rate=spawn_rate)

    # Run for duration
    gevent.sleep(duration_seconds)

    # Stop
    runner.stop()

    # Collect results
    stats = env.stats
    results = {
        "total_requests": stats.total.num_requests,
        "total_failures": stats.total.num_failures,
        "requests_per_second": stats.total.total_rps,
        "response_time_avg": stats.total.avg_response_time,
        "response_time_p50": stats.total.get_response_time_percentile(0.50),
        "response_time_p95": stats.total.get_response_time_percentile(0.95),
        "response_time_p99": stats.total.get_response_time_percentile(0.99),
        "error_rate": stats.total.fail_ratio * 100,
    }

    # Check thresholds
    thresholds_passed = True
    if results["response_time_p95"] > DEFAULT_CONFIG["thresholds"]["response_time_p95_ms"]:
        thresholds_passed = False
    if results["error_rate"] > DEFAULT_CONFIG["thresholds"]["error_rate_percent"]:
        thresholds_passed = False

    results["thresholds_passed"] = thresholds_passed

    return results


# =============================================================================
# Pytest Integration
# =============================================================================

def test_load_smoke():
    """Smoke test - quick verification."""
    if not LOCUST_AVAILABLE:
        import pytest
        pytest.skip("Locust not installed")

    results = run_load_test_standalone(
        users=5,
        spawn_rate=1,
        duration_seconds=30,
    )

    assert results.get("error_rate", 100) < 10, f"Error rate too high: {results}"


def test_load_standard():
    """Standard load test - 25 users."""
    if not LOCUST_AVAILABLE:
        import pytest
        pytest.skip("Locust not installed")

    results = run_load_test_standalone(
        users=25,
        spawn_rate=5,
        duration_seconds=60,
    )

    assert results.get("thresholds_passed", False), f"Thresholds not met: {results}"


def test_load_stress():
    """Stress test - 50 concurrent users."""
    if not LOCUST_AVAILABLE:
        import pytest
        pytest.skip("Locust not installed")

    results = run_load_test_standalone(
        users=50,
        spawn_rate=10,
        duration_seconds=120,
    )

    # Stress test has relaxed thresholds
    assert results.get("error_rate", 100) < 15, f"Error rate too high: {results}"


if __name__ == "__main__":
    print("SceneMachine Load Test Suite")
    print("="*50)
    print("\nUsage with Locust CLI:")
    print("  locust -f load_test_suite.py --headless -u 50 -r 5 -t 5m")
    print("\nAvailable User Classes:")
    print("  - HealthCheckUser (weight: 3)")
    print("  - ProjectUser (weight: 5)")
    print("  - CharacterLabUser (weight: 4)")
    print("  - GenerationUser (weight: 3)")
    print("  - TimelineUser (weight: 4)")
    print("  - ExplainabilityUser (weight: 2)")
    print("  - MixedWorkloadUser (weight: 10)")
    print("\nAvailable Shapes:")
    print("  - SmokeTestShape")
    print("  - StressTestShape")
    print("  - SpikeTestShape")
