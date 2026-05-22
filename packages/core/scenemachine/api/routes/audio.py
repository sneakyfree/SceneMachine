"""Audio library API routes for sound effects and music."""

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.models.audio_asset import (
    MUSIC_GENRES,
    MUSIC_MOODS,
    SOUND_EFFECT_CATEGORIES,
    AudioAsset,
    AudioAssetType,
)
from scenemachine.services.audio_library import AudioLibraryService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Response Models ============


class SoundEffectResponse(BaseModel):
    """Response model for a sound effect."""

    id: str
    name: str
    category: str
    subcategory: str | None = None
    duration: float
    audioUrl: str
    tags: list[str]
    isFavorite: bool
    isCustom: bool

    @classmethod
    def from_model(cls, asset: AudioAsset) -> "SoundEffectResponse":
        return cls(
            id=str(asset.id),
            name=asset.name,
            category=asset.category,
            subcategory=asset.subcategory,
            duration=asset.duration_seconds,
            audioUrl=f"file://{asset.file_path}",
            tags=asset.tags or [],
            isFavorite=asset.is_favorite,
            isCustom=not asset.is_system,
        )


class MusicTrackResponse(BaseModel):
    """Response model for a music track."""

    id: str
    title: str
    artist: str | None = None
    duration: float
    genre: str
    mood: list[str]
    bpm: int | None = None
    audioUrl: str
    waveformUrl: str | None = None
    isFavorite: bool
    isCustom: bool
    tags: list[str]

    @classmethod
    def from_model(cls, asset: AudioAsset) -> "MusicTrackResponse":
        return cls(
            id=str(asset.id),
            title=asset.name,
            artist=asset.artist,
            duration=asset.duration_seconds,
            genre=asset.genre or "Cinematic",
            mood=asset.mood or [],
            bpm=asset.bpm,
            audioUrl=f"file://{asset.file_path}",
            waveformUrl=f"file://{asset.waveform_path}" if asset.waveform_path else None,
            isFavorite=asset.is_favorite,
            isCustom=not asset.is_system,
            tags=asset.tags or [],
        )


class CategoryResponse(BaseModel):
    """Response model for a category."""

    id: str
    name: str
    icon: str
    subcategories: list[str]
    count: int


class UploadResponse(BaseModel):
    """Response for audio upload."""

    success: bool
    id: str | None = None
    name: str | None = None
    error: str | None = None


# ============ Sound Effects Endpoints ============


@router.get("/sfx", response_model=list[SoundEffectResponse])
async def get_sound_effects(
    category: str | None = None,
    subcategory: str | None = None,
    favorites_only: bool = False,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[SoundEffectResponse]:
    """Get sound effects with optional filtering."""
    service = AudioLibraryService(db)
    effects = await service.get_sound_effects(
        category=category,
        subcategory=subcategory,
        favorites_only=favorites_only,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [SoundEffectResponse.from_model(e) for e in effects]


@router.get("/sfx/categories")
async def get_sfx_categories() -> dict[str, Any]:
    """Get all sound effect categories."""
    # Map categories to frontend format
    categories = []
    icons = {
        "ambience": "🌿",
        "foley": "👣",
        "impacts": "💥",
        "whooshes": "💨",
        "risers": "📈",
        "ui": "🔔",
        "vehicles": "🚗",
        "weapons": "⚔️",
        "animals": "🐕",
        "voice": "🗣️",
    }

    for cat_id, subcats in SOUND_EFFECT_CATEGORIES.items():
        categories.append(
            {
                "id": cat_id,
                "name": cat_id.replace("_", " ").title(),
                "icon": icons.get(cat_id, "📁"),
                "subcategories": subcats,
                "count": 0,  # Would be filled with actual counts
            }
        )

    return {"categories": categories}


@router.get("/sfx/{effect_id}", response_model=SoundEffectResponse)
async def get_sound_effect(
    effect_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SoundEffectResponse:
    """Get a specific sound effect."""
    service = AudioLibraryService(db)
    effect = await service.get_audio_asset(effect_id)

    if not effect or effect.asset_type != AudioAssetType.SOUND_EFFECT:
        raise HTTPException(status_code=404, detail="Sound effect not found")

    return SoundEffectResponse.from_model(effect)


@router.post("/sfx/{effect_id}/favorite")
async def toggle_sfx_favorite(
    effect_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Toggle favorite status for a sound effect."""
    service = AudioLibraryService(db)
    try:
        new_status = await service.toggle_favorite(effect_id)
        return {"isFavorite": new_status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sfx/upload", response_model=UploadResponse)
async def upload_sound_effect(
    file: UploadFile = File(...),
    category: str = "other",
    subcategory: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Upload a custom sound effect."""
    import tempfile

    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename or "audio.mp3").suffix
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        service = AudioLibraryService(db)
        asset = await service.upload_audio(
            file_path=tmp_path,
            asset_type=AudioAssetType.SOUND_EFFECT,
            name=Path(file.filename or "Sound Effect").stem,
            category=category,
            subcategory=subcategory,
        )

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        return UploadResponse(
            success=True,
            id=str(asset.id),
            name=asset.name,
        )

    except Exception as e:
        logger.error(f"Failed to upload sound effect: {e}")
        return UploadResponse(success=False, error=str(e))


@router.delete("/sfx/{effect_id}")
async def delete_sound_effect(
    effect_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Delete a custom sound effect."""
    service = AudioLibraryService(db)
    try:
        await service.delete_audio(effect_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Music Endpoints ============


@router.get("/music", response_model=list[MusicTrackResponse])
async def get_music_tracks(
    genre: str | None = None,
    mood: str | None = None,
    favorites_only: bool = False,
    custom_only: bool = False,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[MusicTrackResponse]:
    """Get music tracks with optional filtering."""
    service = AudioLibraryService(db)
    tracks = await service.get_music_tracks(
        genre=genre,
        mood=mood,
        favorites_only=favorites_only,
        custom_only=custom_only,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [MusicTrackResponse.from_model(t) for t in tracks]


@router.get("/music/genres")
async def get_music_genres() -> dict[str, list[str]]:
    """Get all music genres."""
    return {"genres": MUSIC_GENRES}


@router.get("/music/moods")
async def get_music_moods() -> dict[str, list[str]]:
    """Get all music moods."""
    return {"moods": MUSIC_MOODS}


@router.get("/music/{track_id}", response_model=MusicTrackResponse)
async def get_music_track(
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MusicTrackResponse:
    """Get a specific music track."""
    service = AudioLibraryService(db)
    track = await service.get_audio_asset(track_id)

    if not track or track.asset_type != AudioAssetType.MUSIC:
        raise HTTPException(status_code=404, detail="Music track not found")

    return MusicTrackResponse.from_model(track)


@router.post("/music/{track_id}/favorite")
async def toggle_music_favorite(
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Toggle favorite status for a music track."""
    service = AudioLibraryService(db)
    try:
        new_status = await service.toggle_favorite(track_id)
        return {"isFavorite": new_status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/music/upload", response_model=UploadResponse)
async def upload_music_track(
    file: UploadFile = File(...),
    genre: str = "Cinematic",
    mood: str | None = None,
    artist: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Upload a custom music track."""
    import tempfile

    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename or "audio.mp3").suffix
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        moods = [mood] if mood else None

        service = AudioLibraryService(db)
        asset = await service.upload_audio(
            file_path=tmp_path,
            asset_type=AudioAssetType.MUSIC,
            name=Path(file.filename or "Music Track").stem,
            genre=genre,
            mood=moods,
            artist=artist,
        )

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        return UploadResponse(
            success=True,
            id=str(asset.id),
            name=asset.name,
        )

    except Exception as e:
        logger.error(f"Failed to upload music track: {e}")
        return UploadResponse(success=False, error=str(e))


@router.delete("/music/{track_id}")
async def delete_music_track(
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Delete a custom music track."""
    service = AudioLibraryService(db)
    try:
        await service.delete_audio(track_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
