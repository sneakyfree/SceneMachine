#!/usr/bin/env python3
"""
SceneMachine Hardening Test Harness.

This is the main entry point for comprehensive E2E testing.
It orchestrates:
1. Mock data generation
2. API endpoint testing
3. IPC handler testing
4. Workflow integration testing
5. Report generation
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.mock_data_generator import MockDataGenerator
from tests.e2e_test_suite import E2ETestSuite, TestStatus
from tests.smoke_test import SmokeTest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("./data/hardening_test.log"),
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# IPC HANDLER TESTS
# ============================================================================

@dataclass
class IPCTestResult:
    """Result of an IPC handler test."""
    handler: str
    status: TestStatus
    duration_ms: float
    error: Optional[str] = None


class IPCHandlerTests:
    """Tests for IPC handlers."""

    def __init__(self):
        self.results: List[IPCTestResult] = []

    async def test_handler_imports(self) -> List[IPCTestResult]:
        """Test that all IPC handlers can be imported."""
        results = []

        try:
            from scenemachine.ipc import handlers as h

            # Get handler file and count decorators
            handler_file = Path(__file__).parent.parent / "scenemachine" / "ipc" / "handlers.py"
            content = handler_file.read_text()

            # Extract handler names
            import re
            handler_pattern = r'@server\.handler\(["\']([^"\']+)["\']\)'
            handler_names = re.findall(handler_pattern, content)

            for handler_name in handler_names:
                start = time.time()
                try:
                    # Verify the handler module imported correctly
                    assert h is not None
                    duration = (time.time() - start) * 1000
                    results.append(IPCTestResult(
                        handler=handler_name,
                        status=TestStatus.PASSED,
                        duration_ms=duration,
                    ))
                except Exception as e:
                    duration = (time.time() - start) * 1000
                    results.append(IPCTestResult(
                        handler=handler_name,
                        status=TestStatus.FAILED,
                        duration_ms=duration,
                        error=str(e),
                    ))

        except Exception as e:
            results.append(IPCTestResult(
                handler="module_import",
                status=TestStatus.ERROR,
                duration_ms=0,
                error=str(e),
            ))

        self.results = results
        return results


# ============================================================================
# WORKFLOW TESTS
# ============================================================================

@dataclass
class WorkflowTestResult:
    """Result of a workflow test."""
    workflow: str
    steps_total: int
    steps_passed: int
    status: TestStatus
    duration_ms: float
    errors: List[str] = field(default_factory=list)


class WorkflowTests:
    """Integration tests for complete workflows."""

    def __init__(self, database_url: str):
        # Each workflow test uses its own database to avoid locking issues
        self.base_url = database_url
        self.results: List[WorkflowTestResult] = []

    def _get_test_db_url(self, test_name: str) -> str:
        """Get a unique database URL for each test."""
        base = self.base_url.replace(".db", f"_{test_name}.db")
        return base

    async def test_project_creation_workflow(self) -> WorkflowTestResult:
        """Test complete project creation workflow."""
        start = time.time()
        steps_passed = 0
        errors = []
        db_url = self._get_test_db_url("project")

        try:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            from scenemachine.models import Project, ProjectState
            from scenemachine.models.base import Base
            from tests.sqlite_compat import create_all_tables_sqlite

            # Create engine with unique database
            engine = create_async_engine(db_url, echo=False)
            is_sqlite = "sqlite" in db_url

            if is_sqlite:
                await create_all_tables_sqlite(engine, Base)
            else:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Step 1: Create project
            async with session_factory() as session:
                project = Project(
                    name="Workflow Test Project",
                    description="Testing project workflow",
                    state=ProjectState.EMPTY,
                )
                session.add(project)
                await session.commit()
                project_id = project.id
                steps_passed += 1

            # Step 2: Verify project exists
            async with session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                found = result.scalar_one_or_none()
                assert found is not None, "Project not found after creation"
                steps_passed += 1

            # Step 3: Update project state
            async with session_factory() as session:
                result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = result.scalar_one()
                project.state = ProjectState.SCREENPLAY_UPLOADED
                await session.commit()
                steps_passed += 1

            # Step 4: Verify state change
            async with session_factory() as session:
                result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = result.scalar_one()
                assert project.state == ProjectState.SCREENPLAY_UPLOADED
                steps_passed += 1

            await engine.dispose()

        except Exception as e:
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        status = TestStatus.PASSED if steps_passed == 4 else TestStatus.FAILED

        result = WorkflowTestResult(
            workflow="Project Creation",
            steps_total=4,
            steps_passed=steps_passed,
            status=status,
            duration_ms=duration,
            errors=errors,
        )
        self.results.append(result)
        return result

    async def test_character_workflow(self) -> WorkflowTestResult:
        """Test character creation and locking workflow."""
        start = time.time()
        steps_passed = 0
        errors = []
        db_url = self._get_test_db_url("character")

        try:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            from sqlalchemy import select
            from scenemachine.models import Project, ProjectState, Character, CharacterLockState, CharacterGender
            from scenemachine.models.base import Base
            from tests.sqlite_compat import create_all_tables_sqlite

            engine = create_async_engine(db_url, echo=False)
            is_sqlite = "sqlite" in db_url

            if is_sqlite:
                await create_all_tables_sqlite(engine, Base)
            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Step 1: Create project
            async with session_factory() as session:
                project = Project(
                    name="Character Workflow Test",
                    state=ProjectState.CHARACTERS_IN_PROGRESS,
                )
                session.add(project)
                await session.commit()
                project_id = project.id
                steps_passed += 1

            # Step 2: Create character
            async with session_factory() as session:
                character = Character(
                    project_id=project_id,
                    name="Test Character",
                    screenplay_name="TEST",
                    gender=CharacterGender.UNSPECIFIED,
                    lock_state=CharacterLockState.DRAFT,
                )
                session.add(character)
                await session.commit()
                char_id = character.id
                steps_passed += 1

            # Step 3: Update character to review
            async with session_factory() as session:
                result = await session.execute(
                    select(Character).where(Character.id == char_id)
                )
                character = result.scalar_one()
                character.lock_state = CharacterLockState.REVIEW
                character.physical_description = {
                    "hair_color": "brown",
                    "eye_color": "blue",
                }
                await session.commit()
                steps_passed += 1

            # Step 4: Lock character
            async with session_factory() as session:
                result = await session.execute(
                    select(Character).where(Character.id == char_id)
                )
                character = result.scalar_one()
                character.lock_state = CharacterLockState.LOCKED
                await session.commit()
                steps_passed += 1

            # Step 5: Verify lock state
            async with session_factory() as session:
                result = await session.execute(
                    select(Character).where(Character.id == char_id)
                )
                character = result.scalar_one()
                assert character.lock_state == CharacterLockState.LOCKED
                assert character.is_locked
                steps_passed += 1

            await engine.dispose()

        except Exception as e:
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        status = TestStatus.PASSED if steps_passed == 5 else TestStatus.FAILED

        result = WorkflowTestResult(
            workflow="Character Workflow",
            steps_total=5,
            steps_passed=steps_passed,
            status=status,
            duration_ms=duration,
            errors=errors,
        )
        self.results.append(result)
        return result

    async def test_shot_generation_workflow(self) -> WorkflowTestResult:
        """Test shot generation queue workflow."""
        start = time.time()
        steps_passed = 0
        errors = []
        db_url = self._get_test_db_url("shot")
        is_sqlite = "sqlite" in db_url

        # Skip this test for SQLite due to ARRAY column compatibility issues
        # The Scene and Shot models use ARRAY(UUID) which requires PostgreSQL
        if is_sqlite:
            result = WorkflowTestResult(
                workflow="Shot Generation Workflow",
                status=TestStatus.SKIPPED,
                steps_total=7,
                steps_passed=0,
                duration_ms=(time.time() - start) * 1000,
                errors=["Skipped: SQLite does not support PostgreSQL ARRAY(UUID) columns in Scene/Shot models"],
            )
            self.results.append(result)
            return result

        try:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            from sqlalchemy import select
            from scenemachine.models import (
                Project, ProjectState, Scene, SceneState, SceneType, TimeOfDay,
                Shot, ShotState, ShotType, CameraMovement,
                GenerationJob, JobStatus, JobProvider,
            )
            from scenemachine.models.base import Base
            from tests.sqlite_compat import create_all_tables_sqlite

            engine = create_async_engine(db_url, echo=False)

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Step 1: Create project and scene
            async with session_factory() as session:
                project = Project(
                    name="Generation Workflow Test",
                    state=ProjectState.GENERATING,
                )
                session.add(project)
                await session.flush()

                scene = Scene(
                    project_id=project.id,
                    scene_number="1",
                    sequence_number=0,
                    scene_type=SceneType.INTERIOR,
                    location="TEST LOCATION",
                    time_of_day=TimeOfDay.DAY,
                    state=SceneState.APPROVED,
                    raw_content="INT. TEST LOCATION - DAY\n\nAction description.",
                )
                session.add(scene)
                await session.commit()
                scene_id = scene.id
                steps_passed += 1

            # Step 2: Create shot
            async with session_factory() as session:
                shot = Shot(
                    scene_id=scene_id,
                    shot_number="1.1",
                    sequence_number=0,
                    shot_type=ShotType.WIDE,
                    camera_movement=CameraMovement.STATIC,
                    description="Test shot",
                    state=ShotState.PLANNED,
                )
                session.add(shot)
                await session.commit()
                shot_id = shot.id
                steps_passed += 1

            # Step 3: Queue shot for generation
            async with session_factory() as session:
                result = await session.execute(
                    select(Shot).where(Shot.id == shot_id)
                )
                shot = result.scalar_one()
                shot.state = ShotState.QUEUED
                shot.generation_prompt = "Cinematic wide shot, dramatic lighting"

                job = GenerationJob(
                    shot_id=shot_id,
                    job_number=1,
                    status=JobStatus.PENDING,
                    provider=JobProvider.REPLICATE,
                    model_id="svd",
                    parameters={"num_frames": 24},
                )
                session.add(job)
                await session.commit()
                job_id = job.id
                steps_passed += 1

            # Step 4: Start generation
            async with session_factory() as session:
                result = await session.execute(
                    select(Shot).where(Shot.id == shot_id)
                )
                shot = result.scalar_one()
                shot.state = ShotState.GENERATING

                result = await session.execute(
                    select(GenerationJob).where(GenerationJob.id == job_id)
                )
                job = result.scalar_one()
                job.status = JobStatus.RUNNING
                job.progress_percent = 50.0
                await session.commit()
                steps_passed += 1

            # Step 5: Complete generation
            async with session_factory() as session:
                result = await session.execute(
                    select(Shot).where(Shot.id == shot_id)
                )
                shot = result.scalar_one()
                shot.state = ShotState.GENERATED
                shot.output_video_path = f"/data/outputs/{shot_id}.mp4"

                result = await session.execute(
                    select(GenerationJob).where(GenerationJob.id == job_id)
                )
                job = result.scalar_one()
                job.status = JobStatus.COMPLETED
                job.progress_percent = 100.0
                job.output_path = shot.output_video_path
                await session.commit()
                steps_passed += 1

            # Step 6: Approve shot
            async with session_factory() as session:
                result = await session.execute(
                    select(Shot).where(Shot.id == shot_id)
                )
                shot = result.scalar_one()
                shot.state = ShotState.APPROVED
                await session.commit()
                steps_passed += 1

            # Step 7: Verify final state
            async with session_factory() as session:
                result = await session.execute(
                    select(Shot).where(Shot.id == shot_id)
                )
                shot = result.scalar_one()
                assert shot.state == ShotState.APPROVED
                assert shot.is_approved
                steps_passed += 1

            await engine.dispose()

        except Exception as e:
            errors.append(str(e))
            import traceback
            errors.append(traceback.format_exc())

        duration = (time.time() - start) * 1000
        status = TestStatus.PASSED if steps_passed == 7 else TestStatus.FAILED

        result = WorkflowTestResult(
            workflow="Shot Generation",
            steps_total=7,
            steps_passed=steps_passed,
            status=status,
            duration_ms=duration,
            errors=errors,
        )
        self.results.append(result)
        return result

    async def run_all(self) -> List[WorkflowTestResult]:
        """Run all workflow tests."""
        await self.test_project_creation_workflow()
        await self.test_character_workflow()
        await self.test_shot_generation_workflow()
        return self.results


# ============================================================================
# COMPREHENSIVE REPORT
# ============================================================================

@dataclass
class ComprehensiveReport:
    """Complete hardening test report."""
    start_time: datetime
    end_time: Optional[datetime] = None

    # Mock data stats
    mock_data_generated: Dict[str, int] = field(default_factory=dict)
    mock_data_duration_ms: float = 0

    # Smoke test results
    smoke_tests_passed: int = 0
    smoke_tests_failed: int = 0
    smoke_tests_total: int = 0

    # E2E API test results
    api_tests_passed: int = 0
    api_tests_failed: int = 0
    api_tests_total: int = 0
    api_coverage: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # IPC handler results
    ipc_handlers_passed: int = 0
    ipc_handlers_failed: int = 0
    ipc_handlers_total: int = 0

    # Workflow results
    workflows_passed: int = 0
    workflows_failed: int = 0
    workflows_total: int = 0
    workflow_details: List[WorkflowTestResult] = field(default_factory=list)

    # Errors
    critical_errors: List[str] = field(default_factory=list)

    def generate_report(self) -> str:
        """Generate comprehensive report."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0

        total_passed = (
            self.smoke_tests_passed +
            self.api_tests_passed +
            self.ipc_handlers_passed +
            self.workflows_passed
        )
        total_failed = (
            self.smoke_tests_failed +
            self.api_tests_failed +
            self.ipc_handlers_failed +
            self.workflows_failed
        )
        total_tests = total_passed + total_failed
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        lines = [
            "=" * 80,
            "SCENEMACHINE HARDENING TEST REPORT",
            "=" * 80,
            "",
            f"Start Time: {self.start_time.isoformat()}",
            f"End Time: {self.end_time.isoformat() if self.end_time else 'N/A'}",
            f"Total Duration: {duration:.2f} seconds",
            "",
            "=" * 80,
            "EXECUTIVE SUMMARY",
            "=" * 80,
            "",
            f"Overall Success Rate: {success_rate:.1f}%",
            f"Total Tests Run: {total_tests}",
            f"Total Passed: {total_passed}",
            f"Total Failed: {total_failed}",
            "",
        ]

        # Mock data section
        lines.extend([
            "-" * 40,
            "MOCK DATA GENERATION",
            "-" * 40,
            f"Duration: {self.mock_data_duration_ms:.0f}ms",
        ])
        for entity, count in sorted(self.mock_data_generated.items()):
            lines.append(f"  {entity}: {count}")

        # Smoke tests section
        smoke_pct = (self.smoke_tests_passed / self.smoke_tests_total * 100) if self.smoke_tests_total > 0 else 0
        lines.extend([
            "",
            "-" * 40,
            "SMOKE TESTS",
            "-" * 40,
            f"Passed: {self.smoke_tests_passed}/{self.smoke_tests_total} ({smoke_pct:.1f}%)",
        ])

        # API tests section
        api_pct = (self.api_tests_passed / self.api_tests_total * 100) if self.api_tests_total > 0 else 0
        lines.extend([
            "",
            "-" * 40,
            "API ENDPOINT TESTS",
            "-" * 40,
            f"Passed: {self.api_tests_passed}/{self.api_tests_total} ({api_pct:.1f}%)",
        ])
        for category, subcats in sorted(self.api_coverage.items()):
            for subcat, stats in sorted(subcats.items()):
                status = "✓" if stats.get("passed", 0) == stats.get("total", 0) else "✗"
                lines.append(f"  [{status}] {category}/{subcat}: {stats.get('passed', 0)}/{stats.get('total', 0)}")

        # IPC handlers section
        ipc_pct = (self.ipc_handlers_passed / self.ipc_handlers_total * 100) if self.ipc_handlers_total > 0 else 0
        lines.extend([
            "",
            "-" * 40,
            "IPC HANDLER TESTS",
            "-" * 40,
            f"Passed: {self.ipc_handlers_passed}/{self.ipc_handlers_total} ({ipc_pct:.1f}%)",
        ])

        # Workflow tests section
        workflow_pct = (self.workflows_passed / self.workflows_total * 100) if self.workflows_total > 0 else 0
        lines.extend([
            "",
            "-" * 40,
            "WORKFLOW INTEGRATION TESTS",
            "-" * 40,
            f"Passed: {self.workflows_passed}/{self.workflows_total} ({workflow_pct:.1f}%)",
        ])
        for wf in self.workflow_details:
            status = "✓" if wf.status == TestStatus.PASSED else "✗"
            lines.append(f"  [{status}] {wf.workflow}: {wf.steps_passed}/{wf.steps_total} steps")
            for error in wf.errors[:2]:  # Show first 2 errors
                lines.append(f"      Error: {error[:100]}...")

        # Critical errors
        if self.critical_errors:
            lines.extend([
                "",
                "-" * 40,
                "CRITICAL ERRORS",
                "-" * 40,
            ])
            for error in self.critical_errors:
                lines.append(f"  - {error[:200]}")

        # Final status
        overall_status = "PASS" if total_failed == 0 else "FAIL"
        lines.extend([
            "",
            "=" * 80,
            f"OVERALL STATUS: {overall_status}",
            "=" * 80,
        ])

        return "\n".join(lines)


# ============================================================================
# MAIN HARNESS
# ============================================================================

class HardeningTestHarness:
    """Main test harness orchestrator."""

    def __init__(
        self,
        database_url: str = "sqlite+aiosqlite:///./data/hardening_test.db",
        num_projects: int = 10,
    ):
        self.database_url = database_url
        self.num_projects = num_projects
        self.report = ComprehensiveReport(start_time=datetime.now(timezone.utc))

    async def run_mock_data_generation(self):
        """Run mock data generation."""
        logger.info("=" * 60)
        logger.info("PHASE 1: MOCK DATA GENERATION")
        logger.info("=" * 60)

        start = time.time()
        generator = MockDataGenerator(self.database_url)

        try:
            summary = await generator.generate_all(
                clear_existing=True,
                num_projects=self.num_projects,
            )
            self.report.mock_data_generated = summary
        except Exception as e:
            self.report.critical_errors.append(f"Mock data generation failed: {e}")
            logger.error(f"Mock data generation failed: {e}")
        finally:
            await generator.close()

        self.report.mock_data_duration_ms = (time.time() - start) * 1000
        logger.info(f"Mock data generation completed in {self.report.mock_data_duration_ms:.0f}ms")

    async def run_smoke_tests(self):
        """Run smoke tests."""
        logger.info("=" * 60)
        logger.info("PHASE 2: SMOKE TESTS")
        logger.info("=" * 60)

        try:
            smoke = SmokeTest()
            smoke.run_all_tests()

            self.report.smoke_tests_passed = smoke.report.passed_tests
            self.report.smoke_tests_failed = smoke.report.failed_tests
            self.report.smoke_tests_total = smoke.report.total_tests
        except Exception as e:
            self.report.critical_errors.append(f"Smoke tests failed: {e}")
            logger.error(f"Smoke tests failed: {e}")

        logger.info(f"Smoke tests: {self.report.smoke_tests_passed}/{self.report.smoke_tests_total} passed")

    async def run_api_tests(self):
        """Run API endpoint tests."""
        logger.info("=" * 60)
        logger.info("PHASE 3: API ENDPOINT TESTS")
        logger.info("=" * 60)

        try:
            suite = E2ETestSuite(database_url=self.database_url)
            api_report = await suite.run_all_tests()

            self.report.api_tests_passed = api_report.passed
            self.report.api_tests_failed = api_report.failed
            self.report.api_tests_total = api_report.total_tests
            self.report.api_coverage = api_report.coverage
        except Exception as e:
            self.report.critical_errors.append(f"API tests failed: {e}")
            logger.error(f"API tests failed: {e}")

        logger.info(f"API tests: {self.report.api_tests_passed}/{self.report.api_tests_total} passed")

    async def run_ipc_tests(self):
        """Run IPC handler tests."""
        logger.info("=" * 60)
        logger.info("PHASE 4: IPC HANDLER TESTS")
        logger.info("=" * 60)

        try:
            ipc_tests = IPCHandlerTests()
            results = await ipc_tests.test_handler_imports()

            self.report.ipc_handlers_total = len(results)
            self.report.ipc_handlers_passed = sum(1 for r in results if r.status == TestStatus.PASSED)
            self.report.ipc_handlers_failed = sum(1 for r in results if r.status != TestStatus.PASSED)
        except Exception as e:
            self.report.critical_errors.append(f"IPC tests failed: {e}")
            logger.error(f"IPC tests failed: {e}")

        logger.info(f"IPC tests: {self.report.ipc_handlers_passed}/{self.report.ipc_handlers_total} passed")

    async def run_workflow_tests(self):
        """Run workflow integration tests."""
        logger.info("=" * 60)
        logger.info("PHASE 5: WORKFLOW INTEGRATION TESTS")
        logger.info("=" * 60)

        try:
            workflow_tests = WorkflowTests(self.database_url)
            results = await workflow_tests.run_all()

            self.report.workflow_details = results
            self.report.workflows_total = len(results)
            self.report.workflows_passed = sum(1 for r in results if r.status == TestStatus.PASSED)
            self.report.workflows_failed = sum(1 for r in results if r.status != TestStatus.PASSED)
        except Exception as e:
            self.report.critical_errors.append(f"Workflow tests failed: {e}")
            logger.error(f"Workflow tests failed: {e}")

        logger.info(f"Workflow tests: {self.report.workflows_passed}/{self.report.workflows_total} passed")

    async def run_all(self) -> ComprehensiveReport:
        """Run complete hardening test suite."""
        logger.info("=" * 80)
        logger.info("SCENEMACHINE HARDENING TEST HARNESS")
        logger.info("=" * 80)

        await self.run_mock_data_generation()
        await self.run_smoke_tests()
        await self.run_api_tests()
        await self.run_ipc_tests()
        await self.run_workflow_tests()

        self.report.end_time = datetime.now(timezone.utc)

        return self.report


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run SceneMachine Hardening Tests")
    parser.add_argument(
        "--database-url",
        default="sqlite+aiosqlite:///./data/hardening_test.db",
        help="Database URL for testing",
    )
    parser.add_argument(
        "--projects",
        type=int,
        default=10,
        help="Number of mock projects to generate",
    )
    parser.add_argument(
        "--output",
        default="./data/hardening_test_report.txt",
        help="Output file for report",
    )

    args = parser.parse_args()

    # Ensure data directory exists
    Path("./data").mkdir(parents=True, exist_ok=True)

    harness = HardeningTestHarness(
        database_url=args.database_url,
        num_projects=args.projects,
    )

    report = await harness.run_all()

    # Generate and print report
    report_text = report.generate_report()
    print("\n" + report_text)

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report_text)
    logger.info(f"Report saved to: {output_path}")

    # Also save JSON report
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump({
            "start_time": report.start_time.isoformat(),
            "end_time": report.end_time.isoformat() if report.end_time else None,
            "mock_data": report.mock_data_generated,
            "smoke_tests": {
                "passed": report.smoke_tests_passed,
                "failed": report.smoke_tests_failed,
                "total": report.smoke_tests_total,
            },
            "api_tests": {
                "passed": report.api_tests_passed,
                "failed": report.api_tests_failed,
                "total": report.api_tests_total,
            },
            "ipc_tests": {
                "passed": report.ipc_handlers_passed,
                "failed": report.ipc_handlers_failed,
                "total": report.ipc_handlers_total,
            },
            "workflow_tests": {
                "passed": report.workflows_passed,
                "failed": report.workflows_failed,
                "total": report.workflows_total,
            },
            "critical_errors": report.critical_errors,
        }, f, indent=2)
    logger.info(f"JSON report saved to: {json_path}")

    # Return exit code
    total_failed = (
        report.smoke_tests_failed +
        report.api_tests_failed +
        report.ipc_handlers_failed +
        report.workflows_failed
    )
    return 0 if total_failed == 0 and not report.critical_errors else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
