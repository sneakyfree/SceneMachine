"""Beta Testing Harness for SceneMachine.

Provides structured test scenarios for beta testers with:
- Session recording
- Feedback collection
- Success/failure tracking
- UX friction point identification

Usage:
    python -m pytest tests/beta_testing_harness.py -v --html=beta_report.html
"""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

# =============================================================================
# Data Models
# =============================================================================


class TestOutcome(Enum):
    """Outcome of a test scenario."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class FrictionLevel(Enum):
    """Level of UX friction encountered."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKING = "blocking"


@dataclass
class TestStep:
    """A single step in a test scenario."""

    step_number: int
    description: str
    expected_result: str
    actual_result: str | None = None
    passed: bool | None = None
    duration_seconds: float = 0.0
    friction_level: FrictionLevel = FrictionLevel.NONE
    notes: str = ""
    screenshot_path: str | None = None


@dataclass
class TestScenario:
    """A complete test scenario with multiple steps."""

    scenario_id: str
    name: str
    description: str
    steps: list[TestStep]
    outcome: TestOutcome = TestOutcome.SKIPPED
    total_duration_seconds: float = 0.0
    tester_id: str | None = None
    session_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    feedback: str = ""
    severity_score: int = 0  # 1-5 bug severity if found


@dataclass
class BetaSession:
    """A beta testing session."""

    session_id: str
    tester_id: str
    tester_name: str
    started_at: datetime
    completed_at: datetime | None = None
    scenarios: list[TestScenario] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    overall_feedback: str = ""
    nps_score: int | None = None  # 0-10 Net Promoter Score


# =============================================================================
# Test Scenarios
# =============================================================================

SCREENPLAY_IMPORT_SCENARIO = TestScenario(
    scenario_id="SC-001",
    name="Screenplay Import Workflow",
    description="Test importing a screenplay and verifying parsing results",
    steps=[
        TestStep(1, "Open SceneMachine application", "Application launches successfully"),
        TestStep(2, "Click 'New Project' button", "New project dialog appears"),
        TestStep(3, "Enter project name and click Create", "Project is created, main view shows"),
        TestStep(4, "Click 'Import Screenplay'", "File picker dialog appears"),
        TestStep(5, "Select a .fountain file and upload", "Upload progress shows, parsing begins"),
        TestStep(6, "Review parsing preview screen", "Title, scenes, and characters are shown"),
        TestStep(7, "Confirm parsing is correct", "Screenplay is imported, scenes listed"),
    ],
)

CHARACTER_LAB_SCENARIO = TestScenario(
    scenario_id="SC-002",
    name="Character Laboratory Setup",
    description="Test creating and locking a character with reference and voice",
    steps=[
        TestStep(1, "Navigate to Character Lab", "Character Lab page loads"),
        TestStep(2, "Click 'Add Character'", "Character form appears"),
        TestStep(3, "Enter character details (name, description)", "Fields accept input"),
        TestStep(4, "Click 'Generate with AI' for reference", "AI generates portrait options"),
        TestStep(5, "Select a generated portrait", "Portrait is set as reference"),
        TestStep(6, "Click 'Select Voice' and choose a voice", "Voice preview plays"),
        TestStep(7, "Click 'Lock Character'", "Character shows locked status ✅"),
    ],
)

GENERATION_SCENARIO = TestScenario(
    scenario_id="SC-003",
    name="Video Generation Workflow",
    description="Test generating video shots and monitoring progress",
    steps=[
        TestStep(1, "Navigate to Generation page", "Generation dashboard loads"),
        TestStep(2, "Review cost estimate", "Cost and time estimates displayed"),
        TestStep(3, "Click 'Start Generation'", "Confirmation dialog appears"),
        TestStep(4, "Approve generation", "Queue shows generation started"),
        TestStep(5, "Monitor progress in queue", "Progress updates in real-time"),
        TestStep(6, "Wait for at least one shot to complete", "Completed shot shows preview"),
        TestStep(7, "Review quality of generated shot", "Shot meets quality expectations"),
    ],
)

EXPORT_SCENARIO = TestScenario(
    scenario_id="SC-004",
    name="Export and Download Workflow",
    description="Test assembling and exporting final movie",
    steps=[
        TestStep(1, "Navigate to Timeline", "Timeline editor loads with clips"),
        TestStep(2, "Preview assembled movie", "Preview plays in player"),
        TestStep(3, "Click 'Export'", "Export options dialog appears"),
        TestStep(4, "Select YouTube preset", "Preset settings are applied"),
        TestStep(5, "Click 'Start Export'", "Export begins, progress shows"),
        TestStep(6, "Wait for export to complete", "Export shows 100% complete"),
        TestStep(7, "Download exported file", "File downloads successfully"),
    ],
)

EXPLAINABILITY_SCENARIO = TestScenario(
    scenario_id="SC-005",
    name="Explainability Dashboard Navigation",
    description="Test all four views of the explainability dashboard",
    steps=[
        TestStep(1, "Navigate to Explainability Dashboard", "Dashboard loads with tabs"),
        TestStep(2, "View Client tab", "Plain language summary shown"),
        TestStep(3, "View Operator tab", "Shot breakdown visible"),
        TestStep(4, "View Technical tab", "Logs and metrics displayed"),
        TestStep(5, "View Audit tab", "Snapshots listed"),
        TestStep(6, "Create a snapshot", "Snapshot is created with timestamp"),
        TestStep(7, "Compare two snapshots", "Delta report shows changes"),
    ],
)

ALL_SCENARIOS = [
    SCREENPLAY_IMPORT_SCENARIO,
    CHARACTER_LAB_SCENARIO,
    GENERATION_SCENARIO,
    EXPORT_SCENARIO,
    EXPLAINABILITY_SCENARIO,
]


# =============================================================================
# Test Runner
# =============================================================================


class BetaTestRunner:
    """Runs beta test scenarios and collects results."""

    def __init__(self, tester_id: str, tester_name: str):
        self.session = BetaSession(
            session_id=str(uuid4()),
            tester_id=tester_id,
            tester_name=tester_name,
            started_at=datetime.now(UTC),
            environment=self._collect_environment(),
        )
        self.results_dir = Path("beta_test_results")
        self.results_dir.mkdir(exist_ok=True)

    def _collect_environment(self) -> dict[str, Any]:
        """Collect environment information."""
        import platform

        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def run_scenario(self, scenario: TestScenario) -> TestScenario:
        """Run a single test scenario (interactive mode)."""
        print(f"\n{'=' * 60}")
        print(f"SCENARIO: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"{'=' * 60}\n")

        scenario.session_id = self.session.session_id
        scenario.tester_id = self.session.tester_id
        scenario.started_at = datetime.now(UTC)

        all_passed = True

        for step in scenario.steps:
            print(f"\nStep {step.step_number}: {step.description}")
            print(f"Expected: {step.expected_result}")

            step_start = time.time()

            # In real usage, tester would perform action and provide input
            # For automated testing, we simulate
            result = input("Result (p=passed, f=failed, s=skip, b=blocked): ").strip().lower()

            step.duration_seconds = time.time() - step_start

            if result == "p":
                step.passed = True
                step.actual_result = step.expected_result
            elif result == "f":
                step.passed = False
                step.actual_result = input("Actual result: ")
                step.notes = input("Notes: ")
                all_passed = False
            elif result == "s":
                step.passed = None
            elif result == "b":
                step.passed = False
                step.actual_result = "BLOCKED"
                step.notes = input("Blocking reason: ")
                scenario.outcome = TestOutcome.BLOCKED
                break

            friction = input("Friction level (0=none, 1=low, 2=medium, 3=high, 4=blocking): ")
            try:
                step.friction_level = [
                    FrictionLevel.NONE,
                    FrictionLevel.LOW,
                    FrictionLevel.MEDIUM,
                    FrictionLevel.HIGH,
                    FrictionLevel.BLOCKING,
                ][int(friction)]
            except (ValueError, IndexError):
                step.friction_level = FrictionLevel.NONE

        scenario.completed_at = datetime.now(UTC)
        scenario.total_duration_seconds = sum(s.duration_seconds for s in scenario.steps)

        if scenario.outcome != TestOutcome.BLOCKED:
            scenario.outcome = TestOutcome.PASSED if all_passed else TestOutcome.FAILED

        scenario.feedback = input("\nOverall feedback for this scenario: ")

        self.session.scenarios.append(scenario)
        return scenario

    def finalize_session(self) -> dict[str, Any]:
        """Finalize the testing session and generate report."""
        self.session.completed_at = datetime.now(UTC)
        self.session.overall_feedback = input("\nOverall feedback for SceneMachine: ")

        try:
            nps = input("On a scale of 0-10, how likely are you to recommend SceneMachine? ")
            self.session.nps_score = int(nps)
        except ValueError:
            self.session.nps_score = None

        report = self._generate_report()
        self._save_report(report)
        return report

    def _generate_report(self) -> dict[str, Any]:
        """Generate test session report."""
        passed = sum(1 for s in self.session.scenarios if s.outcome == TestOutcome.PASSED)
        failed = sum(1 for s in self.session.scenarios if s.outcome == TestOutcome.FAILED)
        blocked = sum(1 for s in self.session.scenarios if s.outcome == TestOutcome.BLOCKED)

        # Collect friction points
        friction_points = []
        for scenario in self.session.scenarios:
            for step in scenario.steps:
                if step.friction_level.value not in ["none", "low"]:
                    friction_points.append(
                        {
                            "scenario": scenario.name,
                            "step": step.step_number,
                            "description": step.description,
                            "friction_level": step.friction_level.value,
                            "notes": step.notes,
                        }
                    )

        return {
            "session_id": self.session.session_id,
            "tester": {
                "id": self.session.tester_id,
                "name": self.session.tester_name,
            },
            "environment": self.session.environment,
            "summary": {
                "total_scenarios": len(self.session.scenarios),
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "pass_rate": f"{passed / max(1, len(self.session.scenarios)) * 100:.1f}%",
            },
            "friction_points": friction_points,
            "nps_score": self.session.nps_score,
            "overall_feedback": self.session.overall_feedback,
            "scenarios": [
                {
                    "id": s.scenario_id,
                    "name": s.name,
                    "outcome": s.outcome.value,
                    "duration_seconds": s.total_duration_seconds,
                    "feedback": s.feedback,
                }
                for s in self.session.scenarios
            ],
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _save_report(self, report: dict[str, Any]):
        """Save report to file."""
        filename = f"beta_session_{self.session.session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.results_dir / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {filepath}")


# =============================================================================
# Automated Tests (for pytest)
# =============================================================================


class TestBetaScenarios:
    """Automated validation of beta test scenario definitions."""

    def test_all_scenarios_have_steps(self):
        """Verify all scenarios have at least 3 steps."""
        for scenario in ALL_SCENARIOS:
            assert len(scenario.steps) >= 3, f"{scenario.name} has too few steps"

    def test_all_steps_have_descriptions(self):
        """Verify all steps have descriptions and expected results."""
        for scenario in ALL_SCENARIOS:
            for step in scenario.steps:
                assert step.description, (
                    f"Step {step.step_number} in {scenario.name} missing description"
                )
                assert step.expected_result, (
                    f"Step {step.step_number} in {scenario.name} missing expected result"
                )

    def test_scenario_ids_unique(self):
        """Verify all scenario IDs are unique."""
        ids = [s.scenario_id for s in ALL_SCENARIOS]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_step_numbers_sequential(self):
        """Verify step numbers are sequential."""
        for scenario in ALL_SCENARIOS:
            for i, step in enumerate(scenario.steps, 1):
                assert step.step_number == i, f"Step numbers not sequential in {scenario.name}"


class TestBetaTestRunner:
    """Test the beta test runner functionality."""

    def test_environment_collection(self):
        """Test environment info collection."""
        runner = BetaTestRunner("test-001", "Test User")
        env = runner.session.environment

        assert "platform" in env
        assert "python_version" in env
        assert "timestamp" in env

    def test_session_creation(self):
        """Test session is created correctly."""
        runner = BetaTestRunner("test-001", "Test User")

        assert runner.session.tester_id == "test-001"
        assert runner.session.tester_name == "Test User"
        assert runner.session.session_id is not None


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Run interactive beta testing session."""
    print("=" * 60)
    print("SCENEMACHINE BETA TESTING SESSION")
    print("=" * 60)

    tester_id = input("\nEnter your tester ID: ")
    tester_name = input("Enter your name: ")

    runner = BetaTestRunner(tester_id, tester_name)

    print(f"\nSession ID: {runner.session.session_id}")
    print(f"Available scenarios: {len(ALL_SCENARIOS)}")

    for i, scenario in enumerate(ALL_SCENARIOS, 1):
        print(f"  {i}. {scenario.name} ({len(scenario.steps)} steps)")

    while True:
        choice = input("\nEnter scenario number to run (or 'q' to finish): ")
        if choice.lower() == "q":
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ALL_SCENARIOS):
                runner.run_scenario(ALL_SCENARIOS[idx])
            else:
                print("Invalid choice")
        except ValueError:
            print("Enter a number or 'q'")

    report = runner.finalize_session()

    print("\n" + "=" * 60)
    print("SESSION SUMMARY")
    print("=" * 60)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
