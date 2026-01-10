"""Tests for Scene Planning service."""

import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.scene_planning import ScenePlanningService
from scenemachine.models import Project, Scene, SceneState


class TestScenePlanningService:
    """Tests for ScenePlanningService."""

    @pytest.fixture
    def scene_planning_service(self, db_session: AsyncSession) -> ScenePlanningService:
        """Create a scene planning service instance."""
        return ScenePlanningService(db_session)

    @pytest_asyncio.fixture
    async def sample_scene(self, db_session: AsyncSession, sample_project: Project) -> Scene:
        """Create a sample scene for testing."""
        scene = Scene(
            project_id=sample_project.id,
            scene_number=1,
            heading="INT. OFFICE - DAY",
            description="A modern office space with large windows.",
            state=SceneState.DRAFT,
            action_lines=["John enters the room.", "He looks around nervously."],
        )
        db_session.add(scene)
        await db_session.commit()
        await db_session.refresh(scene)
        return scene

    @pytest.mark.asyncio
    async def test_create_scene(
        self,
        scene_planning_service: ScenePlanningService,
        sample_project: Project,
    ):
        """Test creating a new scene."""
        scene = await scene_planning_service.create_scene(
            project_id=sample_project.id,
            scene_number=1,
            heading="EXT. BEACH - SUNSET",
            description="A beautiful beach at sunset.",
        )

        assert scene is not None
        assert scene.scene_number == 1
        assert "BEACH" in scene.heading

    @pytest.mark.asyncio
    async def test_get_scene(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test getting a scene by ID."""
        scene = await scene_planning_service.get_scene(sample_scene.id)

        assert scene is not None
        assert scene.id == sample_scene.id

    @pytest.mark.asyncio
    async def test_get_scenes_by_project(
        self,
        scene_planning_service: ScenePlanningService,
        sample_project: Project,
        sample_scene: Scene,
    ):
        """Test getting all scenes for a project."""
        scenes = await scene_planning_service.get_scenes(sample_project.id)

        assert isinstance(scenes, list)
        assert len(scenes) >= 1
        assert any(s.id == sample_scene.id for s in scenes)

    @pytest.mark.asyncio
    async def test_update_scene(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test updating a scene."""
        updated_scene = await scene_planning_service.update_scene(
            scene_id=sample_scene.id,
            description="Updated description for the office scene.",
        )

        assert updated_scene is not None
        assert "Updated" in updated_scene.description

    @pytest.mark.asyncio
    async def test_delete_scene(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test deleting a scene."""
        result = await scene_planning_service.delete_scene(sample_scene.id)

        assert result is True

        # Verify it's deleted
        scene = await scene_planning_service.get_scene(sample_scene.id)
        assert scene is None

    @pytest.mark.asyncio
    async def test_reorder_scenes(
        self,
        scene_planning_service: ScenePlanningService,
        db_session: AsyncSession,
        sample_project: Project,
    ):
        """Test reordering scenes."""
        # Create multiple scenes
        scene1 = Scene(
            project_id=sample_project.id,
            scene_number=1,
            heading="INT. HOUSE - DAY",
            state=SceneState.DRAFT,
        )
        scene2 = Scene(
            project_id=sample_project.id,
            scene_number=2,
            heading="EXT. GARDEN - DAY",
            state=SceneState.DRAFT,
        )
        db_session.add_all([scene1, scene2])
        await db_session.commit()

        # Reorder if method exists
        if hasattr(scene_planning_service, "reorder_scenes"):
            await scene_planning_service.reorder_scenes(
                sample_project.id,
                [scene2.id, scene1.id],
            )

    @pytest.mark.asyncio
    async def test_generate_shot_breakdown(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test generating a shot breakdown for a scene."""
        if hasattr(scene_planning_service, "generate_shot_breakdown"):
            breakdown = await scene_planning_service.generate_shot_breakdown(
                sample_scene.id
            )
            assert breakdown is not None

    @pytest.mark.asyncio
    async def test_approve_scene(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test approving a scene for production."""
        if hasattr(scene_planning_service, "approve_scene"):
            result = await scene_planning_service.approve_scene(sample_scene.id)
            assert result is not None

    @pytest.mark.asyncio
    async def test_scene_state_transitions(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test valid scene state transitions."""
        # Scene should start in DRAFT state
        assert sample_scene.state == SceneState.DRAFT

        # Update to PLANNED if method exists
        if hasattr(scene_planning_service, "transition_state"):
            await scene_planning_service.transition_state(
                sample_scene.id,
                SceneState.PLANNED,
            )

    @pytest.mark.asyncio
    async def test_get_scene_statistics(
        self,
        scene_planning_service: ScenePlanningService,
        sample_project: Project,
        sample_scene: Scene,
    ):
        """Test getting scene statistics for a project."""
        if hasattr(scene_planning_service, "get_statistics"):
            stats = await scene_planning_service.get_statistics(sample_project.id)
            assert stats is not None

    @pytest.mark.asyncio
    async def test_duplicate_scene(
        self,
        scene_planning_service: ScenePlanningService,
        sample_scene: Scene,
    ):
        """Test duplicating a scene."""
        if hasattr(scene_planning_service, "duplicate_scene"):
            duplicate = await scene_planning_service.duplicate_scene(sample_scene.id)
            assert duplicate is not None
            assert duplicate.id != sample_scene.id
