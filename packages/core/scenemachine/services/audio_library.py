"""Audio library service for managing sound effects and music tracks."""

import hashlib
import logging
import mimetypes
import os
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.audio_asset import (
    AudioAsset,
    AudioAssetType,
    MUSIC_GENRES,
    MUSIC_MOODS,
    SOUND_EFFECT_CATEGORIES,
)

logger = logging.getLogger(__name__)


class AudioLibraryService:
    """Service for managing audio assets (sound effects and music)."""

    SUPPORTED_FORMATS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".webm"}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.settings = get_settings()

    def _get_audio_dir(self, asset_type: AudioAssetType) -> Path:
        """Get the directory for storing audio files.

        Args:
            asset_type: Type of audio asset

        Returns:
            Path to the audio directory
        """
        data_dir = Path(self.settings.data_dir).expanduser()
        subdir = "sfx" if asset_type == AudioAssetType.SOUND_EFFECT else "music"
        audio_dir = data_dir / "assets" / "audio" / subdir
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    async def get_sound_effects(
        self,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        favorites_only: bool = False,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AudioAsset]:
        """Get sound effects with optional filtering.

        Args:
            category: Filter by category
            subcategory: Filter by subcategory
            favorites_only: Only return favorites
            search: Search in name, tags
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching sound effects
        """
        conditions = [AudioAsset.asset_type == AudioAssetType.SOUND_EFFECT]

        if category:
            conditions.append(AudioAsset.category == category)
        if subcategory:
            conditions.append(AudioAsset.subcategory == subcategory)
        if favorites_only:
            conditions.append(AudioAsset.is_favorite == True)
        if search:
            search_pattern = f"%{search.lower()}%"
            conditions.append(
                or_(
                    AudioAsset.name.ilike(search_pattern),
                    AudioAsset.description.ilike(search_pattern),
                )
            )

        stmt = (
            select(AudioAsset)
            .where(and_(*conditions))
            .order_by(AudioAsset.category, AudioAsset.name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_music_tracks(
        self,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        favorites_only: bool = False,
        custom_only: bool = False,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AudioAsset]:
        """Get music tracks with optional filtering.

        Args:
            genre: Filter by genre
            mood: Filter by mood
            favorites_only: Only return favorites
            custom_only: Only return user-uploaded tracks
            search: Search in title, artist, tags
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching music tracks
        """
        conditions = [AudioAsset.asset_type == AudioAssetType.MUSIC]

        if genre:
            conditions.append(AudioAsset.genre == genre)
        if mood:
            conditions.append(AudioAsset.mood.contains([mood]))
        if favorites_only:
            conditions.append(AudioAsset.is_favorite == True)
        if custom_only:
            conditions.append(AudioAsset.is_system == False)
        if search:
            search_pattern = f"%{search.lower()}%"
            conditions.append(
                or_(
                    AudioAsset.name.ilike(search_pattern),
                    AudioAsset.artist.ilike(search_pattern),
                    AudioAsset.description.ilike(search_pattern),
                )
            )

        stmt = (
            select(AudioAsset)
            .where(and_(*conditions))
            .order_by(AudioAsset.name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_audio_asset(self, asset_id: UUID) -> Optional[AudioAsset]:
        """Get a single audio asset by ID.

        Args:
            asset_id: UUID of the asset

        Returns:
            AudioAsset if found, None otherwise
        """
        stmt = select(AudioAsset).where(AudioAsset.id == asset_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def toggle_favorite(self, asset_id: UUID) -> bool:
        """Toggle the favorite status of an audio asset.

        Args:
            asset_id: UUID of the asset

        Returns:
            New favorite status
        """
        asset = await self.get_audio_asset(asset_id)
        if not asset:
            raise ValueError(f"Audio asset {asset_id} not found")

        asset.is_favorite = not asset.is_favorite
        await self.session.commit()
        return asset.is_favorite

    async def upload_audio(
        self,
        file_path: str,
        asset_type: AudioAssetType,
        name: Optional[str] = None,
        category: str = "other",
        subcategory: Optional[str] = None,
        genre: Optional[str] = None,
        mood: Optional[List[str]] = None,
        artist: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> AudioAsset:
        """Upload a new audio file.

        Args:
            file_path: Path to the audio file
            asset_type: Type of audio (SFX or music)
            name: Display name (defaults to filename)
            category: Category for SFX
            subcategory: Subcategory for SFX
            genre: Genre for music
            mood: Mood tags for music
            artist: Artist name for music
            tags: Additional tags

        Returns:
            Created AudioAsset

        Raises:
            ValueError: If file is invalid
        """
        source_path = Path(file_path)

        # Validate file exists
        if not source_path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Validate extension
        ext = source_path.suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {ext}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Validate size
        file_size = source_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum: {self.MAX_FILE_SIZE // (1024*1024)} MB")

        # Generate unique filename
        asset_id = uuid4()
        safe_name = "".join(c for c in source_path.stem if c.isalnum() or c in "-_")[:64]
        new_filename = f"{safe_name}_{str(asset_id)[:8]}{ext}"

        # Determine destination directory
        dest_dir = self._get_audio_dir(asset_type)
        dest_path = dest_dir / new_filename

        # Copy file
        shutil.copy2(source_path, dest_path)

        # Get audio duration (placeholder - would use ffprobe in production)
        duration = await self._get_audio_duration(dest_path)

        # Calculate file hash
        file_hash = self._calculate_hash(dest_path)

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(dest_path))

        # Create asset record
        asset = AudioAsset(
            id=asset_id,
            asset_type=asset_type,
            name=name or source_path.stem,
            file_path=str(dest_path),
            file_size_bytes=file_size,
            duration_seconds=duration,
            mime_type=mime_type,
            category=category,
            subcategory=subcategory,
            genre=genre,
            mood=mood,
            artist=artist,
            tags=tags,
            is_system=False,
        )

        self.session.add(asset)
        await self.session.commit()

        logger.info(f"Uploaded audio asset: {asset.name} ({asset_type.value})")
        return asset

    async def delete_audio(self, asset_id: UUID) -> bool:
        """Delete an audio asset.

        Args:
            asset_id: UUID of the asset

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If asset not found or is a system asset
        """
        asset = await self.get_audio_asset(asset_id)
        if not asset:
            raise ValueError(f"Audio asset {asset_id} not found")

        if asset.is_system:
            raise ValueError("Cannot delete system audio assets")

        # Delete file
        file_path = Path(asset.file_path)
        if file_path.exists():
            file_path.unlink()

        # Delete waveform if exists
        if asset.waveform_path:
            waveform_path = Path(asset.waveform_path)
            if waveform_path.exists():
                waveform_path.unlink()

        # Delete database record
        await self.session.delete(asset)
        await self.session.commit()

        logger.info(f"Deleted audio asset: {asset.name}")
        return True

    async def increment_use_count(self, asset_id: UUID) -> None:
        """Increment the use count for an audio asset.

        Args:
            asset_id: UUID of the asset
        """
        asset = await self.get_audio_asset(asset_id)
        if asset:
            asset.use_count += 1
            await self.session.commit()

    async def get_categories(self) -> dict:
        """Get all sound effect categories with subcategories.

        Returns:
            Dictionary of categories and their subcategories
        """
        return SOUND_EFFECT_CATEGORIES.copy()

    async def get_genres(self) -> List[str]:
        """Get all music genres.

        Returns:
            List of genre names
        """
        return MUSIC_GENRES.copy()

    async def get_moods(self) -> List[str]:
        """Get all music moods.

        Returns:
            List of mood names
        """
        return MUSIC_MOODS.copy()

    async def _get_audio_duration(self, file_path: Path) -> float:
        """Get the duration of an audio file using ffprobe.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            import asyncio
            import json

            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0 and stdout:
                data = json.loads(stdout.decode())
                return float(data.get("format", {}).get("duration", 0))
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")

        return 0.0

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded hash string
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


# Convenience functions

async def get_sound_effects(
    session: AsyncSession,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    favorites_only: bool = False,
    search: Optional[str] = None,
) -> List[AudioAsset]:
    """Get sound effects with optional filtering."""
    service = AudioLibraryService(session)
    return await service.get_sound_effects(
        category=category,
        subcategory=subcategory,
        favorites_only=favorites_only,
        search=search,
    )


async def get_music_tracks(
    session: AsyncSession,
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    favorites_only: bool = False,
    custom_only: bool = False,
    search: Optional[str] = None,
) -> List[AudioAsset]:
    """Get music tracks with optional filtering."""
    service = AudioLibraryService(session)
    return await service.get_music_tracks(
        genre=genre,
        mood=mood,
        favorites_only=favorites_only,
        custom_only=custom_only,
        search=search,
    )
