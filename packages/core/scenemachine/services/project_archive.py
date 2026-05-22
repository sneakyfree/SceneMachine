"""Project archive service for import/export functionality."""

import json
import logging
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.config import get_settings
from scenemachine.models import Character, Project, Scene, Screenplay, Shot

logger = logging.getLogger(__name__)


@dataclass
class ArchiveManifest:
    """Archive manifest containing project metadata."""

    version: str
    created_at: str
    project_id: str
    project_name: str
    includes_assets: bool
    includes_outputs: bool
    file_count: int
    total_size_bytes: int


@dataclass
class ImportResult:
    """Result of importing an archive."""

    success: bool
    project_id: str | None
    project_name: str | None
    scenes_imported: int
    shots_imported: int
    characters_imported: int
    assets_imported: int
    warnings: list[str]
    error: str | None


@dataclass
class ExportResult:
    """Result of exporting a project."""

    success: bool
    archive_path: str | None
    file_size_bytes: int
    manifest: ArchiveManifest | None
    error: str | None


class ProjectArchiveService:
    """Service for importing and exporting project archives."""

    ARCHIVE_VERSION = "1.0"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def export_project(
        self,
        project_id: UUID,
        output_path: Path | None = None,
        include_assets: bool = True,
        include_outputs: bool = True,
        include_generated_videos: bool = False,
    ) -> ExportResult:
        """Export a project to a ZIP archive.

        Args:
            project_id: Project UUID to export
            output_path: Optional output path (defaults to exports directory)
            include_assets: Include uploaded assets (images, references)
            include_outputs: Include output files (thumbnails)
            include_generated_videos: Include generated video files (can be large)

        Returns:
            ExportResult with archive path and metadata
        """
        try:
            # Fetch project with all related data
            project = await self._fetch_project_data(project_id)
            if not project:
                return ExportResult(
                    success=False,
                    archive_path=None,
                    file_size_bytes=0,
                    manifest=None,
                    error=f"Project {project_id} not found",
                )

            # Determine output path
            if output_path is None:
                exports_dir = self.settings.data_dir / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project.name)
                output_path = exports_dir / f"{safe_name}_{timestamp}.smproject"

            # Create temporary directory for archive contents
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                file_count = 0
                total_size = 0

                # Export project data as JSON
                project_data = await self._serialize_project(project)
                project_json_path = temp_path / "project.json"
                with open(project_json_path, "w") as f:
                    json.dump(project_data, f, indent=2, default=str)
                file_count += 1
                total_size += project_json_path.stat().st_size

                # Export screenplay if exists
                if project.screenplay:
                    screenplay_data = {
                        "id": str(project.screenplay.id),
                        "title": project.screenplay.title,
                        "format": project.screenplay.format,
                        "content": project.screenplay.content,
                        "parsed_content": project.screenplay.parsed_content,
                        "metadata": project.screenplay.metadata,
                    }
                    screenplay_path = temp_path / "screenplay.json"
                    with open(screenplay_path, "w") as f:
                        json.dump(screenplay_data, f, indent=2, default=str)
                    file_count += 1
                    total_size += screenplay_path.stat().st_size

                # Export assets
                if include_assets:
                    assets_dir = temp_path / "assets"
                    assets_dir.mkdir(exist_ok=True)

                    # Character reference images
                    for character in project.characters:
                        if character.reference_images:
                            char_dir = assets_dir / "characters" / str(character.id)
                            char_dir.mkdir(parents=True, exist_ok=True)
                            for i, ref in enumerate(character.reference_images):
                                if isinstance(ref, str) and Path(ref).exists():
                                    dest = char_dir / f"reference_{i}{Path(ref).suffix}"
                                    shutil.copy2(ref, dest)
                                    file_count += 1
                                    total_size += dest.stat().st_size

                # Export outputs (thumbnails)
                if include_outputs:
                    outputs_dir = temp_path / "outputs"
                    outputs_dir.mkdir(exist_ok=True)

                    for scene in project.scenes:
                        for shot in scene.shots:
                            if shot.thumbnail_path:
                                thumb_path = Path(shot.thumbnail_path)
                                if thumb_path.exists():
                                    shot_dir = outputs_dir / "shots" / str(shot.id)
                                    shot_dir.mkdir(parents=True, exist_ok=True)
                                    dest = shot_dir / "thumbnail.jpg"
                                    shutil.copy2(thumb_path, dest)
                                    file_count += 1
                                    total_size += dest.stat().st_size

                # Export generated videos (optional, can be large)
                if include_generated_videos:
                    videos_dir = temp_path / "videos"
                    videos_dir.mkdir(exist_ok=True)

                    for scene in project.scenes:
                        for shot in scene.shots:
                            if shot.output_path:
                                video_path = Path(shot.output_path)
                                if video_path.exists():
                                    shot_dir = videos_dir / str(shot.id)
                                    shot_dir.mkdir(parents=True, exist_ok=True)
                                    dest = shot_dir / "output.mp4"
                                    shutil.copy2(video_path, dest)
                                    file_count += 1
                                    total_size += dest.stat().st_size

                # Create manifest
                manifest = ArchiveManifest(
                    version=self.ARCHIVE_VERSION,
                    created_at=datetime.now(UTC).isoformat(),
                    project_id=str(project_id),
                    project_name=project.name,
                    includes_assets=include_assets,
                    includes_outputs=include_outputs,
                    file_count=file_count,
                    total_size_bytes=total_size,
                )

                manifest_path = temp_path / "manifest.json"
                with open(manifest_path, "w") as f:
                    json.dump(manifest.__dict__, f, indent=2)

                # Create ZIP archive
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_path in temp_path.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_path)
                            zf.write(file_path, arcname)

            archive_size = output_path.stat().st_size

            logger.info(f"Exported project {project_id} to {output_path} ({archive_size} bytes)")

            return ExportResult(
                success=True,
                archive_path=str(output_path),
                file_size_bytes=archive_size,
                manifest=manifest,
                error=None,
            )

        except Exception as e:
            logger.exception(f"Failed to export project {project_id}")
            return ExportResult(
                success=False,
                archive_path=None,
                file_size_bytes=0,
                manifest=None,
                error=str(e),
            )

    async def import_project(
        self,
        archive_path: Path,
        new_name: str | None = None,
        import_assets: bool = True,
    ) -> ImportResult:
        """Import a project from a ZIP archive.

        Args:
            archive_path: Path to the archive file
            new_name: Optional new name for the project
            import_assets: Whether to import asset files

        Returns:
            ImportResult with imported project details
        """
        warnings: list[str] = []

        try:
            if not archive_path.exists():
                return ImportResult(
                    success=False,
                    project_id=None,
                    project_name=None,
                    scenes_imported=0,
                    shots_imported=0,
                    characters_imported=0,
                    assets_imported=0,
                    warnings=[],
                    error=f"Archive file not found: {archive_path}",
                )

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract archive
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(temp_path)

                # Read manifest
                manifest_path = temp_path / "manifest.json"
                if not manifest_path.exists():
                    return ImportResult(
                        success=False,
                        project_id=None,
                        project_name=None,
                        scenes_imported=0,
                        shots_imported=0,
                        characters_imported=0,
                        assets_imported=0,
                        warnings=[],
                        error="Invalid archive: manifest.json not found",
                    )

                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Check version compatibility
                if manifest.get("version", "0") > self.ARCHIVE_VERSION:
                    warnings.append(
                        f"Archive version {manifest.get('version')} may not be fully compatible"
                    )

                # Read project data
                project_json_path = temp_path / "project.json"
                if not project_json_path.exists():
                    return ImportResult(
                        success=False,
                        project_id=None,
                        project_name=None,
                        scenes_imported=0,
                        shots_imported=0,
                        characters_imported=0,
                        assets_imported=0,
                        warnings=warnings,
                        error="Invalid archive: project.json not found",
                    )

                with open(project_json_path) as f:
                    project_data = json.load(f)

                # Create new project
                project_name = new_name or project_data.get("name", "Imported Project")

                # Check for duplicate name
                existing = await self.session.execute(
                    select(Project).where(Project.name == project_name)
                )
                if existing.scalar_one_or_none():
                    project_name = f"{project_name} (Imported)"

                project = Project(
                    name=project_name,
                    description=project_data.get("description"),
                    settings=project_data.get("settings", {}),
                )
                self.session.add(project)
                await self.session.flush()

                # Import screenplay if exists
                screenplay_path = temp_path / "screenplay.json"
                if screenplay_path.exists():
                    with open(screenplay_path) as f:
                        screenplay_data = json.load(f)

                    screenplay = Screenplay(
                        project_id=project.id,
                        title=screenplay_data.get("title", project_name),
                        format=screenplay_data.get("format", "text"),
                        content=screenplay_data.get("content", ""),
                        parsed_content=screenplay_data.get("parsed_content"),
                        metadata=screenplay_data.get("metadata", {}),
                    )
                    self.session.add(screenplay)

                # Import characters
                characters_imported = 0
                character_id_map: dict[str, UUID] = {}

                for char_data in project_data.get("characters", []):
                    old_id = char_data.get("id")
                    character = Character(
                        project_id=project.id,
                        name=char_data.get("name"),
                        description=char_data.get("description"),
                        visual_description=char_data.get("visual_description"),
                        age=char_data.get("age"),
                        gender=char_data.get("gender"),
                        reference_images=[],  # Will be updated if assets imported
                        style_notes=char_data.get("style_notes"),
                        metadata=char_data.get("metadata", {}),
                    )
                    self.session.add(character)
                    await self.session.flush()

                    if old_id:
                        character_id_map[old_id] = character.id

                    characters_imported += 1

                # Import scenes and shots
                scenes_imported = 0
                shots_imported = 0
                assets_imported = 0

                for scene_data in project_data.get("scenes", []):
                    scene = Scene(
                        project_id=project.id,
                        sequence_number=scene_data.get("sequence_number", scenes_imported + 1),
                        title=scene_data.get("title"),
                        location=scene_data.get("location"),
                        time_of_day=scene_data.get("time_of_day"),
                        description=scene_data.get("description"),
                        screenplay_text=scene_data.get("screenplay_text"),
                        metadata=scene_data.get("metadata", {}),
                    )
                    self.session.add(scene)
                    await self.session.flush()
                    scenes_imported += 1

                    # Import shots
                    for shot_data in scene_data.get("shots", []):
                        shot = Shot(
                            scene_id=scene.id,
                            project_id=project.id,
                            shot_number=shot_data.get("shot_number", f"{scenes_imported}.{shots_imported + 1}"),
                            sequence_number=shot_data.get("sequence_number", shots_imported + 1),
                            shot_type=shot_data.get("shot_type", "medium"),
                            camera_movement=shot_data.get("camera_movement", "static"),
                            camera_angle=shot_data.get("camera_angle", "eye_level"),
                            description=shot_data.get("description"),
                            action=shot_data.get("action"),
                            dialogue=shot_data.get("dialogue"),
                            duration_seconds=shot_data.get("duration_seconds", 3.0),
                            composition_notes=shot_data.get("composition_notes"),
                            lighting_notes=shot_data.get("lighting_notes"),
                            generation_prompt=shot_data.get("generation_prompt"),
                            negative_prompt=shot_data.get("negative_prompt"),
                            metadata=shot_data.get("metadata", {}),
                        )
                        self.session.add(shot)
                        shots_imported += 1

                # Import assets if requested
                if import_assets:
                    assets_dir = temp_path / "assets"
                    if assets_dir.exists():
                        dest_assets_dir = self.settings.data_dir / "assets" / str(project.id)
                        dest_assets_dir.mkdir(parents=True, exist_ok=True)

                        for asset_file in assets_dir.rglob("*"):
                            if asset_file.is_file():
                                rel_path = asset_file.relative_to(assets_dir)
                                dest_path = dest_assets_dir / rel_path
                                dest_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(asset_file, dest_path)
                                assets_imported += 1

                await self.session.commit()

                logger.info(
                    f"Imported project {project.id} with "
                    f"{scenes_imported} scenes, {shots_imported} shots, "
                    f"{characters_imported} characters, {assets_imported} assets"
                )

                return ImportResult(
                    success=True,
                    project_id=str(project.id),
                    project_name=project.name,
                    scenes_imported=scenes_imported,
                    shots_imported=shots_imported,
                    characters_imported=characters_imported,
                    assets_imported=assets_imported,
                    warnings=warnings,
                    error=None,
                )

        except Exception as e:
            logger.exception(f"Failed to import archive {archive_path}")
            await self.session.rollback()
            return ImportResult(
                success=False,
                project_id=None,
                project_name=None,
                scenes_imported=0,
                shots_imported=0,
                characters_imported=0,
                assets_imported=0,
                warnings=warnings,
                error=str(e),
            )

    async def _fetch_project_data(self, project_id: UUID) -> Project | None:
        """Fetch project with all related data."""
        stmt = (
            select(Project)
            .options(
                selectinload(Project.screenplay),
                selectinload(Project.characters),
                selectinload(Project.scenes).selectinload(Scene.shots),
            )
            .where(Project.id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _serialize_project(self, project: Project) -> dict[str, Any]:
        """Serialize project to dictionary for JSON export."""
        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "state": project.state.value if project.state else None,
            "settings": project.settings or {},
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "characters": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "description": c.description,
                    "visual_description": c.visual_description,
                    "age": c.age,
                    "gender": c.gender,
                    "reference_images": c.reference_images,
                    "style_notes": c.style_notes,
                    "metadata": c.metadata or {},
                }
                for c in project.characters
            ],
            "scenes": [
                {
                    "id": str(s.id),
                    "sequence_number": s.sequence_number,
                    "title": s.title,
                    "location": s.location,
                    "time_of_day": s.time_of_day,
                    "description": s.description,
                    "screenplay_text": s.screenplay_text,
                    "metadata": s.metadata or {},
                    "shots": [
                        {
                            "id": str(shot.id),
                            "shot_number": shot.shot_number,
                            "sequence_number": shot.sequence_number,
                            "shot_type": shot.shot_type.value if shot.shot_type else None,
                            "camera_movement": shot.camera_movement.value if shot.camera_movement else None,
                            "camera_angle": shot.camera_angle.value if shot.camera_angle else None,
                            "description": shot.description,
                            "action": shot.action,
                            "dialogue": shot.dialogue,
                            "duration_seconds": shot.duration_seconds,
                            "composition_notes": shot.composition_notes,
                            "lighting_notes": shot.lighting_notes,
                            "generation_prompt": shot.generation_prompt,
                            "negative_prompt": shot.negative_prompt,
                            "metadata": shot.metadata or {},
                        }
                        for shot in sorted(s.shots, key=lambda x: x.sequence_number)
                    ],
                }
                for s in sorted(project.scenes, key=lambda x: x.sequence_number)
            ],
        }

    async def get_archive_info(self, archive_path: Path) -> ArchiveManifest | None:
        """Get information about an archive without importing.

        Args:
            archive_path: Path to the archive file

        Returns:
            ArchiveManifest or None if invalid
        """
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    return None

                with zf.open("manifest.json") as f:
                    data = json.load(f)

                return ArchiveManifest(**data)

        except Exception as e:
            logger.warning(f"Failed to read archive info: {e}")
            return None

    async def list_exports(self) -> list[dict[str, Any]]:
        """List all exported archives."""
        exports_dir = self.settings.data_dir / "exports"
        if not exports_dir.exists():
            return []

        archives = []
        for path in exports_dir.glob("*.smproject"):
            try:
                manifest = await self.get_archive_info(path)
                archives.append({
                    "path": str(path),
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "manifest": manifest.__dict__ if manifest else None,
                })
            except Exception:
                pass

        return sorted(archives, key=lambda x: x["created_at"], reverse=True)
