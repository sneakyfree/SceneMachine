"""Project duplication service.

Provides functionality to create deep copies of projects including
all characters, scenes, shots, and reference images.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.config import get_settings
from scenemachine.models import (
    Character,
    CharacterLockState,
    Project,
    ProjectState,
    Scene,
    Screenplay,
    Shot,
    ShotState,
)

logger = logging.getLogger(__name__)


class ProjectDuplicator:
    """Service for duplicating projects with all their data."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.settings = get_settings()

    async def duplicate(
        self,
        project_id: UUID,
        new_name: str | None = None,
        include_generated_videos: bool = False,
    ) -> Project:
        """Create a complete copy of a project.

        Args:
            project_id: UUID of the project to duplicate
            new_name: Optional custom name for the new project
            include_generated_videos: Whether to copy generated video files

        Returns:
            The newly created project

        Raises:
            ValueError: If the source project is not found
        """
        # Load source project with all relationships
        source_project = await self._load_project_with_relations(project_id)
        if not source_project:
            raise ValueError(f"Project {project_id} not found")

        # Generate new name if not provided
        if new_name is None:
            new_name = f"{source_project.name} (Copy)"

        # Create ID mappings for relationships
        character_id_map: dict[UUID, UUID] = {}
        scene_id_map: dict[UUID, UUID] = {}

        # Create the new project
        new_project = Project(
            id=uuid4(),
            name=new_name,
            description=source_project.description,
            state=ProjectState.CREATED,  # Reset state to CREATED
            screenplay_parsed=source_project.screenplay_parsed,
            plan_approved=source_project.plan_approved,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(new_project)

        # Copy screenplay if exists
        if source_project.screenplay:
            new_screenplay = await self._copy_screenplay(source_project.screenplay, new_project.id)
            self.session.add(new_screenplay)

        # Copy characters
        for character in source_project.characters:
            new_char, old_id = await self._copy_character(character, new_project.id)
            character_id_map[old_id] = new_char.id
            self.session.add(new_char)

        # Copy scenes and shots
        for scene in source_project.scenes:
            new_scene, old_scene_id = await self._copy_scene(
                scene, new_project.id, include_generated_videos
            )
            scene_id_map[old_scene_id] = new_scene.id
            self.session.add(new_scene)

            # Copy shots for this scene
            for shot in scene.shots:
                new_shot = await self._copy_shot(shot, new_scene.id, include_generated_videos)
                self.session.add(new_shot)

        # Copy reference images (files)
        await self._copy_reference_images(source_project, new_project)

        # Flush to get all IDs assigned
        await self.session.flush()

        logger.info(
            f"Duplicated project {project_id} -> {new_project.id} "
            f"({len(character_id_map)} characters, {len(scene_id_map)} scenes)"
        )

        return new_project

    async def _load_project_with_relations(self, project_id: UUID) -> Project | None:
        """Load project with all relationships eagerly loaded.

        Args:
            project_id: Project UUID to load

        Returns:
            Project with all relations or None if not found
        """
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.screenplay),
                selectinload(Project.characters),
                selectinload(Project.scenes).selectinload(Scene.shots),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _copy_screenplay(self, source: Screenplay, new_project_id: UUID) -> Screenplay:
        """Create a copy of a screenplay.

        Args:
            source: Source screenplay to copy
            new_project_id: ID of the new project

        Returns:
            New screenplay instance
        """
        return Screenplay(
            id=uuid4(),
            project_id=new_project_id,
            title=source.title,
            author=source.author,
            format=source.format,
            content=source.content,
            raw_text=source.raw_text,
            page_count=source.page_count,
            metadata=source.metadata.copy() if source.metadata else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def _copy_character(
        self, source: Character, new_project_id: UUID
    ) -> tuple[Character, UUID]:
        """Create a copy of a character.

        Args:
            source: Source character to copy
            new_project_id: ID of the new project

        Returns:
            Tuple of (new character, old character ID)
        """
        new_char = Character(
            id=uuid4(),
            project_id=new_project_id,
            name=source.name,
            description=source.description,
            dialogue_count=source.dialogue_count,
            first_appearance=source.first_appearance,
            role=source.role,
            lock_state=CharacterLockState.UNLOCKED,  # Reset lock state
            physical_description=source.physical_description.copy()
            if source.physical_description
            else None,
            voice_id=source.voice_id,
            voice_provider=source.voice_provider,
            reference_image_paths=None,  # Will copy files separately
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return new_char, source.id

    async def _copy_scene(
        self, source: Scene, new_project_id: UUID, include_videos: bool
    ) -> tuple[Scene, UUID]:
        """Create a copy of a scene.

        Args:
            source: Source scene to copy
            new_project_id: ID of the new project
            include_videos: Whether to include generated video paths

        Returns:
            Tuple of (new scene, old scene ID)
        """
        new_scene = Scene(
            id=uuid4(),
            project_id=new_project_id,
            scene_number=source.scene_number,
            heading=source.heading,
            int_ext=source.int_ext,
            location=source.location,
            time_of_day=source.time_of_day,
            description=source.description,
            characters=source.characters.copy() if source.characters else [],
            action_lines=source.action_lines.copy() if source.action_lines else [],
            dialogue=source.dialogue.copy() if source.dialogue else [],
            visual_style=source.visual_style,
            mood=source.mood,
            ai_analysis=source.ai_analysis.copy() if source.ai_analysis else None,
            shot_breakdown_approved=False,  # Reset approval
            # Don't copy assembled_video_path unless including videos
            assembled_video_path=source.assembled_video_path if include_videos else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return new_scene, source.id

    async def _copy_shot(self, source: Shot, new_scene_id: UUID, include_videos: bool) -> Shot:
        """Create a copy of a shot.

        Args:
            source: Source shot to copy
            new_scene_id: ID of the new scene
            include_videos: Whether to include generated video paths

        Returns:
            New shot instance
        """
        # Reset status if not including videos
        status = source.status if include_videos else ShotState.PENDING

        return Shot(
            id=uuid4(),
            scene_id=new_scene_id,
            shot_number=source.shot_number,
            shot_type=source.shot_type,
            camera_movement=source.camera_movement,
            description=source.description,
            duration=source.duration,
            status=status,
            # Don't copy generated outputs unless including videos
            output_video_path=source.output_video_path if include_videos else None,
            thumbnail_path=source.thumbnail_path if include_videos else None,
            generation_prompt=source.generation_prompt,
            custom_prompt=source.custom_prompt,
            # Don't copy job metadata
            generation_job_id=None,
            generation_attempts=0,
            last_error=None,
            transition_type=source.transition_type,
            transition_duration=source.transition_duration,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def _copy_reference_images(self, source_project: Project, new_project: Project) -> None:
        """Copy character reference images to new project folder.

        Args:
            source_project: Source project
            new_project: New project
        """
        # Get paths
        data_dir = Path(self.settings.data_dir).expanduser()
        source_dir = data_dir / "projects" / str(source_project.id) / "references"
        dest_dir = data_dir / "projects" / str(new_project.id) / "references"

        if not source_dir.exists():
            return

        # Create destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Find character mapping (old name -> new character)
        char_map = {}
        for old_char in source_project.characters:
            for new_char in [c for c in self.session.new if isinstance(c, Character)]:
                if new_char.project_id == new_project.id and new_char.name == old_char.name:
                    char_map[old_char.name] = new_char
                    break

        # Copy files and update character reference paths
        for old_char in source_project.characters:
            if not old_char.reference_image_paths:
                continue

            new_char = char_map.get(old_char.name)
            if not new_char:
                continue

            new_paths = []
            for old_path in old_char.reference_image_paths:
                old_file = Path(old_path)
                if old_file.exists():
                    # Create new filename with new project/char ID
                    new_filename = f"{new_char.id}_{old_file.name}"
                    new_file = dest_dir / new_filename
                    shutil.copy2(old_file, new_file)
                    new_paths.append(str(new_file))

            if new_paths:
                new_char.reference_image_paths = new_paths


async def duplicate_project(
    session: AsyncSession,
    project_id: UUID,
    new_name: str | None = None,
    include_generated_videos: bool = False,
) -> Project:
    """Convenience function to duplicate a project.

    Args:
        session: Database session
        project_id: UUID of project to duplicate
        new_name: Optional custom name
        include_generated_videos: Whether to copy generated videos

    Returns:
        The newly created project
    """
    duplicator = ProjectDuplicator(session)
    return await duplicator.duplicate(project_id, new_name, include_generated_videos)


# Backwards compatibility alias
ProjectDuplicatorService = ProjectDuplicator
