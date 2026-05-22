"""Tests for scene planning service."""

from uuid import uuid4

import pytest

from scenemachine.models.scene import SceneState, SceneType, TimeOfDay
from scenemachine.models.shot import CameraMovement, ShotType
from scenemachine.services.scene_planning import (
    SceneAnalysis,
    ScenePlanningService,
    ShotBreakdown,
    ShotSpec,
)


class TestSceneAnalysis:
    """Tests for scene analysis functionality."""

    def test_shot_spec_creation(self):
        """Test creating a shot specification."""
        spec = ShotSpec(
            shot_number="1-1",
            sequence_number=1,
            shot_type=ShotType.ESTABLISHING,
            camera_movement=CameraMovement.STATIC,
            description="Establishing shot of city skyline",
            duration_seconds=4.0,
        )

        assert spec.shot_number == "1-1"
        assert spec.sequence_number == 1
        assert spec.shot_type == ShotType.ESTABLISHING
        assert spec.camera_movement == CameraMovement.STATIC
        assert spec.description == "Establishing shot of city skyline"
        assert spec.duration_seconds == 4.0
        assert spec.dialogue is None
        assert spec.character_ids == []

    def test_scene_analysis_dataclass(self):
        """Test SceneAnalysis dataclass."""
        analysis = SceneAnalysis(
            summary="A tense confrontation in an alley",
            mood="tense",
            emotional_arc=["anticipation", "tension", "resolution"],
            key_moments=[{"description": "Character reveals gun", "importance": "high"}],
            visual_style_suggestions=["low-key lighting", "high contrast"],
            pacing="fast-paced with quick cuts",
            importance=8,
            suggested_shot_count=12,
            dialogue_heavy=False,
            action_heavy=True,
        )

        assert analysis.mood == "tense"
        assert analysis.importance == 8
        assert analysis.action_heavy is True
        assert len(analysis.key_moments) == 1

    def test_shot_breakdown_dataclass(self):
        """Test ShotBreakdown dataclass."""
        shots = [
            ShotSpec(
                shot_number="1-1",
                sequence_number=1,
                shot_type=ShotType.WIDE,
                camera_movement=CameraMovement.STATIC,
                description="Wide shot",
                duration_seconds=3.0,
            ),
            ShotSpec(
                shot_number="1-2",
                sequence_number=2,
                shot_type=ShotType.MEDIUM,
                camera_movement=CameraMovement.TRACKING,
                description="Medium shot",
                duration_seconds=2.5,
            ),
        ]

        breakdown = ShotBreakdown(
            scene_id=str(uuid4()),
            approach="Classical coverage",
            coverage_style="dialogue",
            notes="Standard dialogue scene",
            shots=shots,
            estimated_duration=5.5,
        )

        assert len(breakdown.shots) == 2
        assert breakdown.estimated_duration == 5.5
        assert breakdown.coverage_style == "dialogue"


class TestScenePlanningService:
    """Tests for ScenePlanningService."""

    @pytest.fixture
    def mock_scene(self):
        """Create a mock scene for testing."""
        from unittest.mock import MagicMock

        scene = MagicMock()
        scene.id = uuid4()
        scene.project_id = uuid4()
        scene.scene_number = "1"
        scene.sequence_number = 1
        scene.heading = "INT. OFFICE - DAY"
        scene.scene_type = SceneType.INTERIOR
        scene.location = "Office"
        scene.time_of_day = TimeOfDay.DAY
        scene.raw_content = """
        John enters the office slowly. He looks around nervously.

        JOHN
        Is anyone here?

        Sarah reveals herself from behind the door.

        SARAH
        I've been waiting for you.
        """
        scene.action_lines = [
            "John enters the office slowly",
            "He looks around nervously",
            "Sarah reveals herself from behind the door",
        ]
        scene.character_ids = [uuid4(), uuid4()]
        scene.analysis = None
        scene.shots = []
        scene.shot_breakdown = None
        scene.state = SceneState.PARSED

        return scene

    def test_determine_mood_tense(self):
        """Test mood determination for tense scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        content = "He slowly reached for the gun, his eyes filled with fear."
        mood = service._determine_mood(content)

        assert mood == "tense"

    def test_determine_mood_romantic(self):
        """Test mood determination for romantic scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        content = "They embrace, sharing a tender kiss. Her heart was full of love."
        mood = service._determine_mood(content)

        assert mood == "romantic"

    def test_determine_mood_neutral(self):
        """Test mood determination for neutral scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        content = "He walked to the table and sat down."
        mood = service._determine_mood(content)

        assert mood == "neutral"

    def test_determine_pacing_action_heavy(self):
        """Test pacing determination for action scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        pacing = service._determine_pacing(
            content="",
            action_heavy=True,
            dialogue_heavy=False,
        )

        assert "fast" in pacing.lower()

    def test_determine_pacing_dialogue_heavy(self):
        """Test pacing determination for dialogue scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        pacing = service._determine_pacing(
            content="",
            action_heavy=False,
            dialogue_heavy=True,
        )

        assert "measured" in pacing.lower() or "deliberate" in pacing.lower()

    def test_extract_key_moments(self):
        """Test key moment extraction from action lines."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        action_lines = [
            "John enters the room",
            "He looks around",
            "Sarah suddenly reveals a letter",
            "John realizes the truth",
        ]

        moments = service._extract_key_moments(action_lines)

        # Should find high importance moments
        high_importance = [m for m in moments if m["importance"] == "high"]
        assert len(high_importance) >= 2  # "enters", "reveals", "realizes"

    def test_suggest_shot_for_reveal_moment(self):
        """Test shot suggestion for reveal moments."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        moment = {"description": "Sarah reveals the hidden document", "importance": "high"}
        shot_type, movement = service._suggest_shot_for_moment(moment)

        assert shot_type == ShotType.CLOSE_UP
        assert movement == CameraMovement.DOLLY

    def test_suggest_shot_for_enter_moment(self):
        """Test shot suggestion for entrance moments."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        moment = {"description": "John enters through the door", "importance": "high"}
        shot_type, movement = service._suggest_shot_for_moment(moment)

        assert shot_type == ShotType.MEDIUM
        assert movement == CameraMovement.TRACKING

    def test_suggest_shot_for_medium_importance(self):
        """Test shot suggestion for medium importance moments."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        moment = {"description": "She looks toward the window", "importance": "medium"}
        shot_type, movement = service._suggest_shot_for_moment(moment)

        assert shot_type == ShotType.MEDIUM_CLOSE_UP
        assert movement == CameraMovement.STATIC

    def test_estimate_importance_with_characters(self):
        """Test importance estimation based on character count."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        scene = MagicMock()
        scene.character_ids = [uuid4() for _ in range(5)]  # Many characters

        importance = service._estimate_importance(scene, dialogue_count=5, action_count=2)

        assert importance >= 6  # Should be above average due to characters

    def test_suggest_shot_count(self):
        """Test shot count suggestion."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        # High importance scene with dialogue
        count = service._suggest_shot_count(
            dialogue_count=10,
            action_count=3,
            importance=8,
        )

        assert count >= 6  # Should suggest multiple shots
        assert count <= 20  # But not too many

    def test_suggest_shot_count_simple_scene(self):
        """Test shot count for simple scene."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        # Low importance, minimal content
        count = service._suggest_shot_count(
            dialogue_count=0,
            action_count=1,
            importance=3,
        )

        assert count >= 3  # Minimum shots
        assert count <= 6  # Simple scene shouldn't have many

    def test_coverage_style_action(self):
        """Test coverage style for action scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        analysis = SceneAnalysis(
            summary="",
            mood="action",
            emotional_arc=[],
            key_moments=[],
            visual_style_suggestions=[],
            pacing="fast",
            importance=5,
            suggested_shot_count=10,
            dialogue_heavy=False,
            action_heavy=True,
        )

        style = service._determine_coverage_style(analysis)

        assert "dynamic" in style.lower() or "action" in style.lower()

    def test_coverage_style_dialogue(self):
        """Test coverage style for dialogue scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        analysis = SceneAnalysis(
            summary="",
            mood="neutral",
            emotional_arc=[],
            key_moments=[],
            visual_style_suggestions=[],
            pacing="measured",
            importance=5,
            suggested_shot_count=8,
            dialogue_heavy=True,
            action_heavy=False,
        )

        style = service._determine_coverage_style(analysis)

        assert "classical" in style.lower() or "dialogue" in style.lower()

    def test_visual_style_night_scene(self):
        """Test visual style suggestions for night scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        scene = MagicMock()
        scene.time_of_day = TimeOfDay.NIGHT
        scene.scene_type = SceneType.EXTERIOR

        suggestions = service._suggest_visual_style(scene, mood="mysterious")

        assert any("low-key" in s.lower() or "dark" in s.lower() for s in suggestions)

    def test_visual_style_romantic_mood(self):
        """Test visual style suggestions for romantic mood."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        scene = MagicMock()
        scene.time_of_day = TimeOfDay.DUSK
        scene.scene_type = SceneType.EXTERIOR

        suggestions = service._suggest_visual_style(scene, mood="romantic")

        assert any("soft" in s.lower() or "warm" in s.lower() for s in suggestions)


class TestShotGeneration:
    """Tests for shot generation logic."""

    def test_generate_shots_exterior_scene(self):
        """Test shot generation for exterior scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        scene = MagicMock()
        scene.scene_number = "5"
        scene.scene_type = SceneType.EXTERIOR
        scene.location = "City Park"
        scene.time_of_day = TimeOfDay.DAY
        scene.action_lines = ["John walks through the park"]
        scene.character_ids = [uuid4()]

        analysis = SceneAnalysis(
            summary="Walking scene",
            mood="neutral",
            emotional_arc=["neutral"],
            key_moments=[],
            visual_style_suggestions=["natural lighting"],
            pacing="moderate",
            importance=5,
            suggested_shot_count=4,
            dialogue_heavy=False,
            action_heavy=False,
        )

        shots = service._generate_shots(scene, analysis)

        # Should start with establishing shot for exterior
        assert len(shots) > 0
        assert shots[0].shot_type == ShotType.ESTABLISHING

    def test_generate_shots_interior_scene(self):
        """Test shot generation for interior scenes."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        scene = MagicMock()
        scene.scene_number = "3"
        scene.scene_type = SceneType.INTERIOR
        scene.location = "Living Room"
        scene.time_of_day = TimeOfDay.DAY
        scene.action_lines = []
        scene.character_ids = []

        analysis = SceneAnalysis(
            summary="Interior scene",
            mood="neutral",
            emotional_arc=["neutral"],
            key_moments=[],
            visual_style_suggestions=[],
            pacing="moderate",
            importance=5,
            suggested_shot_count=4,
            dialogue_heavy=False,
            action_heavy=False,
        )

        shots = service._generate_shots(scene, analysis)

        # Should start with wide shot for interior
        assert len(shots) > 0
        assert shots[0].shot_type == ShotType.WIDE

    def test_generate_shots_with_multiple_characters(self):
        """Test shot generation includes two-shots for multiple characters."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        char1_id = uuid4()
        char2_id = uuid4()

        scene = MagicMock()
        scene.scene_number = "2"
        scene.scene_type = SceneType.INTERIOR
        scene.location = "Office"
        scene.time_of_day = TimeOfDay.DAY
        scene.action_lines = []
        scene.character_ids = [char1_id, char2_id]

        analysis = SceneAnalysis(
            summary="Dialogue scene",
            mood="neutral",
            emotional_arc=["neutral"],
            key_moments=[],
            visual_style_suggestions=[],
            pacing="measured",
            importance=5,
            suggested_shot_count=6,
            dialogue_heavy=True,
            action_heavy=False,
        )

        shots = service._generate_shots(scene, analysis)

        # Should include a two-shot for dialogue
        two_shots = [s for s in shots if s.shot_type == ShotType.TWO_SHOT]
        assert len(two_shots) >= 1

    def test_generate_shots_emotional_scene(self):
        """Test shot generation for emotional scenes includes reaction shots."""
        from unittest.mock import MagicMock

        session = MagicMock()
        service = ScenePlanningService(session)

        scene = MagicMock()
        scene.scene_number = "7"
        scene.scene_type = SceneType.INTERIOR
        scene.location = "Hospital Room"
        scene.time_of_day = TimeOfDay.NIGHT
        scene.action_lines = []
        scene.character_ids = [uuid4(), uuid4()]

        analysis = SceneAnalysis(
            summary="Emotional scene",
            mood="dramatic",
            emotional_arc=["tension", "sadness"],
            key_moments=[],
            visual_style_suggestions=[],
            pacing="slow",
            importance=8,
            suggested_shot_count=10,
            dialogue_heavy=True,
            action_heavy=False,
        )

        shots = service._generate_shots(scene, analysis)

        # Should include close-up reaction shots for emotional scenes
        close_ups = [s for s in shots if s.shot_type == ShotType.CLOSE_UP]
        assert len(close_ups) >= 1


class TestShotTypeEnum:
    """Tests for shot type enumeration."""

    def test_all_shot_types_have_values(self):
        """Test all shot types have string values."""
        for shot_type in ShotType:
            assert isinstance(shot_type.value, str)
            assert len(shot_type.value) > 0

    def test_common_shot_types_exist(self):
        """Test common shot types are defined."""
        common_types = [
            "establishing",
            "wide",
            "medium",
            "close_up",
            "two_shot",
            "over_the_shoulder",
        ]

        for type_name in common_types:
            assert hasattr(ShotType, type_name.upper())


class TestCameraMovementEnum:
    """Tests for camera movement enumeration."""

    def test_all_movements_have_values(self):
        """Test all camera movements have string values."""
        for movement in CameraMovement:
            assert isinstance(movement.value, str)
            assert len(movement.value) > 0

    def test_common_movements_exist(self):
        """Test common camera movements are defined."""
        common_movements = [
            "static",
            "pan",
            "tilt",
            "dolly",
            "tracking",
            "handheld",
        ]

        for movement_name in common_movements:
            assert hasattr(CameraMovement, movement_name.upper())
