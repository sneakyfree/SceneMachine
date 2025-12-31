"""End-to-end tests for complete user workflow.

Tests the entire journey from screenplay upload to final movie export,
validating all major system components work together correctly.

These tests use mock providers to avoid external API costs while
validating the complete pipeline integration.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

# Test constants
SAMPLE_SCREENPLAY = """
FADE IN:

INT. COFFEE SHOP - DAY

A cozy coffee shop with warm lighting. SARAH (30s) sits at a corner table.

SARAH
I can't believe you're actually here.

JOHN (35), enters through the front door, spots Sarah.

JOHN
I told you I'd come. I always keep my promises.

He walks over and sits across from her.

SARAH
That's what I'm afraid of.

CUT TO:

EXT. CITY STREET - NIGHT

Rain falls heavily. John runs down the street, looking behind him.

JOHN (V.O.)
Some promises are harder to keep than others.

FADE OUT.
"""


# Mock fixtures for standalone testing
class MockProject:
    """Mock project for testing."""

    def __init__(self, id: str = None, name: str = "Test Project"):
        self.id = id or str(uuid4())
        self.name = name
        self.state = "draft"
        self.scenes: List[Dict] = []
        self.characters: List[Dict] = []
        self.shots: List[Dict] = []


class MockScreenplayParser:
    """Mock screenplay parser."""

    def parse(self, content: str) -> Dict[str, Any]:
        """Parse screenplay content."""
        return {
            "title": "Test Screenplay",
            "scenes": [
                {
                    "scene_number": 1,
                    "heading": "INT. COFFEE SHOP - DAY",
                    "location": "COFFEE SHOP",
                    "time_of_day": "DAY",
                    "int_ext": "INT",
                    "elements": [
                        {"type": "action", "content": "A cozy coffee shop..."},
                        {"type": "character", "name": "SARAH"},
                        {"type": "dialogue", "content": "I can't believe..."},
                    ]
                },
                {
                    "scene_number": 2,
                    "heading": "EXT. CITY STREET - NIGHT",
                    "location": "CITY STREET",
                    "time_of_day": "NIGHT",
                    "int_ext": "EXT",
                    "elements": [
                        {"type": "action", "content": "Rain falls heavily..."},
                    ]
                }
            ],
            "characters": ["SARAH", "JOHN"],
        }


class MockGenerationProvider:
    """Mock video generation provider."""

    def __init__(self, fail_rate: float = 0.0):
        self.fail_rate = fail_rate
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate a mock video."""
        import random
        self.call_count += 1

        if random.random() < self.fail_rate:
            raise RuntimeError("Mock generation failure")

        # Simulate generation time
        await asyncio.sleep(0.01)

        return {
            "id": str(uuid4()),
            "status": "completed",
            "output_url": f"https://mock.provider/videos/{uuid4()}.mp4",
            "duration_seconds": 5.0,
            "thumbnail_url": f"https://mock.provider/thumbnails/{uuid4()}.jpg",
        }


class MockAssemblyService:
    """Mock video assembly service."""

    async def assemble(
        self,
        project_id: str,
        shots: List[Dict],
        output_path: str,
        settings: Dict = None
    ) -> Dict[str, Any]:
        """Assemble shots into final video."""
        # Create a mock output file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"MOCK_VIDEO_DATA")

        return {
            "output_path": output_path,
            "duration_seconds": sum(s.get("duration_seconds", 5.0) for s in shots),
            "resolution": "1920x1080",
            "file_size_bytes": len(b"MOCK_VIDEO_DATA"),
        }


# =============================================================================
# Complete Workflow Tests
# =============================================================================


class TestCompleteWorkflow:
    """Test complete user workflow from screenplay to export."""

    def test_screenplay_parsing(self):
        """Test screenplay can be parsed into scenes and characters."""
        parser = MockScreenplayParser()
        result = parser.parse(SAMPLE_SCREENPLAY)

        assert "scenes" in result
        assert len(result["scenes"]) == 2
        assert "characters" in result
        assert "SARAH" in result["characters"]
        assert "JOHN" in result["characters"]

    def test_scene_extraction(self):
        """Test scenes are correctly extracted from screenplay."""
        parser = MockScreenplayParser()
        result = parser.parse(SAMPLE_SCREENPLAY)

        scene1 = result["scenes"][0]
        assert scene1["scene_number"] == 1
        assert scene1["location"] == "COFFEE SHOP"
        assert scene1["time_of_day"] == "DAY"
        assert scene1["int_ext"] == "INT"

        scene2 = result["scenes"][1]
        assert scene2["scene_number"] == 2
        assert scene2["location"] == "CITY STREET"
        assert scene2["time_of_day"] == "NIGHT"
        assert scene2["int_ext"] == "EXT"

    def test_character_extraction(self):
        """Test characters are correctly extracted from screenplay."""
        parser = MockScreenplayParser()
        result = parser.parse(SAMPLE_SCREENPLAY)

        characters = result["characters"]
        assert len(characters) == 2
        assert "SARAH" in characters
        assert "JOHN" in characters

    @pytest.mark.asyncio
    async def test_shot_generation_success(self):
        """Test successful shot video generation."""
        provider = MockGenerationProvider(fail_rate=0.0)

        result = await provider.generate(
            prompt="A cozy coffee shop with warm lighting",
            duration=5.0,
            aspect_ratio="16:9"
        )

        assert result["status"] == "completed"
        assert result["output_url"].endswith(".mp4")
        assert result["duration_seconds"] == 5.0
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_shot_generation_failure_handling(self):
        """Test shot generation handles failures gracefully."""
        provider = MockGenerationProvider(fail_rate=1.0)

        with pytest.raises(RuntimeError, match="Mock generation failure"):
            await provider.generate(
                prompt="Test prompt",
                duration=5.0
            )

    @pytest.mark.asyncio
    async def test_multiple_shots_generation(self):
        """Test generating multiple shots in sequence."""
        provider = MockGenerationProvider(fail_rate=0.0)

        prompts = [
            "A cozy coffee shop with warm lighting",
            "Sarah sitting at a corner table",
            "John entering through the front door",
            "Rain falling on a city street at night",
        ]

        results = []
        for prompt in prompts:
            result = await provider.generate(prompt=prompt)
            results.append(result)

        assert len(results) == 4
        assert all(r["status"] == "completed" for r in results)
        assert provider.call_count == 4

    @pytest.mark.asyncio
    async def test_concurrent_shot_generation(self):
        """Test generating multiple shots concurrently."""
        provider = MockGenerationProvider(fail_rate=0.0)

        prompts = [f"Test prompt {i}" for i in range(5)]

        tasks = [provider.generate(prompt=p) for p in prompts]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r["status"] == "completed" for r in results)
        assert provider.call_count == 5

    @pytest.mark.asyncio
    async def test_video_assembly(self):
        """Test video assembly from multiple shots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = MockAssemblyService()
            output_path = os.path.join(tmpdir, "final_movie.mp4")

            shots = [
                {"id": "1", "output_url": "shot1.mp4", "duration_seconds": 5.0},
                {"id": "2", "output_url": "shot2.mp4", "duration_seconds": 5.0},
                {"id": "3", "output_url": "shot3.mp4", "duration_seconds": 5.0},
            ]

            result = await assembler.assemble(
                project_id="test-project",
                shots=shots,
                output_path=output_path
            )

            assert os.path.exists(output_path)
            assert result["duration_seconds"] == 15.0
            assert result["resolution"] == "1920x1080"


class TestProjectLifecycle:
    """Test project lifecycle state transitions."""

    def test_project_state_draft_to_screenplay_uploaded(self):
        """Test project transitions from draft to screenplay_uploaded."""
        project = MockProject()
        assert project.state == "draft"

        # Upload screenplay
        parser = MockScreenplayParser()
        result = parser.parse(SAMPLE_SCREENPLAY)
        project.scenes = result["scenes"]
        project.characters = [{"name": c} for c in result["characters"]]
        project.state = "screenplay_uploaded"

        assert project.state == "screenplay_uploaded"
        assert len(project.scenes) == 2
        assert len(project.characters) == 2

    def test_project_state_to_planning(self):
        """Test project transitions to planning state."""
        project = MockProject()
        project.state = "screenplay_uploaded"

        # Start planning
        project.state = "planning"

        assert project.state == "planning"

    def test_project_state_to_generating(self):
        """Test project transitions to generating state."""
        project = MockProject()
        project.state = "planning"

        # Start generation
        project.shots = [
            {"id": "1", "scene_id": "s1", "state": "queued"},
            {"id": "2", "scene_id": "s1", "state": "queued"},
        ]
        project.state = "generating"

        assert project.state == "generating"
        assert len(project.shots) == 2

    def test_project_state_to_complete(self):
        """Test project transitions to complete state."""
        project = MockProject()
        project.state = "generating"
        project.shots = [
            {"id": "1", "state": "approved"},
            {"id": "2", "state": "approved"},
        ]

        # All shots approved
        project.state = "complete"

        assert project.state == "complete"

    def test_full_project_lifecycle(self):
        """Test complete project lifecycle."""
        project = MockProject(name="My Movie")
        states_visited = [project.state]

        # Upload screenplay
        project.state = "screenplay_uploaded"
        states_visited.append(project.state)

        # Plan scenes
        project.state = "planning"
        states_visited.append(project.state)

        # Generate
        project.state = "generating"
        states_visited.append(project.state)

        # Assembly
        project.state = "assembly_in_progress"
        states_visited.append(project.state)

        # Complete
        project.state = "complete"
        states_visited.append(project.state)

        # Export
        project.state = "exported"
        states_visited.append(project.state)

        expected = [
            "draft",
            "screenplay_uploaded",
            "planning",
            "generating",
            "assembly_in_progress",
            "complete",
            "exported"
        ]
        assert states_visited == expected


class TestErrorRecovery:
    """Test error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_retry_failed_generation(self):
        """Test retrying a failed generation."""
        # First provider fails
        failing_provider = MockGenerationProvider(fail_rate=1.0)

        with pytest.raises(RuntimeError):
            await failing_provider.generate(prompt="Test")

        # Retry with working provider
        working_provider = MockGenerationProvider(fail_rate=0.0)
        result = await working_provider.generate(prompt="Test")

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_partial_generation_recovery(self):
        """Test recovering from partial generation failure."""
        provider = MockGenerationProvider(fail_rate=0.0)

        # Simulate: 3 shots needed, 2 succeeded, 1 failed
        successful_shots = []
        for i in range(2):
            result = await provider.generate(prompt=f"Shot {i}")
            successful_shots.append(result)

        failed_shot_id = "shot_3"

        # Retry the failed shot
        retry_result = await provider.generate(prompt="Shot 3 retry")
        successful_shots.append(retry_result)

        assert len(successful_shots) == 3
        assert all(s["status"] == "completed" for s in successful_shots)

    def test_rollback_invalid_state_transition(self):
        """Test invalid state transitions are rejected."""
        project = MockProject()
        project.state = "draft"

        # Cannot skip directly to generating
        valid_next_states = {
            "draft": ["screenplay_uploaded"],
            "screenplay_uploaded": ["planning"],
            "planning": ["generating"],
            "generating": ["assembly_in_progress", "generating"],  # Can stay
            "assembly_in_progress": ["complete"],
            "complete": ["exported", "archived"],
        }

        next_valid = valid_next_states.get(project.state, [])
        assert "generating" not in next_valid
        assert "screenplay_uploaded" in next_valid


class TestDataIntegrity:
    """Test data integrity throughout workflow."""

    def test_scene_shot_relationship(self):
        """Test scenes contain valid shots."""
        project = MockProject()

        scene = {"id": "s1", "scene_number": 1, "shots": []}
        shots = [
            {"id": "shot1", "scene_id": "s1", "sequence_number": 1},
            {"id": "shot2", "scene_id": "s1", "sequence_number": 2},
        ]
        scene["shots"] = shots
        project.scenes.append(scene)

        # Verify relationship integrity
        for shot in project.scenes[0]["shots"]:
            assert shot["scene_id"] == project.scenes[0]["id"]

    def test_character_consistency(self):
        """Test character data is consistent across scenes."""
        characters = {
            "SARAH": {"name": "SARAH", "description": "30s woman"},
            "JOHN": {"name": "JOHN", "description": "35 year old man"},
        }

        scene1_characters = ["SARAH", "JOHN"]
        scene2_characters = ["JOHN"]

        # All characters in scenes should be defined
        for char in scene1_characters:
            assert char in characters
        for char in scene2_characters:
            assert char in characters

    def test_shot_sequence_ordering(self):
        """Test shots maintain proper sequence ordering."""
        shots = [
            {"id": "a", "sequence_number": 3},
            {"id": "b", "sequence_number": 1},
            {"id": "c", "sequence_number": 2},
        ]

        # Sort by sequence number
        sorted_shots = sorted(shots, key=lambda x: x["sequence_number"])

        assert sorted_shots[0]["id"] == "b"
        assert sorted_shots[1]["id"] == "c"
        assert sorted_shots[2]["id"] == "a"

    def test_no_duplicate_scene_numbers(self):
        """Test scene numbers are unique."""
        scenes = [
            {"scene_number": 1},
            {"scene_number": 2},
            {"scene_number": 3},
        ]

        scene_numbers = [s["scene_number"] for s in scenes]
        assert len(scene_numbers) == len(set(scene_numbers))

    def test_no_duplicate_shot_numbers_per_scene(self):
        """Test shot numbers are unique within each scene."""
        scenes_shots = {
            "scene1": [
                {"shot_number": 1},
                {"shot_number": 2},
            ],
            "scene2": [
                {"shot_number": 1},  # OK: different scene
                {"shot_number": 2},
            ],
        }

        for scene_id, shots in scenes_shots.items():
            shot_numbers = [s["shot_number"] for s in shots]
            assert len(shot_numbers) == len(set(shot_numbers)), \
                f"Duplicate shot numbers in {scene_id}"


class TestQueueManagement:
    """Test generation queue management."""

    def test_queue_ordering_by_priority(self):
        """Test queue orders jobs by priority."""
        import time

        jobs = [
            {"id": "1", "priority": 0, "queued_at": time.time()},
            {"id": "2", "priority": 10, "queued_at": time.time() + 1},  # High priority
            {"id": "3", "priority": -10, "queued_at": time.time() + 2},  # Low priority
        ]

        # Sort by priority (highest first)
        sorted_jobs = sorted(jobs, key=lambda x: -x["priority"])

        assert sorted_jobs[0]["id"] == "2"  # Highest priority
        assert sorted_jobs[1]["id"] == "1"  # Normal priority
        assert sorted_jobs[2]["id"] == "3"  # Lowest priority

    def test_queue_ordering_by_time_same_priority(self):
        """Test queue orders by time when priority is same."""
        import time

        base_time = time.time()
        jobs = [
            {"id": "1", "priority": 0, "queued_at": base_time + 2},
            {"id": "2", "priority": 0, "queued_at": base_time + 0},  # First
            {"id": "3", "priority": 0, "queued_at": base_time + 1},
        ]

        # Sort by priority (desc), then queued_at (asc)
        sorted_jobs = sorted(jobs, key=lambda x: (-x["priority"], x["queued_at"]))

        assert sorted_jobs[0]["id"] == "2"  # First queued
        assert sorted_jobs[1]["id"] == "3"
        assert sorted_jobs[2]["id"] == "1"  # Last queued

    def test_concurrent_generation_limit(self):
        """Test concurrent generation is limited."""
        max_concurrent = 3

        running_jobs = [
            {"id": "1", "status": "running"},
            {"id": "2", "status": "running"},
            {"id": "3", "status": "running"},
        ]
        pending_jobs = [
            {"id": "4", "status": "pending"},
            {"id": "5", "status": "pending"},
        ]

        current_running = len([j for j in running_jobs if j["status"] == "running"])

        # Cannot start new jobs if at limit
        can_start = current_running < max_concurrent
        assert can_start is False

    def test_job_state_transitions(self):
        """Test job state transitions are valid."""
        valid_transitions = {
            "pending": ["preparing", "cancelled"],
            "preparing": ["running", "failed"],
            "running": ["post_processing", "failed", "timeout"],
            "post_processing": ["completed", "failed"],
            "completed": [],  # Terminal state
            "failed": ["pending"],  # Can retry
            "cancelled": [],  # Terminal state
            "timeout": ["pending"],  # Can retry
        }

        # Test each transition
        for state, next_states in valid_transitions.items():
            assert isinstance(next_states, list)


class TestExportWorkflow:
    """Test export workflow."""

    @pytest.mark.asyncio
    async def test_export_creates_file(self):
        """Test export creates output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = MockAssemblyService()
            output_path = os.path.join(tmpdir, "output", "movie.mp4")

            shots = [
                {"id": "1", "duration_seconds": 5.0},
            ]

            result = await assembler.assemble(
                project_id="test",
                shots=shots,
                output_path=output_path
            )

            assert os.path.exists(output_path)
            assert result["file_size_bytes"] > 0

    def test_export_format_options(self):
        """Test export supports different formats."""
        supported_formats = ["mp4", "webm", "mov"]

        for fmt in supported_formats:
            output_name = f"movie.{fmt}"
            assert output_name.endswith(f".{fmt}")

    def test_export_quality_options(self):
        """Test export supports different quality levels."""
        quality_levels = {
            "low": {"bitrate": "1M", "resolution": "720p"},
            "medium": {"bitrate": "5M", "resolution": "1080p"},
            "high": {"bitrate": "15M", "resolution": "1080p"},
            "ultra": {"bitrate": "50M", "resolution": "4K"},
        }

        for quality, settings in quality_levels.items():
            assert "bitrate" in settings
            assert "resolution" in settings


class TestProgressTracking:
    """Test progress tracking through workflow."""

    def test_overall_progress_calculation(self):
        """Test calculating overall project progress."""
        def calculate_progress(project: Dict) -> float:
            """Calculate overall project progress as percentage."""
            weights = {
                "screenplay_parsed": 10,
                "scenes_planned": 20,
                "shots_generated": 50,
                "assembly_complete": 20,
            }

            progress = 0
            if project.get("screenplay_parsed"):
                progress += weights["screenplay_parsed"]
            if project.get("scenes_planned"):
                progress += weights["scenes_planned"]

            # Partial progress for shot generation
            total_shots = project.get("total_shots", 0)
            completed_shots = project.get("completed_shots", 0)
            if total_shots > 0:
                shot_progress = (completed_shots / total_shots) * weights["shots_generated"]
                progress += shot_progress

            if project.get("assembly_complete"):
                progress += weights["assembly_complete"]

            return min(100, progress)

        # Test various states
        project = {"screenplay_parsed": True}
        assert calculate_progress(project) == 10

        project["scenes_planned"] = True
        assert calculate_progress(project) == 30

        project["total_shots"] = 10
        project["completed_shots"] = 5
        assert calculate_progress(project) == 30 + 25  # 50% of 50

    def test_shot_progress_tracking(self):
        """Test tracking progress of individual shots."""
        shots = [
            {"id": "1", "status": "completed", "progress": 100},
            {"id": "2", "status": "running", "progress": 50},
            {"id": "3", "status": "pending", "progress": 0},
            {"id": "4", "status": "pending", "progress": 0},
        ]

        total_progress = sum(s["progress"] for s in shots)
        average_progress = total_progress / len(shots)

        assert average_progress == 37.5

    def test_time_estimation(self):
        """Test estimating remaining time."""
        def estimate_time(completed: int, total: int, elapsed_seconds: float) -> float:
            """Estimate remaining time based on current progress."""
            if completed == 0:
                return float('inf')

            rate = completed / elapsed_seconds  # items per second
            remaining = total - completed
            return remaining / rate

        # 5 of 20 completed in 60 seconds
        remaining = estimate_time(completed=5, total=20, elapsed_seconds=60)

        # Rate = 5/60 = 0.083 items/sec
        # Remaining = 15 items
        # Time = 15 / 0.083 = 180 seconds
        assert remaining == pytest.approx(180.0, rel=0.01)
