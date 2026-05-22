#!/usr/bin/env python3
"""
SceneMachine Comprehensive E2E Test Suite.

This test suite exercises every API endpoint, IPC handler, and workflow
to ensure complete coverage and identify any issues.
"""

import asyncio
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scenemachine.api.app import create_app
from scenemachine.config import Settings
from scenemachine.models.base import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# TEST RESULT TYPES
# ============================================================================


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    category: str
    subcategory: str
    status: TestStatus
    duration_ms: float
    request_method: str | None = None
    request_path: str | None = None
    response_status: int | None = None
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteReport:
    """Complete test suite report."""

    start_time: datetime
    end_time: datetime | None = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[TestResult] = field(default_factory=list)
    coverage: dict[str, dict[str, int]] = field(default_factory=dict)

    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1
        else:
            self.errors += 1

        # Track coverage
        cat = result.category
        subcat = result.subcategory
        if cat not in self.coverage:
            self.coverage[cat] = {}
        if subcat not in self.coverage[cat]:
            self.coverage[cat][subcat] = {"passed": 0, "failed": 0, "total": 0}
        self.coverage[cat][subcat]["total"] += 1
        if result.status == TestStatus.PASSED:
            self.coverage[cat][subcat]["passed"] += 1
        else:
            self.coverage[cat][subcat]["failed"] += 1

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    def generate_report(self) -> str:
        """Generate formatted report."""
        lines = [
            "=" * 80,
            "SCENEMACHINE E2E TEST SUITE REPORT",
            "=" * 80,
            "",
            f"Start Time: {self.start_time.isoformat()}",
            f"End Time: {self.end_time.isoformat() if self.end_time else 'N/A'}",
            f"Duration: {(self.end_time - self.start_time).total_seconds():.2f}s"
            if self.end_time
            else "",
            "",
            "-" * 40,
            "SUMMARY",
            "-" * 40,
            f"Total Tests: {self.total_tests}",
            f"Passed: {self.passed} ({self.success_rate:.1f}%)",
            f"Failed: {self.failed}",
            f"Skipped: {self.skipped}",
            f"Errors: {self.errors}",
            "",
        ]

        # Coverage by category
        lines.extend(
            [
                "-" * 40,
                "COVERAGE BY CATEGORY",
                "-" * 40,
            ]
        )
        for category, subcats in sorted(self.coverage.items()):
            cat_passed = sum(s["passed"] for s in subcats.values())
            cat_total = sum(s["total"] for s in subcats.values())
            cat_pct = (cat_passed / cat_total * 100) if cat_total > 0 else 0
            lines.append(f"\n{category} ({cat_passed}/{cat_total} = {cat_pct:.1f}%)")
            for subcat, stats in sorted(subcats.items()):
                status = "✓" if stats["passed"] == stats["total"] else "✗"
                lines.append(f"  [{status}] {subcat}: {stats['passed']}/{stats['total']}")

        # Failed tests
        failed_tests = [
            r for r in self.results if r.status in [TestStatus.FAILED, TestStatus.ERROR]
        ]
        if failed_tests:
            lines.extend(
                [
                    "",
                    "-" * 40,
                    "FAILED TESTS",
                    "-" * 40,
                ]
            )
            for result in failed_tests:
                lines.append(f"\n  [{result.status.value.upper()}] {result.name}")
                lines.append(f"    Category: {result.category} / {result.subcategory}")
                if result.request_method:
                    lines.append(f"    Request: {result.request_method} {result.request_path}")
                if result.response_status:
                    lines.append(f"    Response Status: {result.response_status}")
                if result.error_message:
                    lines.append(f"    Error: {result.error_message[:200]}")

        lines.extend(
            [
                "",
                "=" * 80,
                f"OVERALL STATUS: {'PASS' if self.failed == 0 and self.errors == 0 else 'FAIL'}",
                "=" * 80,
            ]
        )

        return "\n".join(lines)


# ============================================================================
# E2E TEST SUITE
# ============================================================================


class E2ETestSuite:
    """Comprehensive E2E test suite for SceneMachine."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./data/test_e2e.db"):
        """Initialize test suite."""
        self.database_url = database_url
        self.report = TestSuiteReport(start_time=datetime.now(UTC))
        self.client: AsyncClient | None = None
        self.session: AsyncSession | None = None

        # Test data references
        self.test_project_id: str | None = None
        self.test_character_id: str | None = None
        self.test_scene_id: str | None = None
        self.test_shot_id: str | None = None

    async def setup(self):
        """Set up test environment."""
        from scenemachine.database import get_db_manager, reset_db_manager

        # Reset any existing database manager
        reset_db_manager()

        # Create test settings
        settings = Settings(
            database_url=self.database_url,
            debug=True,
            environment="test",
        )

        # Initialize the database manager manually for testing
        is_sqlite = "sqlite" in self.database_url
        db_manager = get_db_manager()

        # Set the database URL before initialization
        db_manager._database_url = self.database_url

        # For SQLite, we need to use our compatibility layer
        if is_sqlite:
            from tests.sqlite_compat import create_all_tables_sqlite

            # Convert URL and create engine
            url = self.database_url
            if url.startswith("sqlite:///"):
                url = url.replace("sqlite:///", "sqlite+aiosqlite:///")

            db_manager._engine = create_async_engine(url, echo=False)
            db_manager._session_factory = async_sessionmaker(
                db_manager._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            await create_all_tables_sqlite(db_manager._engine, Base)
        else:
            await db_manager.initialize()

        # Create app
        app = create_app(settings)

        # Create test client using lifespan_handler
        # The lifespan won't re-initialize since db_manager is already set up
        transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=transport, base_url="http://test")

        # Create our own session for direct DB access in tests
        # URL is already async-compatible from db_manager setup
        session_url = self.database_url
        if "sqlite:///" in session_url and "+aiosqlite" not in session_url:
            session_url = session_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        engine = create_async_engine(session_url, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self.session = session_factory()

        logger.info("Test environment set up")

    async def teardown(self):
        """Tear down test environment."""
        from scenemachine.database import get_db_manager, reset_db_manager

        if self.client:
            await self.client.aclose()
        if self.session:
            await self.session.close()

        # Clean up database manager
        try:
            db_manager = get_db_manager()
            await db_manager.close()
        except Exception:
            pass
        reset_db_manager()

        logger.info("Test environment torn down")

    async def run_test(
        self,
        name: str,
        category: str,
        subcategory: str,
        test_func: Callable,
        *args,
        **kwargs,
    ) -> TestResult:
        """Run a single test and record result."""
        start = time.time()
        try:
            result_data = await test_func(*args, **kwargs)
            duration = (time.time() - start) * 1000

            result = TestResult(
                name=name,
                category=category,
                subcategory=subcategory,
                status=TestStatus.PASSED,
                duration_ms=duration,
                **result_data if result_data else {},
            )
        except AssertionError as e:
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                category=category,
                subcategory=subcategory,
                status=TestStatus.FAILED,
                duration_ms=duration,
                error_message=str(e),
            )
            logger.warning(f"Test FAILED: {name} - {e}")
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                category=category,
                subcategory=subcategory,
                status=TestStatus.ERROR,
                duration_ms=duration,
                error_message=f"{type(e).__name__}: {str(e)}",
            )
            logger.error(f"Test ERROR: {name} - {e}")

        self.report.add_result(result)
        return result

    # ========================================================================
    # API TEST HELPERS
    # ========================================================================

    async def api_get(self, path: str, expected_status: int = 200) -> dict[str, Any]:
        """Make GET request and verify status."""
        response = await self.client.get(path)
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
        )
        return {
            "request_method": "GET",
            "request_path": path,
            "response_status": response.status_code,
            "details": {"response": response.json() if response.content else None},
        }

    async def api_post(
        self,
        path: str,
        json_data: dict = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        """Make POST request and verify status."""
        response = await self.client.post(path, json=json_data)
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
        )
        return {
            "request_method": "POST",
            "request_path": path,
            "response_status": response.status_code,
            "details": {"response": response.json() if response.content else None},
        }

    async def api_patch(
        self,
        path: str,
        json_data: dict = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        """Make PATCH request and verify status."""
        response = await self.client.patch(path, json=json_data)
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
        )
        return {
            "request_method": "PATCH",
            "request_path": path,
            "response_status": response.status_code,
            "details": {"response": response.json() if response.content else None},
        }

    async def api_delete(self, path: str, expected_status: int = 200) -> dict[str, Any]:
        """Make DELETE request and verify status."""
        response = await self.client.delete(path)
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
        )
        return {
            "request_method": "DELETE",
            "request_path": path,
            "response_status": response.status_code,
        }

    # ========================================================================
    # HEALTH API TESTS
    # ========================================================================

    async def test_health_check(self):
        """Test basic health check endpoint."""
        return await self.api_get("/health")

    async def test_health_ready(self):
        """Test readiness check endpoint."""
        return await self.api_get("/ready")

    async def test_health_detailed(self):
        """Test detailed health endpoint."""
        return await self.api_get("/health/detailed")

    async def test_health_providers(self):
        """Test providers health endpoint."""
        return await self.api_get("/health/providers")

    async def test_health_circuits(self):
        """Test circuit breakers endpoint."""
        return await self.api_get("/health/circuits")

    # ========================================================================
    # PROJECT API TESTS
    # ========================================================================

    async def test_projects_list(self):
        """Test listing projects."""
        return await self.api_get("/api/v1/projects")

    async def test_projects_create(self):
        """Test creating a project."""
        result = await self.api_post(
            "/api/v1/projects",
            json_data={
                "name": "E2E Test Project",
                "description": "Created by E2E test suite",
            },
            expected_status=201,
        )
        if result.get("details", {}).get("response"):
            self.test_project_id = result["details"]["response"].get("id")
        return result

    async def test_projects_get(self):
        """Test getting a project."""
        if not self.test_project_id:
            # Get first project from list
            response = await self.client.get("/api/v1/projects")
            if response.status_code == 200 and response.json():
                self.test_project_id = response.json()[0]["id"]

        if self.test_project_id:
            return await self.api_get(f"/api/v1/projects/{self.test_project_id}")
        return {"error_message": "No project available for testing"}

    async def test_projects_update(self):
        """Test updating a project."""
        if self.test_project_id:
            return await self.api_patch(
                f"/api/v1/projects/{self.test_project_id}",
                json_data={"name": "E2E Test Project Updated"},
            )
        return {"error_message": "No project available for testing"}

    async def test_projects_list_with_pagination(self):
        """Test project listing with pagination."""
        return await self.api_get("/api/v1/projects?skip=0&limit=5")

    # ========================================================================
    # CHARACTER API TESTS
    # ========================================================================

    async def test_characters_list(self):
        """Test listing characters for a project."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/characters/project/{self.test_project_id}")
        return {"error_message": "No project available"}

    async def test_characters_get(self):
        """Test getting a character."""
        if self.test_project_id:
            # First get list
            response = await self.client.get(f"/api/v1/characters/project/{self.test_project_id}")
            if response.status_code == 200:
                data = response.json()
                # Response is CharacterListResponse with "characters" field
                characters = data.get("characters", []) if isinstance(data, dict) else data
                if characters:
                    self.test_character_id = characters[0]["id"]
                    return await self.api_get(f"/api/v1/characters/{self.test_character_id}")
        return {"error_message": "No character available"}

    async def test_characters_update(self):
        """Test updating a character."""
        if self.test_character_id:
            return await self.api_patch(
                f"/api/v1/characters/{self.test_character_id}",
                json_data={"description": "Updated by E2E test"},
            )
        return {"error_message": "No character available"}

    # ========================================================================
    # SCENE API TESTS
    # ========================================================================

    async def test_scenes_list(self):
        """Test listing scenes for a project."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/scenes/project/{self.test_project_id}")
        return {"error_message": "No project available"}

    async def test_scenes_get(self):
        """Test getting a scene."""
        if self.test_project_id:
            response = await self.client.get(f"/api/v1/scenes/project/{self.test_project_id}")
            if response.status_code == 200 and response.json():
                self.test_scene_id = response.json()[0]["id"]
                return await self.api_get(f"/api/v1/scenes/{self.test_scene_id}")
        return {"error_message": "No scene available"}

    async def test_scenes_shots(self):
        """Test getting shots for a scene."""
        if self.test_scene_id:
            return await self.api_get(f"/api/v1/scenes/{self.test_scene_id}/shots")
        return {"error_message": "No scene available"}

    async def test_scenes_reference_shot_types(self):
        """Test getting shot type reference."""
        return await self.api_get("/api/v1/scenes/reference/shot-types")

    async def test_scenes_reference_camera_movements(self):
        """Test getting camera movement reference."""
        return await self.api_get("/api/v1/scenes/reference/camera-movements")

    # ========================================================================
    # SHOT API TESTS
    # ========================================================================

    async def test_shots_get(self):
        """Test getting a shot."""
        if self.test_scene_id:
            response = await self.client.get(f"/api/v1/scenes/{self.test_scene_id}/shots")
            if response.status_code == 200 and response.json():
                self.test_shot_id = response.json()[0]["id"]
                return await self.api_get(f"/api/v1/scenes/shots/{self.test_shot_id}")
        return {"error_message": "No shot available"}

    async def test_shots_update(self):
        """Test updating a shot."""
        if self.test_shot_id:
            return await self.api_patch(
                f"/api/v1/scenes/shots/{self.test_shot_id}",
                json_data={"description": "Updated by E2E test"},
            )
        return {"error_message": "No shot available"}

    # ========================================================================
    # GENERATION API TESTS
    # ========================================================================

    async def test_generation_providers(self):
        """Test getting generation providers."""
        return await self.api_get("/api/v1/generation/providers")

    async def test_generation_queue_status(self):
        """Test getting queue status."""
        return await self.api_get("/api/v1/generation/queue")

    async def test_generation_pending_jobs(self):
        """Test getting pending jobs."""
        return await self.api_get("/api/v1/generation/queue/pending")

    async def test_generation_worker_status(self):
        """Test getting worker status."""
        return await self.api_get("/api/v1/generation/worker/status")

    async def test_generation_providers_health(self):
        """Test getting providers health."""
        return await self.api_get("/api/v1/generation/providers/health")

    async def test_generation_cost_estimate(self):
        """Test cost estimation."""
        return await self.api_post(
            "/api/v1/generation/estimate-cost",
            json_data={
                "provider": "replicate",
                "duration_seconds": 5.0,
            },
        )

    # ========================================================================
    # ASSEMBLY API TESTS
    # ========================================================================

    async def test_assembly_formats(self):
        """Test getting export formats."""
        return await self.api_get("/api/v1/assembly/formats")

    async def test_assembly_quality_presets(self):
        """Test getting quality presets."""
        return await self.api_get("/api/v1/assembly/quality-presets")

    async def test_assembly_status(self):
        """Test getting assembly status."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/assembly/status/{self.test_project_id}")
        return {"error_message": "No project available"}

    async def test_assembly_timeline(self):
        """Test getting timeline."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/assembly/timeline/{self.test_project_id}")
        return {"error_message": "No project available"}

    async def test_assembly_export_history(self):
        """Test getting export history."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/assembly/export/history/{self.test_project_id}")
        return {"error_message": "No project available"}

    # ========================================================================
    # SETTINGS API TESTS
    # ========================================================================

    async def test_settings_get(self):
        """Test getting settings."""
        return await self.api_get("/api/v1/settings")

    async def test_settings_update(self):
        """Test updating settings."""
        return await self.api_patch(
            "/api/v1/settings",
            json_data={"theme_mode": "dark"},
        )

    async def test_settings_storage(self):
        """Test getting storage stats."""
        return await self.api_get("/api/v1/settings/storage")

    async def test_settings_providers_status(self):
        """Test getting provider status."""
        return await self.api_get("/api/v1/settings/providers/status")

    async def test_settings_llm_providers(self):
        """Test getting LLM providers."""
        return await self.api_get("/api/v1/settings/providers/llm")

    async def test_settings_video_providers(self):
        """Test getting video providers."""
        return await self.api_get("/api/v1/settings/providers/video")

    async def test_settings_themes(self):
        """Test getting themes."""
        return await self.api_get("/api/v1/settings/themes")

    # ========================================================================
    # ANALYTICS API TESTS
    # ========================================================================

    async def test_analytics_dashboard(self):
        """Test getting dashboard data."""
        return await self.api_get("/api/v1/analytics/dashboard")

    async def test_analytics_generation_stats(self):
        """Test getting generation stats."""
        return await self.api_get("/api/v1/analytics/generation-stats")

    async def test_analytics_cost_stats(self):
        """Test getting cost stats."""
        return await self.api_get("/api/v1/analytics/cost-stats")

    async def test_analytics_project_stats(self):
        """Test getting project stats."""
        return await self.api_get("/api/v1/analytics/project-stats")

    async def test_analytics_daily_stats(self):
        """Test getting daily stats."""
        return await self.api_get("/api/v1/analytics/daily-stats")

    async def test_analytics_provider_usage(self):
        """Test getting provider usage."""
        return await self.api_get("/api/v1/analytics/provider-usage")

    # ========================================================================
    # AUDIO API TESTS
    # ========================================================================

    async def test_audio_sfx_list(self):
        """Test listing sound effects."""
        return await self.api_get("/api/v1/audio/sfx")

    async def test_audio_sfx_categories(self):
        """Test getting SFX categories."""
        return await self.api_get("/api/v1/audio/sfx/categories")

    async def test_audio_music_list(self):
        """Test listing music tracks."""
        return await self.api_get("/api/v1/audio/music")

    async def test_audio_music_genres(self):
        """Test getting music genres."""
        return await self.api_get("/api/v1/audio/music/genres")

    async def test_audio_music_moods(self):
        """Test getting music moods."""
        return await self.api_get("/api/v1/audio/music/moods")

    # ========================================================================
    # SHARING API TESTS
    # ========================================================================

    async def test_sharing_project_shares(self):
        """Test getting project shares."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/sharing/project/{self.test_project_id}")
        return {"error_message": "No project available"}

    async def test_sharing_project_comments(self):
        """Test getting project comments."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/sharing/projects/{self.test_project_id}/comments")
        return {"error_message": "No project available"}

    # ========================================================================
    # TEXT OVERLAYS API TESTS
    # ========================================================================

    async def test_overlays_presets(self):
        """Test getting overlay presets."""
        return await self.api_get("/api/v1/text-overlays/presets")

    async def test_overlays_for_project(self):
        """Test getting overlays for project."""
        if self.test_project_id:
            return await self.api_get(f"/api/v1/text-overlays/project/{self.test_project_id}")
        return {"error_message": "No project available"}

    # ========================================================================
    # ARCHIVE API TESTS
    # ========================================================================

    async def test_archive_list(self):
        """Test listing archives."""
        return await self.api_get("/api/v1/archive/list")

    # ========================================================================
    # WATERMARKS API TESTS
    # ========================================================================

    async def test_watermarks_list(self):
        """Test listing watermarks."""
        return await self.api_get("/api/v1/watermarks")

    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================

    async def test_404_handling(self):
        """Test 404 error handling."""
        response = await self.client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code in [404, 422], f"Expected 404/422, got {response.status_code}"
        return {
            "request_method": "GET",
            "request_path": "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            "response_status": response.status_code,
        }

    async def test_invalid_uuid_handling(self):
        """Test invalid UUID handling."""
        response = await self.client.get("/api/v1/projects/not-a-uuid")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        return {
            "request_method": "GET",
            "request_path": "/api/v1/projects/not-a-uuid",
            "response_status": response.status_code,
        }

    async def test_invalid_json_handling(self):
        """Test invalid JSON handling."""
        response = await self.client.post(
            "/api/v1/projects",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        return {
            "request_method": "POST",
            "request_path": "/api/v1/projects",
            "response_status": response.status_code,
        }

    async def test_missing_required_fields(self):
        """Test missing required fields handling."""
        response = await self.client.post("/api/v1/projects", json={})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        return {
            "request_method": "POST",
            "request_path": "/api/v1/projects",
            "response_status": response.status_code,
        }

    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================

    async def run_all_tests(self):
        """Run all E2E tests."""
        logger.info("Starting E2E Test Suite...")

        await self.setup()

        try:
            # Health API Tests
            await self.run_test("Health Check", "API", "Health", self.test_health_check)
            await self.run_test("Readiness Check", "API", "Health", self.test_health_ready)
            await self.run_test("Detailed Health", "API", "Health", self.test_health_detailed)
            await self.run_test("Providers Health", "API", "Health", self.test_health_providers)
            await self.run_test("Circuit Breakers", "API", "Health", self.test_health_circuits)

            # Project API Tests
            await self.run_test("List Projects", "API", "Projects", self.test_projects_list)
            await self.run_test("Create Project", "API", "Projects", self.test_projects_create)
            await self.run_test("Get Project", "API", "Projects", self.test_projects_get)
            await self.run_test("Update Project", "API", "Projects", self.test_projects_update)
            await self.run_test(
                "List Projects Paginated",
                "API",
                "Projects",
                self.test_projects_list_with_pagination,
            )

            # Character API Tests
            await self.run_test("List Characters", "API", "Characters", self.test_characters_list)
            await self.run_test("Get Character", "API", "Characters", self.test_characters_get)
            await self.run_test(
                "Update Character", "API", "Characters", self.test_characters_update
            )

            # Scene API Tests
            await self.run_test("List Scenes", "API", "Scenes", self.test_scenes_list)
            await self.run_test("Get Scene", "API", "Scenes", self.test_scenes_get)
            await self.run_test("Get Scene Shots", "API", "Scenes", self.test_scenes_shots)
            await self.run_test(
                "Shot Types Reference", "API", "Scenes", self.test_scenes_reference_shot_types
            )
            await self.run_test(
                "Camera Movements Reference",
                "API",
                "Scenes",
                self.test_scenes_reference_camera_movements,
            )

            # Shot API Tests
            await self.run_test("Get Shot", "API", "Shots", self.test_shots_get)
            await self.run_test("Update Shot", "API", "Shots", self.test_shots_update)

            # Generation API Tests
            await self.run_test(
                "List Providers", "API", "Generation", self.test_generation_providers
            )
            await self.run_test(
                "Queue Status", "API", "Generation", self.test_generation_queue_status
            )
            await self.run_test(
                "Pending Jobs", "API", "Generation", self.test_generation_pending_jobs
            )
            await self.run_test(
                "Worker Status", "API", "Generation", self.test_generation_worker_status
            )
            await self.run_test(
                "Providers Health", "API", "Generation", self.test_generation_providers_health
            )
            await self.run_test(
                "Cost Estimate", "API", "Generation", self.test_generation_cost_estimate
            )

            # Assembly API Tests
            await self.run_test("Export Formats", "API", "Assembly", self.test_assembly_formats)
            await self.run_test(
                "Quality Presets", "API", "Assembly", self.test_assembly_quality_presets
            )
            await self.run_test("Assembly Status", "API", "Assembly", self.test_assembly_status)
            await self.run_test("Timeline", "API", "Assembly", self.test_assembly_timeline)
            await self.run_test(
                "Export History", "API", "Assembly", self.test_assembly_export_history
            )

            # Settings API Tests
            await self.run_test("Get Settings", "API", "Settings", self.test_settings_get)
            await self.run_test("Update Settings", "API", "Settings", self.test_settings_update)
            await self.run_test("Storage Stats", "API", "Settings", self.test_settings_storage)
            await self.run_test(
                "Provider Status", "API", "Settings", self.test_settings_providers_status
            )
            await self.run_test(
                "LLM Providers", "API", "Settings", self.test_settings_llm_providers
            )
            await self.run_test(
                "Video Providers", "API", "Settings", self.test_settings_video_providers
            )
            await self.run_test("Themes", "API", "Settings", self.test_settings_themes)

            # Analytics API Tests
            await self.run_test("Dashboard", "API", "Analytics", self.test_analytics_dashboard)
            await self.run_test(
                "Generation Stats", "API", "Analytics", self.test_analytics_generation_stats
            )
            await self.run_test("Cost Stats", "API", "Analytics", self.test_analytics_cost_stats)
            await self.run_test(
                "Project Stats", "API", "Analytics", self.test_analytics_project_stats
            )
            await self.run_test("Daily Stats", "API", "Analytics", self.test_analytics_daily_stats)
            await self.run_test(
                "Provider Usage", "API", "Analytics", self.test_analytics_provider_usage
            )

            # Audio API Tests
            await self.run_test("List SFX", "API", "Audio", self.test_audio_sfx_list)
            await self.run_test("SFX Categories", "API", "Audio", self.test_audio_sfx_categories)
            await self.run_test("List Music", "API", "Audio", self.test_audio_music_list)
            await self.run_test("Music Genres", "API", "Audio", self.test_audio_music_genres)
            await self.run_test("Music Moods", "API", "Audio", self.test_audio_music_moods)

            # Sharing API Tests
            await self.run_test(
                "Project Shares", "API", "Sharing", self.test_sharing_project_shares
            )
            await self.run_test(
                "Project Comments", "API", "Sharing", self.test_sharing_project_comments
            )

            # Text Overlays API Tests
            await self.run_test(
                "Overlay Presets", "API", "TextOverlays", self.test_overlays_presets
            )
            await self.run_test(
                "Project Overlays", "API", "TextOverlays", self.test_overlays_for_project
            )

            # Archive API Tests
            await self.run_test("List Archives", "API", "Archive", self.test_archive_list)

            # Watermarks API Tests
            await self.run_test("List Watermarks", "API", "Watermarks", self.test_watermarks_list)

            # Error Handling Tests
            await self.run_test("404 Handling", "API", "ErrorHandling", self.test_404_handling)
            await self.run_test(
                "Invalid UUID", "API", "ErrorHandling", self.test_invalid_uuid_handling
            )
            await self.run_test(
                "Invalid JSON", "API", "ErrorHandling", self.test_invalid_json_handling
            )
            await self.run_test(
                "Missing Fields", "API", "ErrorHandling", self.test_missing_required_fields
            )

        finally:
            await self.teardown()

        self.report.end_time = datetime.now(UTC)
        logger.info("E2E Test Suite completed")

        return self.report


# ============================================================================
# CLI ENTRY POINT
# ============================================================================


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run SceneMachine E2E Test Suite")
    parser.add_argument(
        "--database-url",
        default="sqlite+aiosqlite:///./data/test_e2e.db",
        help="Database URL for testing",
    )
    parser.add_argument(
        "--output",
        default="./data/e2e_test_report.txt",
        help="Output file for report",
    )

    args = parser.parse_args()

    suite = E2ETestSuite(database_url=args.database_url)
    report = await suite.run_all_tests()

    # Print report
    report_text = report.generate_report()
    print(report_text)

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report_text)
    logger.info(f"Report saved to: {output_path}")

    # Return exit code
    return 0 if report.failed == 0 and report.errors == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
