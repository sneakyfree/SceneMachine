#!/usr/bin/env python3
"""
SceneMachine End-to-End Smoke Test.

This script performs comprehensive testing of all modules and components
without requiring a running database, using module imports and unit tests.
"""

import inspect
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    category: str
    passed: bool
    duration_ms: float
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SmokeTestReport:
    """Complete smoke test report."""

    start_time: datetime
    end_time: datetime | None = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    results: list[TestResult] = field(default_factory=list)
    module_stats: dict[str, dict[str, int]] = field(default_factory=dict)

    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def generate_report(self) -> str:
        """Generate a formatted report."""
        lines = [
            "=" * 80,
            "SCENEMACHINE SMOKE TEST REPORT",
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
            f"Passed: {self.passed_tests} ({self.success_rate:.1f}%)",
            f"Failed: {self.failed_tests}",
            f"Skipped: {self.skipped_tests}",
            "",
        ]

        if self.module_stats:
            lines.extend(
                [
                    "-" * 40,
                    "MODULE STATISTICS",
                    "-" * 40,
                ]
            )
            for module, stats in sorted(self.module_stats.items()):
                lines.append(f"  {module}:")
                for key, value in stats.items():
                    lines.append(f"    {key}: {value}")

        lines.extend(
            [
                "",
                "-" * 40,
                "TEST RESULTS BY CATEGORY",
                "-" * 40,
            ]
        )

        # Group by category
        categories: dict[str, list[TestResult]] = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        for category, results in sorted(categories.items()):
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            lines.append(f"\n{category} ({passed}/{total} passed)")
            lines.append("-" * 40)

            for result in results:
                status = "PASS" if result.passed else "FAIL"
                lines.append(f"  [{status}] {result.name} ({result.duration_ms:.1f}ms)")
                if not result.passed and result.message:
                    lines.append(f"         Error: {result.message[:100]}...")

        # Failed tests summary
        failed = [r for r in self.results if not r.passed]
        if failed:
            lines.extend(
                [
                    "",
                    "-" * 40,
                    "FAILED TESTS DETAILS",
                    "-" * 40,
                ]
            )
            for result in failed:
                lines.append(f"\n  {result.name}")
                lines.append(f"  Category: {result.category}")
                lines.append(f"  Error: {result.message}")

        lines.extend(
            [
                "",
                "=" * 80,
                f"OVERALL STATUS: {'PASS' if self.failed_tests == 0 else 'FAIL'}",
                "=" * 80,
            ]
        )

        return "\n".join(lines)


class SmokeTest:
    """End-to-end smoke test for SceneMachine."""

    def __init__(self):
        self.report = SmokeTestReport(start_time=datetime.now(UTC))

    def run_test(self, name: str, category: str, test_func, *args, **kwargs) -> TestResult:
        """Run a single test and record the result."""
        start = time.time()
        try:
            test_func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                category=category,
                passed=True,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                category=category,
                passed=False,
                duration_ms=duration,
                message=str(e),
            )
            logger.error(f"Test failed: {name} - {e}")

        self.report.add_result(result)
        return result

    def run_all_tests(self):
        """Run all smoke tests."""
        logger.info("Starting SceneMachine Smoke Tests...")

        # ============ MODEL IMPORTS ============
        self.run_test("Import Base models", "Models", self.test_import_base_models)
        self.run_test("Import Project model", "Models", self.test_import_project)
        self.run_test("Import Character model", "Models", self.test_import_character)
        self.run_test("Import Scene model", "Models", self.test_import_scene)
        self.run_test("Import Shot model", "Models", self.test_import_shot)
        self.run_test("Import GenerationJob model", "Models", self.test_import_generation_job)
        self.run_test("Import AudioAsset model", "Models", self.test_import_audio_asset)
        self.run_test("Import TextOverlay model", "Models", self.test_import_text_overlay)
        self.run_test("Import Share models", "Models", self.test_import_share_models)
        self.run_test("Import Settings model", "Models", self.test_import_settings)

        # ============ SERVICE IMPORTS ============
        self.run_test("Import Assembly service", "Services", self.test_import_assembly_service)
        self.run_test(
            "Import Generation providers", "Services", self.test_import_generation_providers
        )
        self.run_test("Import Audio library service", "Services", self.test_import_audio_library)
        self.run_test("Import Cost tracking service", "Services", self.test_import_cost_tracking)
        self.run_test("Import Character service", "Services", self.test_import_character_service)
        self.run_test("Import Scene planning service", "Services", self.test_import_scene_planning)

        # ============ API ROUTES ============
        self.run_test("Import Projects routes", "API Routes", self.test_import_projects_routes)
        self.run_test("Import Characters routes", "API Routes", self.test_import_characters_routes)
        self.run_test("Import Scenes routes", "API Routes", self.test_import_scenes_routes)
        self.run_test("Import Generation routes", "API Routes", self.test_import_generation_routes)
        self.run_test("Import Assembly routes", "API Routes", self.test_import_assembly_routes)
        self.run_test("Import Analytics routes", "API Routes", self.test_import_analytics_routes)
        self.run_test("Import Sharing routes", "API Routes", self.test_import_sharing_routes)
        self.run_test("Import Settings routes", "API Routes", self.test_import_settings_routes)
        self.run_test("Import Audio routes", "API Routes", self.test_import_audio_routes)
        self.run_test(
            "Import Text overlay routes", "API Routes", self.test_import_text_overlay_routes
        )

        # ============ IPC HANDLERS ============
        self.run_test("Import IPC handlers", "IPC", self.test_import_ipc_handlers)
        self.run_test("Verify IPC handler count", "IPC", self.test_ipc_handler_count)

        # ============ UTILITIES ============
        self.run_test("Import FFmpeg utilities", "Utilities", self.test_import_ffmpeg)
        self.run_test("Import Circuit breaker", "Utilities", self.test_import_circuit_breaker)
        self.run_test("Import Caching utilities", "Utilities", self.test_import_caching)
        self.run_test("Import logging utilities", "Utilities", self.test_import_logging)

        # ============ PARSERS ============
        self.run_test("Import Fountain parser", "Parsers", self.test_import_fountain_parser)
        self.run_test("Import PDF parser", "Parsers", self.test_import_pdf_parser)
        self.run_test("Test Parsers module", "Parsers", self.test_parsers_module)

        # ============ ENUMS & TYPES ============
        self.run_test("Verify ProjectState enum", "Enums", self.test_project_state_enum)
        self.run_test("Verify ShotType enum", "Enums", self.test_shot_type_enum)
        self.run_test("Verify CameraMovement enum", "Enums", self.test_camera_movement_enum)
        self.run_test("Verify JobStatus enum", "Enums", self.test_job_status_enum)
        self.run_test("Verify TextAnimation enum", "Enums", self.test_text_animation_enum)

        # ============ FUNCTIONALITY TESTS ============
        self.run_test("Test Fountain parsing", "Functionality", self.test_fountain_parsing)
        self.run_test("Test ExportSettings defaults", "Functionality", self.test_export_settings)
        self.run_test("Test ColorGradeSettings", "Functionality", self.test_color_grade_settings)
        self.run_test(
            "Test Circuit breaker states", "Functionality", self.test_circuit_breaker_states
        )
        self.run_test("Test Cost estimation", "Functionality", self.test_cost_estimation)

        # ============ INTEGRATION CHECKS ============
        self.run_test("Verify API app creation", "Integration", self.test_api_app_creation)
        self.run_test("Verify route registration", "Integration", self.test_route_registration)
        self.run_test("Verify model relationships", "Integration", self.test_model_relationships)

        # ============ PHASE 15-22 FEATURE TESTS ============
        self.run_test("Import Queue worker", "Phase 15-22", self.test_import_queue_worker)
        self.run_test("Import Job queue", "Phase 15-22", self.test_import_job_queue)
        self.run_test("Import Export history model", "Phase 15-22", self.test_import_export_history)
        self.run_test("Import ComfyUI provider", "Phase 15-22", self.test_import_comfyui_provider)
        self.run_test("Import RunPod provider", "Phase 15-22", self.test_import_runpod_provider)
        self.run_test("Import Provider registry", "Phase 15-22", self.test_import_provider_registry)
        self.run_test(
            "Import Rate limiter middleware", "Phase 15-22", self.test_import_rate_limiter
        )
        self.run_test(
            "Import Security middleware", "Phase 15-22", self.test_import_security_middleware
        )
        self.run_test("Import Shortcuts manager", "Phase 15-22", self.test_import_shortcuts_manager)
        self.run_test("Import Watermarks routes", "Phase 15-22", self.test_import_watermarks_routes)
        self.run_test("Import Archive routes", "Phase 15-22", self.test_import_archive_routes)
        self.run_test("Import Health routes", "Phase 15-22", self.test_import_health_routes)
        self.run_test(
            "Import Project duplicator", "Phase 15-22", self.test_import_project_duplicator
        )

        # Collect module statistics
        self._collect_module_stats()

        self.report.end_time = datetime.now(UTC)
        logger.info("Smoke tests completed.")

    def _collect_module_stats(self):
        """Collect statistics about modules."""
        stats = {}

        # Count models
        from scenemachine import models

        model_classes = [
            name
            for name, obj in inspect.getmembers(models)
            if inspect.isclass(obj) and hasattr(obj, "__tablename__")
        ]
        stats["models"] = {"table_count": len(model_classes)}

        # Count routes
        try:
            from scenemachine.api import routes

            route_modules = [name for name in dir(routes) if not name.startswith("_")]
            stats["api_routes"] = {"module_count": len(route_modules)}
        except:
            pass

        self.report.module_stats = stats

    # ============ MODEL IMPORT TESTS ============

    def test_import_base_models(self):
        from scenemachine.models import Base, TimestampMixin, UUIDMixin

        assert Base is not None
        assert UUIDMixin is not None
        assert TimestampMixin is not None

    def test_import_project(self):
        from scenemachine.models import Project, ProjectState

        assert hasattr(Project, "__tablename__")
        assert Project.__tablename__ == "projects"
        assert len(ProjectState) >= 5

    def test_import_character(self):
        from scenemachine.models import Character, CharacterGender

        assert hasattr(Character, "__tablename__")
        assert Character.__tablename__ == "characters"
        assert CharacterGender.MALE is not None
        assert CharacterGender.FEMALE is not None

    def test_import_scene(self):
        from scenemachine.models import Scene, SceneType, TimeOfDay

        assert hasattr(Scene, "__tablename__")
        assert SceneType.INTERIOR is not None
        assert SceneType.EXTERIOR is not None
        assert TimeOfDay.DAY is not None

    def test_import_shot(self):
        from scenemachine.models import CameraMovement, Shot, ShotType

        assert hasattr(Shot, "__tablename__")
        assert len(list(ShotType)) >= 10
        assert len(list(CameraMovement)) >= 5

    def test_import_generation_job(self):
        from scenemachine.models import GenerationJob, JobStatus

        assert hasattr(GenerationJob, "__tablename__")
        assert JobStatus.PENDING is not None
        assert JobStatus.COMPLETED is not None

    def test_import_audio_asset(self):
        from scenemachine.models import AudioAsset, AudioAssetType

        assert hasattr(AudioAsset, "__tablename__")
        assert AudioAssetType.SOUND_EFFECT is not None
        assert AudioAssetType.MUSIC is not None

    def test_import_text_overlay(self):
        from scenemachine.models import TextAnimation, TextOverlay, TextOverlayType, TextPosition

        assert hasattr(TextOverlay, "__tablename__")
        assert TextOverlayType.TITLE is not None
        assert TextPosition.CENTER is not None
        assert TextAnimation.FADE_IN is not None

    def test_import_share_models(self):
        from scenemachine.models import ProjectShare, SharePermission

        assert hasattr(ProjectShare, "__tablename__")
        assert SharePermission.VIEW is not None
        assert SharePermission.EDIT is not None

    def test_import_settings(self):
        from scenemachine.models import LLMProvider, UserSettings, VideoProvider

        assert hasattr(UserSettings, "__tablename__")
        assert LLMProvider.ANTHROPIC is not None
        assert VideoProvider.REPLICATE is not None

    # ============ SERVICE IMPORT TESTS ============

    def test_import_assembly_service(self):
        from scenemachine.services.assembly import (
            AssemblyService,
            ExportFormat,
        )

        assert AssemblyService is not None
        assert ExportFormat.MP4_H264 is not None

    def test_import_generation_providers(self):
        from scenemachine.generators import (
            GenerationProvider,
            MockGenerationProvider,
            ReplicateProvider,
        )

        assert GenerationProvider is not None
        assert ReplicateProvider is not None
        assert MockGenerationProvider is not None

    def test_import_audio_library(self):
        from scenemachine.services.audio_library import AudioLibraryService

        assert AudioLibraryService is not None

    def test_import_cost_tracking(self):
        from scenemachine.services.cost_tracking import CostTrackingService

        assert CostTrackingService is not None

    def test_import_character_service(self):
        from scenemachine.services.character import CharacterService

        assert CharacterService is not None

    def test_import_scene_planning(self):
        from scenemachine.services.scene_planning import ScenePlanningService

        assert ScenePlanningService is not None

    # ============ API ROUTE TESTS ============

    def test_import_projects_routes(self):
        from scenemachine.api.routes import projects

        assert hasattr(projects, "router")

    def test_import_characters_routes(self):
        from scenemachine.api.routes import characters

        assert hasattr(characters, "router")

    def test_import_scenes_routes(self):
        from scenemachine.api.routes import scenes

        assert hasattr(scenes, "router")

    def test_import_generation_routes(self):
        from scenemachine.api.routes import generation

        assert hasattr(generation, "router")

    def test_import_assembly_routes(self):
        from scenemachine.api.routes import assembly

        assert hasattr(assembly, "router")

    def test_import_analytics_routes(self):
        from scenemachine.api.routes import analytics

        assert hasattr(analytics, "router")

    def test_import_sharing_routes(self):
        from scenemachine.api.routes import sharing

        assert hasattr(sharing, "router")

    def test_import_settings_routes(self):
        from scenemachine.api.routes import settings

        assert hasattr(settings, "router")

    def test_import_audio_routes(self):
        from scenemachine.api.routes import audio

        assert hasattr(audio, "router")

    def test_import_text_overlay_routes(self):
        from scenemachine.api.routes import text_overlays

        assert hasattr(text_overlays, "router")

    # ============ IPC TESTS ============

    def test_import_ipc_handlers(self):
        from scenemachine.ipc import handlers

        assert handlers is not None

    def test_ipc_handler_count(self):
        """Verify minimum number of IPC handlers exist."""
        # Read the file and count handler decorators
        handler_file = Path(__file__).parent.parent / "scenemachine" / "ipc" / "handlers.py"
        content = handler_file.read_text()
        handler_count = content.count("@server.handler(")
        assert handler_count >= 50, f"Expected at least 50 handlers, found {handler_count}"
        self.report.module_stats["ipc_handlers"] = {"count": handler_count}

    # ============ UTILITY TESTS ============

    def test_import_ffmpeg(self):
        from scenemachine.utils.ffmpeg import FFmpeg, FFmpegValidator

        assert FFmpeg is not None
        assert FFmpegValidator is not None

    def test_import_circuit_breaker(self):
        from scenemachine.utils.circuit_breaker import (
            CircuitBreaker,
            CircuitState,
        )

        assert CircuitBreaker is not None
        assert CircuitState.CLOSED is not None
        assert CircuitState.OPEN is not None

    def test_import_caching(self):
        from scenemachine.utils.cache import FileCache, LRUCache, cached

        assert LRUCache is not None
        assert FileCache is not None
        assert cached is not None

    def test_import_logging(self):
        from scenemachine.utils.logging import setup_logging

        assert setup_logging is not None

    # ============ PARSER TESTS ============

    def test_import_fountain_parser(self):
        from scenemachine.parsers.fountain import FountainParser

        assert FountainParser is not None

    def test_import_pdf_parser(self):
        from scenemachine.parsers.pdf import PDFParser

        assert PDFParser is not None

    def test_parsers_module(self):
        from scenemachine import parsers

        assert parsers is not None
        assert hasattr(parsers, "FountainParser") or hasattr(parsers, "fountain")

    # ============ ENUM TESTS ============

    def test_project_state_enum(self):
        from scenemachine.models import ProjectState

        states = list(ProjectState)
        assert len(states) >= 5
        state_names = [s.name for s in states]
        assert "EMPTY" in state_names or "SCREENPLAY_UPLOADED" in state_names

    def test_shot_type_enum(self):
        from scenemachine.models import ShotType

        types = list(ShotType)
        assert len(types) >= 10
        type_names = [t.value for t in types]
        assert any("wide" in t.lower() or "close" in t.lower() for t in type_names)

    def test_camera_movement_enum(self):
        from scenemachine.models import CameraMovement

        movements = list(CameraMovement)
        assert len(movements) >= 5
        movement_names = [m.value for m in movements]
        assert any("static" in m.lower() or "pan" in m.lower() for m in movement_names)

    def test_job_status_enum(self):
        from scenemachine.models import JobStatus

        statuses = list(JobStatus)
        status_names = [s.name for s in statuses]
        assert "PENDING" in status_names
        assert "COMPLETED" in status_names
        assert "FAILED" in status_names

    def test_text_animation_enum(self):
        from scenemachine.models import TextAnimation

        animations = list(TextAnimation)
        assert len(animations) >= 5
        anim_names = [a.value for a in animations]
        assert "none" in anim_names
        assert "fade_in" in anim_names

    # ============ FUNCTIONALITY TESTS ============

    def test_fountain_parsing(self):
        from scenemachine.parsers.fountain import FountainParser

        parser = FountainParser()
        sample = """
INT. COFFEE SHOP - DAY

JOHN enters and looks around.

JOHN
Hello, is anyone here?
"""
        result = parser.parse(sample)
        assert result is not None
        # Result is a ParsedScreenplay object
        assert hasattr(result, "scenes") or hasattr(result, "title")

    def test_export_settings(self):
        from scenemachine.services.assembly import ExportFormat, ExportQuality, ExportSettings

        settings = ExportSettings()
        assert settings.format == ExportFormat.MP4_H264
        assert settings.quality == ExportQuality.HIGH
        assert settings.resolution == "1920x1080"
        assert settings.frame_rate == 24
        assert settings.include_audio
        assert settings.include_text_overlays

    def test_color_grade_settings(self):
        from scenemachine.services.assembly import ColorGradeSettings

        grade = ColorGradeSettings(
            exposure=0.5,
            contrast=10,
            saturation=-5,
            lut_path="/path/to/lut.cube",
            lut_intensity=80.0,
        )
        assert grade.exposure == 0.5
        assert grade.lut_intensity == 80.0

    def test_circuit_breaker_states(self):
        from scenemachine.utils.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState,
        )

        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30, success_threshold=2)
        cb = CircuitBreaker(name="test", config=config)
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_failures == 0

    def test_cost_estimation(self):
        from scenemachine.services.cost_tracking import CostTrackingService

        # Verify class has expected methods
        assert hasattr(CostTrackingService, "estimate_generation_cost")
        assert hasattr(CostTrackingService, "get_project_costs")

    # ============ INTEGRATION TESTS ============

    def test_api_app_creation(self):
        from scenemachine.api.app import create_app

        # Test the factory function exists and is callable
        assert create_app is not None
        assert callable(create_app)

    def test_route_registration(self):
        # Test individual routers can be imported with their router attributes
        from scenemachine.api.routes import characters, projects, scenes

        assert hasattr(projects, "router")
        assert hasattr(characters, "router")
        assert hasattr(scenes, "router")

    def test_model_relationships(self):
        from scenemachine.models import Project, Scene, Shot

        # Check relationship attributes exist
        assert hasattr(Project, "scenes")
        assert hasattr(Project, "characters")
        assert hasattr(Scene, "shots")
        assert hasattr(Scene, "project")
        assert hasattr(Shot, "scene")

    # ============ PHASE 15-22 FEATURE TESTS ============

    def test_import_queue_worker(self):
        from scenemachine.services.queue_worker import QueueWorker, WorkerStats

        assert QueueWorker is not None
        assert WorkerStats is not None

    def test_import_job_queue(self):
        from scenemachine.services.job_queue import BackgroundJobQueue, JobPriority

        assert BackgroundJobQueue is not None
        assert JobPriority.HIGH is not None

    def test_import_export_history(self):
        from scenemachine.models import ExportHistory

        assert hasattr(ExportHistory, "__tablename__")
        assert ExportHistory.__tablename__ == "export_history"

    def test_import_comfyui_provider(self):
        from scenemachine.generators.comfyui import ComfyUIProvider

        assert ComfyUIProvider is not None

    def test_import_runpod_provider(self):
        from scenemachine.generators.runpod import RunPodProvider

        assert RunPodProvider is not None

    def test_import_provider_registry(self):
        from scenemachine.generators.registry import ProviderRegistry, get_provider_registry

        assert ProviderRegistry is not None
        assert get_provider_registry is not None
        # Note: Don't instantiate here as it may need settings
        assert hasattr(ProviderRegistry, "register")

    def test_import_rate_limiter(self):
        from scenemachine.api.middleware.security import RateLimitMiddleware, TokenBucket

        assert RateLimitMiddleware is not None
        assert TokenBucket is not None

    def test_import_security_middleware(self):
        from scenemachine.api.middleware.security import (
            RequestValidationMiddleware,
            SecurityHeadersMiddleware,
        )

        assert SecurityHeadersMiddleware is not None
        assert RequestValidationMiddleware is not None

    def test_import_shortcuts_manager(self):
        # Frontend-only, test that the TypeScript file exists
        shortcuts_path = (
            Path(__file__).parent.parent.parent.parent
            / "apps"
            / "desktop"
            / "src"
            / "renderer"
            / "lib"
            / "shortcuts-manager.ts"
        )
        assert shortcuts_path.exists(), f"Shortcuts manager not found at {shortcuts_path}"

    def test_import_watermarks_routes(self):
        from scenemachine.api.routes import watermarks

        assert hasattr(watermarks, "router")

    def test_import_archive_routes(self):
        from scenemachine.api.routes import archive

        assert hasattr(archive, "router")

    def test_import_health_routes(self):
        from scenemachine.api.routes import health

        assert hasattr(health, "router")

    def test_import_project_duplicator(self):
        from scenemachine.services.project_duplicator import ProjectDuplicator

        assert ProjectDuplicator is not None
        assert hasattr(ProjectDuplicator, "duplicate")


class SmokeTestSuite:
    """
    Wrapper class for the master hardening suite to use.
    Returns results in dictionary format for integration.
    """

    def __init__(self):
        self.smoke_test = SmokeTest()

    def run_all(self) -> dict[str, dict[str, Any]]:
        """
        Run all smoke tests and return results as a dictionary.

        Returns:
            Dict mapping test names to their results with keys:
            - passed: bool
            - duration_ms: float
            - error: Optional[str]
            - details: Optional[Dict]
        """
        self.smoke_test.run_all_tests()

        results = {}
        for result in self.smoke_test.report.results:
            results[result.name] = {
                "passed": result.passed,
                "duration_ms": result.duration_ms,
                "error": result.message if not result.passed else None,
                "details": result.details if result.details else None,
                "category": result.category,
            }

        return results

    @property
    def report(self) -> SmokeTestReport:
        """Access the underlying smoke test report."""
        return self.smoke_test.report


def main():
    """Main entry point."""
    smoke_test = SmokeTest()
    smoke_test.run_all_tests()

    # Generate and print report
    report_text = smoke_test.report.generate_report()
    print(report_text)

    # Save report to file
    report_path = Path(__file__).parent.parent / "data" / "smoke_test_report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report_text)
    logger.info(f"Report saved to: {report_path}")

    # Return exit code
    return 0 if smoke_test.report.failed_tests == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
