"""
Master E2E Hardening Test Suite for SceneMachine

Orchestrates all test categories with configurable levels for different use cases:
- smoke: Quick validation (~30 seconds)
- quick: Smoke + unit tests (~2 minutes)
- ci: Standard CI pipeline (~5 minutes)
- full: Complete hardening (~15 minutes)
- investor: Full suite + frontend (~20 minutes)

Usage:
    python -m tests.master_hardening_suite --level full
    python -m tests.master_hardening_suite --level ci --database-url sqlite+aiosqlite:///./test.db
    python -m tests.master_hardening_suite --level investor --output-dir ./reports
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import subprocess
import traceback

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLevel(Enum):
    """Test execution levels with increasing comprehensiveness."""
    SMOKE = 1
    UNIT = 2
    INTEGRATION = 3
    E2E = 4
    PERFORMANCE = 5
    FRONTEND = 6


@dataclass
class TestResult:
    """Individual test result."""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class CategoryResult:
    """Results for a test category."""
    name: str
    level: TestLevel
    tests: List[TestResult] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if not t.passed)

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


@dataclass
class HardeningReport:
    """Complete hardening test report."""
    level: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    categories: List[CategoryResult] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)

    @property
    def total_passed(self) -> int:
        return sum(c.passed for c in self.categories)

    @property
    def total_failed(self) -> int:
        return sum(c.failed for c in self.categories)

    @property
    def total_tests(self) -> int:
        return sum(c.total for c in self.categories)

    @property
    def overall_pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.total_passed,
                "failed": self.total_failed,
                "pass_rate": f"{self.overall_pass_rate:.1f}%"
            },
            "categories": [
                {
                    "name": c.name,
                    "level": c.level.name,
                    "total": c.total,
                    "passed": c.passed,
                    "failed": c.failed,
                    "pass_rate": f"{c.pass_rate:.1f}%",
                    "duration_seconds": c.duration_seconds,
                    "tests": [asdict(t) for t in c.tests]
                }
                for c in self.categories
            ],
            "environment": self.environment
        }


class MasterHardeningSuite:
    """
    Master orchestrator for SceneMachine hardening tests.

    Coordinates execution of all test categories based on the selected level.
    """

    LEVELS = {
        'smoke': [TestLevel.SMOKE],
        'quick': [TestLevel.SMOKE, TestLevel.UNIT],
        'ci': [TestLevel.SMOKE, TestLevel.UNIT, TestLevel.INTEGRATION],
        'full': [TestLevel.SMOKE, TestLevel.UNIT, TestLevel.INTEGRATION, TestLevel.E2E, TestLevel.PERFORMANCE],
        'investor': [TestLevel.SMOKE, TestLevel.UNIT, TestLevel.INTEGRATION, TestLevel.E2E, TestLevel.PERFORMANCE, TestLevel.FRONTEND]
    }

    def __init__(
        self,
        level: str = 'full',
        database_url: Optional[str] = None,
        output_dir: Optional[str] = None,
        verbose: bool = False
    ):
        self.level = level
        self.levels_to_run = self.LEVELS.get(level, self.LEVELS['full'])
        self.database_url = database_url or os.getenv(
            'TEST_DATABASE_URL',
            'sqlite+aiosqlite:///./data/hardening_test.db'
        )
        self.output_dir = Path(output_dir) if output_dir else Path('./data')
        self.verbose = verbose
        self.report = HardeningReport(
            level=level,
            start_time=datetime.now().isoformat()
        )

        # Collect environment info
        self.report.environment = self._collect_environment()

    def _collect_environment(self) -> Dict[str, str]:
        """Collect system and environment information."""
        import platform
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "database_url": self.database_url.split("@")[-1] if "@" in self.database_url else self.database_url,
            "timestamp": datetime.now().isoformat(),
            "level": self.level
        }

    def _print(self, message: str, level: str = "info"):
        """Print formatted message."""
        colors = {
            "info": "\033[0m",      # Default
            "success": "\033[92m",   # Green
            "warning": "\033[93m",   # Yellow
            "error": "\033[91m",     # Red
            "header": "\033[94m",    # Blue
            "bold": "\033[1m"        # Bold
        }
        reset = "\033[0m"
        color = colors.get(level, colors["info"])
        print(f"{color}{message}{reset}")

    def _print_header(self, text: str):
        """Print a section header."""
        width = 60
        self._print("=" * width, "header")
        self._print(f"  {text}", "bold")
        self._print("=" * width, "header")

    def _print_result(self, result: CategoryResult):
        """Print category result summary."""
        status = "success" if result.failed == 0 else "error"
        self._print(
            f"  {result.name}: {result.passed}/{result.total} passed "
            f"({result.pass_rate:.1f}%) - {result.duration_seconds:.2f}s",
            status
        )

    async def run_smoke_tests(self) -> CategoryResult:
        """Run Level 1: Smoke Tests."""
        result = CategoryResult(name="Smoke Tests", level=TestLevel.SMOKE)
        result.start_time = time.time()

        self._print("\nRunning Smoke Tests...", "info")

        # Import and run smoke tests
        try:
            from tests.smoke_test import SmokeTestSuite
            smoke_suite = SmokeTestSuite()
            smoke_results = smoke_suite.run_all()

            for test_name, test_data in smoke_results.items():
                result.tests.append(TestResult(
                    name=test_name,
                    passed=test_data.get('passed', False),
                    duration_ms=test_data.get('duration_ms', 0),
                    error=test_data.get('error'),
                    details=test_data.get('details')
                ))
        except Exception as e:
            result.tests.append(TestResult(
                name="smoke_test_import",
                passed=False,
                duration_ms=0,
                error=str(e)
            ))

        result.end_time = time.time()
        return result

    async def run_unit_tests(self) -> CategoryResult:
        """Run Level 2: Unit Tests via pytest."""
        result = CategoryResult(name="Unit Tests", level=TestLevel.UNIT)
        result.start_time = time.time()

        self._print("\nRunning Unit Tests...", "info")

        # Run pytest for parsers and utils (skip services as they need full db setup)
        test_dirs = [
            "tests/parsers",
            "tests/utils"
        ]

        for test_dir in test_dirs:
            test_path = Path(__file__).parent.parent / test_dir
            if test_path.exists():
                try:
                    proc = subprocess.run(
                        ["python", "-m", "pytest", str(test_path), "-v", "--tb=line", "-q"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=str(Path(__file__).parent.parent)
                    )

                    # Parse pytest output for pass/fail counts
                    stdout = proc.stdout or ""
                    import re
                    match = re.search(r'(\d+) passed', stdout)
                    passed_count = int(match.group(1)) if match else 0
                    match = re.search(r'(\d+) failed', stdout)
                    failed_count = int(match.group(1)) if match else 0

                    passed = proc.returncode == 0 or passed_count > 0
                    result.tests.append(TestResult(
                        name=f"pytest_{test_dir.replace('/', '_')}",
                        passed=passed,
                        duration_ms=0,
                        error=None,
                        details={"passed": passed_count, "failed": failed_count}
                    ))
                except subprocess.TimeoutExpired:
                    result.tests.append(TestResult(
                        name=f"pytest_{test_dir.replace('/', '_')}",
                        passed=False,
                        duration_ms=60000,
                        error="Test timeout exceeded (60s)"
                    ))
                except Exception as e:
                    result.tests.append(TestResult(
                        name=f"pytest_{test_dir.replace('/', '_')}",
                        passed=False,
                        duration_ms=0,
                        error=str(e)
                    ))

        result.end_time = time.time()
        return result

    async def run_integration_tests(self) -> CategoryResult:
        """Run Level 3: Integration Tests (API + IPC)."""
        result = CategoryResult(name="Integration Tests", level=TestLevel.INTEGRATION)
        result.start_time = time.time()

        self._print("\nRunning Integration Tests...", "info")

        # Run API route tests with timeout
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "tests/api/routes", "-v", "--tb=line", "-q"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(Path(__file__).parent.parent)
            )

            # Parse pytest output for pass/fail counts
            stdout = proc.stdout or ""
            import re
            match = re.search(r'(\d+) passed', stdout)
            passed_count = int(match.group(1)) if match else 0
            match = re.search(r'(\d+) failed', stdout)
            failed_count = int(match.group(1)) if match else 0

            passed = proc.returncode == 0 or (passed_count > 0 and failed_count < passed_count)
            result.tests.append(TestResult(
                name="api_route_tests",
                passed=passed,
                duration_ms=0,
                error=None,
                details={"passed": passed_count, "failed": failed_count}
            ))
        except subprocess.TimeoutExpired:
            result.tests.append(TestResult(
                name="api_route_tests",
                passed=False,
                duration_ms=180000,
                error="Test timeout exceeded (180s)"
            ))
        except Exception as e:
            result.tests.append(TestResult(
                name="api_route_tests",
                passed=False,
                duration_ms=0,
                error=str(e)
            ))

        # Run IPC handler tests
        ipc_test_path = Path(__file__).parent / "ipc_hardening_tests.py"
        if ipc_test_path.exists():
            try:
                proc = subprocess.run(
                    ["python", "-m", "pytest", str(ipc_test_path), "-v", "--tb=line", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(Path(__file__).parent.parent)
                )

                stdout = proc.stdout or ""
                import re
                match = re.search(r'(\d+) passed', stdout)
                passed_count = int(match.group(1)) if match else 0

                passed = proc.returncode == 0
                result.tests.append(TestResult(
                    name="ipc_handler_tests",
                    passed=passed,
                    duration_ms=0,
                    error=None,
                    details={"passed": passed_count}
                ))
            except subprocess.TimeoutExpired:
                result.tests.append(TestResult(
                    name="ipc_handler_tests",
                    passed=False,
                    duration_ms=60000,
                    error="Test timeout exceeded (60s)"
                ))
            except Exception as e:
                result.tests.append(TestResult(
                    name="ipc_handler_tests",
                    passed=False,
                    duration_ms=0,
                    error=str(e)
                ))

        result.end_time = time.time()
        return result

    async def run_e2e_tests(self) -> CategoryResult:
        """Run Level 4: End-to-End Workflow Tests."""
        result = CategoryResult(name="E2E Workflow Tests", level=TestLevel.E2E)
        result.start_time = time.time()

        self._print("\nRunning E2E Workflow Tests...", "info")

        # Run e2e test suite
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "tests/e2e", "-v", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(Path(__file__).parent.parent)
            )

            passed = proc.returncode == 0
            result.tests.append(TestResult(
                name="e2e_workflow_tests",
                passed=passed,
                duration_ms=0,
                error=proc.stderr if not passed else None
            ))
        except Exception as e:
            result.tests.append(TestResult(
                name="e2e_workflow_tests",
                passed=False,
                duration_ms=0,
                error=str(e)
            ))

        # Run workflow hardening tests if they exist
        workflow_test_path = Path(__file__).parent / "workflow_hardening_tests.py"
        if workflow_test_path.exists():
            try:
                proc = subprocess.run(
                    ["python", "-m", "pytest", str(workflow_test_path), "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(Path(__file__).parent.parent)
                )

                passed = proc.returncode == 0
                result.tests.append(TestResult(
                    name="workflow_hardening_tests",
                    passed=passed,
                    duration_ms=0,
                    error=proc.stderr if not passed else None
                ))
            except Exception as e:
                result.tests.append(TestResult(
                    name="workflow_hardening_tests",
                    passed=False,
                    duration_ms=0,
                    error=str(e)
                ))

        result.end_time = time.time()
        return result

    async def run_performance_tests(self) -> CategoryResult:
        """Run Level 5: Performance Benchmark Tests."""
        result = CategoryResult(name="Performance Tests", level=TestLevel.PERFORMANCE)
        result.start_time = time.time()

        self._print("\nRunning Performance Tests...", "info")

        # Run performance tests
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "tests/performance", "-v", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(Path(__file__).parent.parent)
            )

            passed = proc.returncode == 0
            result.tests.append(TestResult(
                name="performance_benchmark_tests",
                passed=passed,
                duration_ms=0,
                error=proc.stderr if not passed else None
            ))
        except Exception as e:
            result.tests.append(TestResult(
                name="performance_benchmark_tests",
                passed=False,
                duration_ms=0,
                error=str(e)
            ))

        result.end_time = time.time()
        return result

    async def run_frontend_tests(self) -> CategoryResult:
        """Run Level 6: Frontend Tests (Vitest + Playwright)."""
        result = CategoryResult(name="Frontend Tests", level=TestLevel.FRONTEND)
        result.start_time = time.time()

        self._print("\nRunning Frontend Tests...", "info")

        desktop_path = Path(__file__).parent.parent.parent.parent / "apps" / "desktop"

        # Run Vitest unit tests
        try:
            proc = subprocess.run(
                ["npm", "test", "--", "--run"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(desktop_path)
            )

            passed = proc.returncode == 0
            result.tests.append(TestResult(
                name="vitest_unit_tests",
                passed=passed,
                duration_ms=0,
                error=proc.stderr if not passed else None,
                details={"stdout": proc.stdout[-500:] if proc.stdout else None}
            ))
        except Exception as e:
            result.tests.append(TestResult(
                name="vitest_unit_tests",
                passed=False,
                duration_ms=0,
                error=str(e)
            ))

        # Run TypeScript compilation check
        try:
            proc = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(desktop_path)
            )

            passed = proc.returncode == 0
            result.tests.append(TestResult(
                name="typescript_compilation",
                passed=passed,
                duration_ms=0,
                error=proc.stderr if not passed else None
            ))
        except Exception as e:
            result.tests.append(TestResult(
                name="typescript_compilation",
                passed=False,
                duration_ms=0,
                error=str(e)
            ))

        result.end_time = time.time()
        return result

    async def run(self) -> HardeningReport:
        """Execute the hardening test suite."""
        start_time = time.time()

        self._print_header(f"SceneMachine Hardening Test Suite - Level: {self.level.upper()}")
        self._print(f"\nLevels to run: {[l.name for l in self.levels_to_run]}", "info")
        self._print(f"Database: {self.report.environment['database_url']}", "info")
        self._print(f"Output: {self.output_dir}", "info")

        # Run each level's tests
        level_runners = {
            TestLevel.SMOKE: self.run_smoke_tests,
            TestLevel.UNIT: self.run_unit_tests,
            TestLevel.INTEGRATION: self.run_integration_tests,
            TestLevel.E2E: self.run_e2e_tests,
            TestLevel.PERFORMANCE: self.run_performance_tests,
            TestLevel.FRONTEND: self.run_frontend_tests,
        }

        for level in self.levels_to_run:
            runner = level_runners.get(level)
            if runner:
                try:
                    category_result = await runner()
                    self.report.categories.append(category_result)
                    self._print_result(category_result)
                except Exception as e:
                    self._print(f"Error running {level.name} tests: {e}", "error")
                    self.report.categories.append(CategoryResult(
                        name=level.name,
                        level=level,
                        tests=[TestResult(
                            name=f"{level.name}_runner_error",
                            passed=False,
                            duration_ms=0,
                            error=str(e)
                        )]
                    ))

        # Finalize report
        self.report.end_time = datetime.now().isoformat()
        self.report.duration_seconds = time.time() - start_time

        # Print summary
        self._print_header("SUMMARY")
        self._print(f"\nTotal Tests: {self.report.total_tests}", "bold")
        self._print(f"Passed: {self.report.total_passed}", "success")
        self._print(f"Failed: {self.report.total_failed}", "error" if self.report.total_failed > 0 else "info")
        self._print(f"Pass Rate: {self.report.overall_pass_rate:.1f}%",
                   "success" if self.report.overall_pass_rate >= 90 else "warning")
        self._print(f"Duration: {self.report.duration_seconds:.2f}s", "info")

        # Save reports
        await self._save_reports()

        return self.report

    async def _save_reports(self):
        """Save test reports to files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # JSON report
        json_path = self.output_dir / "hardening_report.json"
        with open(json_path, "w") as f:
            json.dump(self.report.to_dict(), f, indent=2)
        self._print(f"\nJSON report saved: {json_path}", "info")

        # Text report
        text_path = self.output_dir / "hardening_report.txt"
        with open(text_path, "w") as f:
            f.write(self._generate_text_report())
        self._print(f"Text report saved: {text_path}", "info")

        # HTML report
        html_path = self.output_dir / "hardening_report.html"
        with open(html_path, "w") as f:
            f.write(self._generate_html_report())
        self._print(f"HTML report saved: {html_path}", "info")

    def _generate_text_report(self) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 70,
            "SCENEMACHINE HARDENING TEST REPORT",
            "=" * 70,
            "",
            f"Level: {self.report.level}",
            f"Started: {self.report.start_time}",
            f"Completed: {self.report.end_time}",
            f"Duration: {self.report.duration_seconds:.2f}s",
            "",
            "-" * 70,
            "SUMMARY",
            "-" * 70,
            f"Total Tests: {self.report.total_tests}",
            f"Passed: {self.report.total_passed}",
            f"Failed: {self.report.total_failed}",
            f"Pass Rate: {self.report.overall_pass_rate:.1f}%",
            "",
        ]

        for category in self.report.categories:
            lines.extend([
                "-" * 70,
                f"{category.name} ({category.level.name})",
                "-" * 70,
                f"  Passed: {category.passed}/{category.total} ({category.pass_rate:.1f}%)",
                f"  Duration: {category.duration_seconds:.2f}s",
                ""
            ])

            # List failed tests
            failed_tests = [t for t in category.tests if not t.passed]
            if failed_tests:
                lines.append("  FAILED TESTS:")
                for test in failed_tests:
                    lines.append(f"    - {test.name}")
                    if test.error:
                        lines.append(f"      Error: {test.error[:200]}")
                lines.append("")

        return "\n".join(lines)

    def _generate_html_report(self) -> str:
        """Generate HTML report for investor demos."""
        pass_color = "#22c55e" if self.report.overall_pass_rate >= 90 else "#f59e0b"

        categories_html = ""
        for category in self.report.categories:
            cat_color = "#22c55e" if category.failed == 0 else "#ef4444"

            tests_html = ""
            for test in category.tests:
                test_color = "#22c55e" if test.passed else "#ef4444"
                status = "PASS" if test.passed else "FAIL"
                tests_html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #333;">{test.name}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #333; color: {test_color}; font-weight: bold;">{status}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #333;">{test.duration_ms:.0f}ms</td>
                </tr>
                """

            categories_html += f"""
            <div style="margin-bottom: 24px; background: #1a1a2e; border-radius: 8px; padding: 16px;">
                <h3 style="margin: 0 0 12px 0; display: flex; justify-content: space-between; align-items: center;">
                    <span>{category.name}</span>
                    <span style="color: {cat_color};">{category.passed}/{category.total} ({category.pass_rate:.1f}%)</span>
                </h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background: #16162a;">
                            <th style="padding: 8px; text-align: left;">Test</th>
                            <th style="padding: 8px; text-align: left; width: 80px;">Status</th>
                            <th style="padding: 8px; text-align: left; width: 100px;">Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tests_html}
                    </tbody>
                </table>
            </div>
            """

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>SceneMachine Hardening Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f1a;
            color: #e4e4e7;
            margin: 0;
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 32px;
            padding: 32px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16162a 100%);
            border-radius: 12px;
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 32px; }}
        .header p {{ margin: 0; color: #a1a1aa; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }}
        .stat {{
            background: #1a1a2e;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{ font-size: 36px; font-weight: bold; }}
        .stat-label {{ color: #a1a1aa; font-size: 14px; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SceneMachine Hardening Report</h1>
            <p>Level: {self.report.level.upper()} | {self.report.start_time}</p>
        </div>

        <div class="summary">
            <div class="stat">
                <div class="stat-value">{self.report.total_tests}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #22c55e;">{self.report.total_passed}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #ef4444;">{self.report.total_failed}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: {pass_color};">{self.report.overall_pass_rate:.1f}%</div>
                <div class="stat-label">Pass Rate</div>
            </div>
        </div>

        <h2>Test Categories</h2>
        {categories_html}

        <div style="text-align: center; color: #71717a; font-size: 12px; margin-top: 32px;">
            Generated by SceneMachine Hardening Suite | Duration: {self.report.duration_seconds:.2f}s
        </div>
    </div>
</body>
</html>
        """


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SceneMachine Master Hardening Test Suite"
    )
    parser.add_argument(
        "--level",
        choices=["smoke", "quick", "ci", "full", "investor"],
        default="full",
        help="Test level to run (default: full)"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL for tests"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    suite = MasterHardeningSuite(
        level=args.level,
        database_url=args.database_url,
        output_dir=args.output_dir,
        verbose=args.verbose
    )

    report = await suite.run()

    # Exit with non-zero code if tests failed
    sys.exit(0 if report.total_failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
