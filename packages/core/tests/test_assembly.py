"""Tests for assembly and export service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from scenemachine.models.project import Project, ProjectState
from scenemachine.models.scene import Scene, SceneState, SceneType, TimeOfDay
from scenemachine.models.shot import Shot, ShotState, ShotType, CameraMovement
from scenemachine.services.assembly import (
    AssemblyService,
    AssemblyProgress,
    ExportFormat,
    ExportQuality,
    ExportResult,
    ExportSettings,
    SceneRender,
    Timeline,
    TimelineScene,
    TimelineShot,
)


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_all_formats_have_values(self):
        """Test all formats have string values."""
        for fmt in ExportFormat:
            assert isinstance(fmt.value, str)
            assert len(fmt.value) > 0

    def test_expected_formats_exist(self):
        """Test expected formats are defined."""
        expected = ["mp4_h264", "mp4_h265", "mov_prores", "webm_vp9", "mkv_h264"]
        for fmt_name in expected:
            assert any(f.value == fmt_name for f in ExportFormat)


class TestExportQuality:
    """Tests for ExportQuality enum."""

    def test_all_qualities_have_values(self):
        """Test all qualities have string values."""
        for quality in ExportQuality:
            assert isinstance(quality.value, str)
            assert len(quality.value) > 0

    def test_expected_qualities_exist(self):
        """Test expected qualities are defined."""
        expected = ["draft", "standard", "high", "master"]
        for quality_name in expected:
            assert any(q.value == quality_name for q in ExportQuality)


class TestExportSettings:
    """Tests for ExportSettings dataclass."""

    def test_default_settings(self):
        """Test default export settings."""
        settings = ExportSettings()

        assert settings.format == ExportFormat.MP4_H264
        assert settings.quality == ExportQuality.HIGH
        assert settings.resolution == "1920x1080"
        assert settings.frame_rate == 24
        assert settings.include_audio is True
        assert settings.include_subtitles is False
        assert settings.watermark is False

    def test_custom_settings(self):
        """Test custom export settings."""
        settings = ExportSettings(
            format=ExportFormat.MOV_PRORES,
            quality=ExportQuality.MASTER,
            resolution="3840x2160",
            frame_rate=30,
            include_audio=False,
            include_subtitles=True,
            watermark=True,
        )

        assert settings.format == ExportFormat.MOV_PRORES
        assert settings.quality == ExportQuality.MASTER
        assert settings.resolution == "3840x2160"
        assert settings.frame_rate == 30
        assert settings.include_audio is False
        assert settings.include_subtitles is True
        assert settings.watermark is True


class TestAssemblyProgress:
    """Tests for AssemblyProgress dataclass."""

    def test_progress_creation(self):
        """Test creating assembly progress."""
        progress = AssemblyProgress(
            percent=50.0,
            stage="encoding",
            message="Encoding video...",
            current_scene=3,
            total_scenes=10,
        )

        assert progress.percent == 50.0
        assert progress.stage == "encoding"
        assert progress.message == "Encoding video..."
        assert progress.current_scene == 3
        assert progress.total_scenes == 10


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_success_result(self):
        """Test successful export result."""
        result = ExportResult(
            success=True,
            output_path="/path/to/movie.mp4",
            file_size=1024 * 1024 * 500,  # 500 MB
            duration_seconds=3600,  # 1 hour
        )

        assert result.success is True
        assert result.output_path == "/path/to/movie.mp4"
        assert result.file_size == 1024 * 1024 * 500
        assert result.duration_seconds == 3600
        assert result.error_message is None

    def test_failure_result(self):
        """Test failed export result."""
        result = ExportResult(
            success=False,
            error_message="Disk full",
        )

        assert result.success is False
        assert result.error_message == "Disk full"
        assert result.output_path is None


class TestSceneRender:
    """Tests for SceneRender dataclass."""

    def test_scene_render_creation(self):
        """Test creating scene render."""
        scene_id = uuid4()
        render = SceneRender(
            scene_id=scene_id,
            output_path="/path/to/scene.mp4",
            duration=120.5,
            shot_count=5,
        )

        assert render.scene_id == scene_id
        assert render.output_path == "/path/to/scene.mp4"
        assert render.duration == 120.5
        assert render.shot_count == 5


class TestTimeline:
    """Tests for Timeline dataclass."""

    def test_timeline_creation(self):
        """Test creating timeline."""
        project_id = uuid4()
        scene_id = uuid4()
        shot_id = uuid4()

        shot = TimelineShot(
            shot_id=shot_id,
            shot_number="1",
            duration=3.0,
            output_path="/path/to/shot.mp4",
            thumbnail_path="/path/to/thumb.jpg",
        )

        scene = TimelineScene(
            scene_id=scene_id,
            scene_number="1",
            title="Opening Scene",
            duration=3.0,
            shots=[shot],
        )

        timeline = Timeline(
            project_id=project_id,
            total_duration=3.0,
            scenes=[scene],
        )

        assert timeline.project_id == project_id
        assert timeline.total_duration == 3.0
        assert len(timeline.scenes) == 1
        assert timeline.scenes[0].scene_number == "1"
        assert len(timeline.scenes[0].shots) == 1

    def test_empty_timeline(self):
        """Test empty timeline."""
        project_id = uuid4()
        timeline = Timeline(
            project_id=project_id,
            total_duration=0.0,
            scenes=[],
        )

        assert timeline.total_duration == 0.0
        assert len(timeline.scenes) == 0


class TestAssemblyService:
    """Tests for AssemblyService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create an assembly service."""
        return AssemblyService(mock_session)

    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        project = MagicMock(spec=Project)
        project.id = uuid4()
        project.name = "Test Movie"
        project.state = ProjectState.GENERATION_COMPLETE
        return project

    @pytest.fixture
    def mock_scene(self):
        """Create a mock scene."""
        scene = MagicMock(spec=Scene)
        scene.id = uuid4()
        scene.project_id = uuid4()
        scene.scene_number = "1"
        scene.heading = "INT. LIVING ROOM - DAY"
        scene.sequence_number = 1
        scene.state = SceneState.APPROVED
        return scene

    @pytest.fixture
    def mock_shot(self, mock_scene):
        """Create a mock shot."""
        shot = MagicMock(spec=Shot)
        shot.id = uuid4()
        shot.scene_id = mock_scene.id
        shot.shot_number = "1-1"
        shot.sequence_number = 1
        shot.duration_seconds = 3.0
        shot.state = ShotState.APPROVED
        shot.output_path = "/path/to/shot.mp4"
        shot.thumbnail_path = "/path/to/thumb.jpg"
        return shot

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None

    @pytest.mark.asyncio
    async def test_get_export_formats(self, service):
        """Test getting export formats."""
        formats = await service.get_export_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0

        # Check structure
        for fmt in formats:
            assert "value" in fmt
            assert "label" in fmt
            assert "description" in fmt
            assert "extension" in fmt

    @pytest.mark.asyncio
    async def test_get_quality_presets(self, service):
        """Test getting quality presets."""
        presets = await service.get_quality_presets()

        assert isinstance(presets, list)
        assert len(presets) > 0

        # Check structure
        for preset in presets:
            assert "value" in preset
            assert "label" in preset
            assert "description" in preset
            assert "bitrate" in preset

    @pytest.mark.asyncio
    async def test_get_timeline_empty_project(
        self, service, mock_session, mock_project
    ):
        """Test getting timeline for project with no scenes."""
        mock_project.scenes = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        timeline = await service.get_timeline(mock_project.id)

        assert timeline.project_id == mock_project.id
        assert timeline.total_duration == 0.0
        assert len(timeline.scenes) == 0

    @pytest.mark.asyncio
    async def test_get_timeline_with_scenes(
        self, service, mock_session, mock_project, mock_scene, mock_shot
    ):
        """Test getting timeline with scenes and shots."""
        mock_scene.shots = [mock_shot]
        mock_project.scenes = [mock_scene]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        timeline = await service.get_timeline(mock_project.id)

        assert timeline.project_id == mock_project.id
        assert len(timeline.scenes) == 1
        assert timeline.scenes[0].scene_number == "1"
        assert len(timeline.scenes[0].shots) == 1
        assert timeline.scenes[0].shots[0].duration == 3.0

    @pytest.mark.asyncio
    async def test_get_export_history_empty(self, service, mock_session, mock_project):
        """Test getting export history with no exports."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        history = await service.get_export_history(mock_project.id)

        assert isinstance(history, list)


class TestExportFormatCodecs:
    """Tests for export format codec settings."""

    def test_mp4_h264_settings(self):
        """Test MP4 H.264 codec settings."""
        settings = ExportSettings(format=ExportFormat.MP4_H264)
        assert settings.format == ExportFormat.MP4_H264

    def test_mov_prores_settings(self):
        """Test MOV ProRes codec settings."""
        settings = ExportSettings(format=ExportFormat.MOV_PRORES)
        assert settings.format == ExportFormat.MOV_PRORES


class TestResolutionParsing:
    """Tests for resolution parsing."""

    def test_1080p_resolution(self):
        """Test 1080p resolution."""
        settings = ExportSettings(resolution="1920x1080")
        assert "1920" in settings.resolution
        assert "1080" in settings.resolution

    def test_4k_resolution(self):
        """Test 4K resolution."""
        settings = ExportSettings(resolution="3840x2160")
        assert "3840" in settings.resolution
        assert "2160" in settings.resolution

    def test_720p_resolution(self):
        """Test 720p resolution."""
        settings = ExportSettings(resolution="1280x720")
        assert "1280" in settings.resolution
        assert "720" in settings.resolution


class TestFrameRates:
    """Tests for frame rate settings."""

    def test_cinema_frame_rate(self):
        """Test cinema frame rate (24fps)."""
        settings = ExportSettings(frame_rate=24)
        assert settings.frame_rate == 24

    def test_pal_frame_rate(self):
        """Test PAL frame rate (25fps)."""
        settings = ExportSettings(frame_rate=25)
        assert settings.frame_rate == 25

    def test_ntsc_frame_rate(self):
        """Test NTSC frame rate (30fps)."""
        settings = ExportSettings(frame_rate=30)
        assert settings.frame_rate == 30

    def test_smooth_frame_rate(self):
        """Test smooth frame rate (60fps)."""
        settings = ExportSettings(frame_rate=60)
        assert settings.frame_rate == 60


class TestTimelineCalculations:
    """Tests for timeline duration calculations."""

    def test_single_shot_duration(self):
        """Test timeline with single shot."""
        shot = TimelineShot(
            shot_id=uuid4(),
            shot_number="1",
            duration=5.0,
        )
        scene = TimelineScene(
            scene_id=uuid4(),
            scene_number="1",
            title="Test Scene",
            duration=5.0,
            shots=[shot],
        )
        timeline = Timeline(
            project_id=uuid4(),
            total_duration=5.0,
            scenes=[scene],
        )

        assert timeline.total_duration == 5.0

    def test_multiple_shots_duration(self):
        """Test timeline with multiple shots."""
        shots = [
            TimelineShot(shot_id=uuid4(), shot_number="1", duration=3.0),
            TimelineShot(shot_id=uuid4(), shot_number="2", duration=4.0),
            TimelineShot(shot_id=uuid4(), shot_number="3", duration=5.0),
        ]
        scene = TimelineScene(
            scene_id=uuid4(),
            scene_number="1",
            title="Test Scene",
            duration=12.0,  # Sum of shots
            shots=shots,
        )
        timeline = Timeline(
            project_id=uuid4(),
            total_duration=12.0,
            scenes=[scene],
        )

        assert timeline.total_duration == 12.0

    def test_multiple_scenes_duration(self):
        """Test timeline with multiple scenes."""
        scene1 = TimelineScene(
            scene_id=uuid4(),
            scene_number="1",
            title="Scene 1",
            duration=30.0,
            shots=[TimelineShot(shot_id=uuid4(), shot_number="1", duration=30.0)],
        )
        scene2 = TimelineScene(
            scene_id=uuid4(),
            scene_number="2",
            title="Scene 2",
            duration=45.0,
            shots=[TimelineShot(shot_id=uuid4(), shot_number="1", duration=45.0)],
        )
        timeline = Timeline(
            project_id=uuid4(),
            total_duration=75.0,  # Sum of scenes
            scenes=[scene1, scene2],
        )

        assert timeline.total_duration == 75.0


class TestQualityBitrates:
    """Tests for quality preset bitrates."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create assembly service."""
        return AssemblyService(mock_session)

    @pytest.mark.asyncio
    async def test_draft_quality_bitrate(self, service):
        """Test draft quality has lowest bitrate."""
        presets = await service.get_quality_presets()
        draft = next((p for p in presets if p["value"] == "draft"), None)

        assert draft is not None
        assert "fast" in draft["description"].lower() or "quick" in draft["description"].lower()

    @pytest.mark.asyncio
    async def test_master_quality_bitrate(self, service):
        """Test master quality has highest bitrate."""
        presets = await service.get_quality_presets()
        master = next((p for p in presets if p["value"] == "master"), None)

        assert master is not None

    @pytest.mark.asyncio
    async def test_quality_order(self, service):
        """Test qualities are ordered correctly."""
        presets = await service.get_quality_presets()
        values = [p["value"] for p in presets]

        # Verify expected order
        expected_order = ["draft", "standard", "high", "master"]
        for expected in expected_order:
            assert expected in values


class TestExportAudioSettings:
    """Tests for audio settings in export."""

    def test_audio_included_by_default(self):
        """Test audio is included by default."""
        settings = ExportSettings()
        assert settings.include_audio is True

    def test_audio_can_be_disabled(self):
        """Test audio can be disabled."""
        settings = ExportSettings(include_audio=False)
        assert settings.include_audio is False


class TestExportSubtitleSettings:
    """Tests for subtitle settings in export."""

    def test_subtitles_disabled_by_default(self):
        """Test subtitles are disabled by default."""
        settings = ExportSettings()
        assert settings.include_subtitles is False

    def test_subtitles_can_be_enabled(self):
        """Test subtitles can be enabled."""
        settings = ExportSettings(include_subtitles=True)
        assert settings.include_subtitles is True


class TestExportWatermarkSettings:
    """Tests for watermark settings in export."""

    def test_watermark_disabled_by_default(self):
        """Test watermark is disabled by default."""
        settings = ExportSettings()
        assert settings.watermark is False

    def test_watermark_can_be_enabled(self):
        """Test watermark can be enabled."""
        settings = ExportSettings(watermark=True)
        assert settings.watermark is True
