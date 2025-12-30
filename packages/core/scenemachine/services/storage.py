"""File storage service for managing project assets."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from uuid import UUID

import aiofiles
import aiofiles.os

from scenemachine.config import get_settings


class StorageService:
    """Local file storage service for project assets.

    Directory structure:
    data/
    ├── projects/
    │   └── {project_id}/
    │       ├── screenplay/
    │       │   └── original.fountain
    │       ├── characters/
    │       │   └── {character_id}/
    │       │       ├── references/
    │       │       └── generated/
    │       ├── scenes/
    │       │   └── {scene_id}/
    │       │       └── {shot_id}/
    │       │           ├── generated/
    │       │           └── approved/
    │       └── exports/
    ├── uploads/           # Temporary upload storage
    ├── cache/             # Temporary cache
    └── models/            # ML model storage
    """

    def __init__(self) -> None:
        """Initialize storage service with settings."""
        self.settings = get_settings()
        self.base_dir = self.settings.data_dir

    def _get_project_dir(self, project_id: UUID) -> Path:
        """Get or create project directory."""
        path = self.base_dir / "projects" / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_character_dir(self, project_id: UUID, character_id: UUID) -> Path:
        """Get or create character directory."""
        path = self._get_project_dir(project_id) / "characters" / str(character_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_scene_dir(self, project_id: UUID, scene_id: UUID) -> Path:
        """Get or create scene directory."""
        path = self._get_project_dir(project_id) / "scenes" / str(scene_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_shot_dir(
        self, project_id: UUID, scene_id: UUID, shot_id: UUID
    ) -> Path:
        """Get or create shot directory."""
        path = self._get_scene_dir(project_id, scene_id) / str(shot_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def compute_file_hash(self, file: BinaryIO) -> str:
        """Compute SHA-256 hash of file contents.

        Args:
            file: File object to hash

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()
        file.seek(0)
        while chunk := file.read(8192):
            sha256.update(chunk)
        file.seek(0)
        return sha256.hexdigest()

    async def save_screenplay(
        self,
        project_id: UUID,
        file: BinaryIO,
        filename: str,
    ) -> Tuple[Path, str]:
        """Save screenplay file to project directory.

        Args:
            project_id: Project UUID
            file: File object containing screenplay
            filename: Original filename

        Returns:
            Tuple of (saved_path, file_hash)
        """
        project_dir = self._get_project_dir(project_id)
        screenplay_dir = project_dir / "screenplay"
        screenplay_dir.mkdir(exist_ok=True)

        file_hash = await self.compute_file_hash(file)
        suffix = Path(filename).suffix.lower()
        dest_path = screenplay_dir / f"original{suffix}"

        async with aiofiles.open(dest_path, "wb") as f:
            file.seek(0)
            while chunk := file.read(8192):
                await f.write(chunk)

        return dest_path, file_hash

    async def save_character_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        file: BinaryIO,
        filename: str,
    ) -> Tuple[Path, str]:
        """Save character reference image.

        Args:
            project_id: Project UUID
            character_id: Character UUID
            file: Image file object
            filename: Original filename

        Returns:
            Tuple of (saved_path, file_hash)
        """
        char_dir = self._get_character_dir(project_id, character_id)
        ref_dir = char_dir / "references"
        ref_dir.mkdir(exist_ok=True)

        file_hash = await self.compute_file_hash(file)
        suffix = Path(filename).suffix.lower()
        dest_path = ref_dir / f"{file_hash[:16]}{suffix}"

        # Only save if file doesn't already exist (deduplication)
        if not dest_path.exists():
            async with aiofiles.open(dest_path, "wb") as f:
                file.seek(0)
                while chunk := file.read(8192):
                    await f.write(chunk)

        return dest_path, file_hash

    async def save_generated_character(
        self,
        project_id: UUID,
        character_id: UUID,
        image_data: bytes,
        generation_id: str,
    ) -> Path:
        """Save generated character image.

        Args:
            project_id: Project UUID
            character_id: Character UUID
            image_data: Image bytes
            generation_id: Unique generation identifier

        Returns:
            Path to saved image
        """
        char_dir = self._get_character_dir(project_id, character_id)
        gen_dir = char_dir / "generated"
        gen_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = gen_dir / f"{generation_id}_{timestamp}.png"

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(image_data)

        return dest_path

    async def save_generated_shot(
        self,
        project_id: UUID,
        scene_id: UUID,
        shot_id: UUID,
        video_data: bytes,
        attempt: int = 1,
    ) -> Path:
        """Save generated shot video.

        Args:
            project_id: Project UUID
            scene_id: Scene UUID
            shot_id: Shot UUID
            video_data: Video bytes
            attempt: Generation attempt number

        Returns:
            Path to saved video
        """
        shot_dir = self._get_shot_dir(project_id, scene_id, shot_id)
        gen_dir = shot_dir / "generated"
        gen_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = gen_dir / f"gen_{attempt}_{timestamp}.mp4"

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(video_data)

        return dest_path

    async def approve_shot(
        self,
        project_id: UUID,
        scene_id: UUID,
        shot_id: UUID,
        source_path: Path,
    ) -> Path:
        """Move approved shot to approved directory.

        Args:
            project_id: Project UUID
            scene_id: Scene UUID
            shot_id: Shot UUID
            source_path: Path to generated video

        Returns:
            Path to approved video
        """
        shot_dir = self._get_shot_dir(project_id, scene_id, shot_id)
        approved_dir = shot_dir / "approved"
        approved_dir.mkdir(exist_ok=True)

        dest_path = approved_dir / "final.mp4"

        # Copy to approved directory (keep original for reference)
        await aiofiles.os.makedirs(approved_dir, exist_ok=True)
        shutil.copy2(source_path, dest_path)

        return dest_path

    async def get_file(self, path: Path) -> Optional[bytes]:
        """Read file contents.

        Args:
            path: Path to file

        Returns:
            File contents or None if not found
        """
        if not path.exists():
            return None

        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_file(self, path: Path) -> bool:
        """Delete a file.

        Args:
            path: Path to file

        Returns:
            True if deleted, False if not found
        """
        if path.exists():
            await aiofiles.os.remove(path)
            return True
        return False

    async def delete_project(self, project_id: UUID) -> bool:
        """Delete all project files.

        Args:
            project_id: Project UUID

        Returns:
            True if deleted, False if not found
        """
        project_dir = self.base_dir / "projects" / str(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)
            return True
        return False

    async def get_project_size(self, project_id: UUID) -> int:
        """Calculate total size of project files in bytes.

        Args:
            project_id: Project UUID

        Returns:
            Total size in bytes
        """
        project_dir = self.base_dir / "projects" / str(project_id)
        if not project_dir.exists():
            return 0

        total = 0
        for path in project_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def get_project_size_display(self, size_bytes: int) -> str:
        """Convert bytes to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable size string (e.g., '1.5 GB')
        """
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"


# Global storage service instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
