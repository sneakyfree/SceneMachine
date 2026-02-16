"""Character API routes."""

import logging
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.models.character import CharacterGender, CharacterLockState
from scenemachine.services.character import CharacterService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/characters", tags=["characters"])


# Request/Response schemas
class PhysicalDescriptionSchema(BaseModel):
    """Physical description schema."""

    hair_color: str = ""
    hair_style: str = ""
    eye_color: str = ""
    skin_tone: str = ""
    height: str = ""
    build: str = ""
    distinguishing_features: List[str] = Field(default_factory=list)
    clothing_style: str = ""
    additional_notes: str = ""


class CharacterUpdateRequest(BaseModel):
    """Request to update a character."""

    name: Optional[str] = None
    description: Optional[str] = None
    age_range_min: Optional[int] = None
    age_range_max: Optional[int] = None
    gender: Optional[CharacterGender] = None
    physical_description: Optional[PhysicalDescriptionSchema] = None
    personality_traits: Optional[List[str]] = None
    voice_description: Optional[str] = None
    is_protagonist: Optional[bool] = None


class AssetResponse(BaseModel):
    """Asset response schema."""

    id: str
    asset_type: str
    original_filename: str
    file_path: str
    is_primary: bool = False
    created_at: str


class CharacterResponse(BaseModel):
    """Character response schema."""

    id: str
    project_id: str
    name: str
    screenplay_name: str
    description: Optional[str]
    age_range_min: Optional[int]
    age_range_max: Optional[int]
    age_range_display: Optional[str]
    gender: str
    physical_description: Optional[Dict[str, Any]]
    personality_traits: Optional[List[str]]
    voice_description: Optional[str]
    lock_state: str
    is_locked: bool
    locked_likeness: Optional[Dict[str, Any]]
    scene_count: int
    dialogue_count: int
    is_protagonist: bool
    reference_assets: List[AssetResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class CharacterListResponse(BaseModel):
    """List of characters response."""

    characters: List[CharacterResponse]
    total: int
    locked_count: int


class GenerateDescriptionResponse(BaseModel):
    """Response from description generation."""

    description: str
    estimated_age: Optional[int]
    gender: Optional[str]
    personality_traits: List[str]
    physical_description: Dict[str, Any]


class LockCharacterRequest(BaseModel):
    """Request to lock a character."""

    primary_reference_id: Optional[str] = None


class CharacterPromptResponse(BaseModel):
    """Generated prompts for a character."""

    positive_prompt: str
    negative_prompt: str
    style_prompt: str
    consistency_tokens: List[str]


def _character_to_response(character: Any) -> CharacterResponse:
    """Convert Character model to response schema."""
    reference_assets = []
    if hasattr(character, "reference_assets") and character.reference_assets:
        for asset in character.reference_assets:
            is_primary = (
                asset.metadata.get("is_primary", False)
                if asset.metadata
                else False
            )
            reference_assets.append(
                AssetResponse(
                    id=str(asset.id),
                    asset_type=asset.asset_type.value,
                    original_filename=asset.original_filename,
                    file_path=asset.file_path,
                    is_primary=is_primary,
                    created_at=asset.created_at.isoformat(),
                )
            )

    return CharacterResponse(
        id=str(character.id),
        project_id=str(character.project_id),
        name=character.name,
        screenplay_name=character.screenplay_name,
        description=character.description,
        age_range_min=character.age_range_min,
        age_range_max=character.age_range_max,
        age_range_display=character.age_range_display,
        gender=character.gender.value,
        physical_description=character.physical_description,
        personality_traits=character.personality_traits,
        voice_description=character.voice_description,
        lock_state=character.lock_state.value,
        is_locked=character.is_locked,
        locked_likeness=character.locked_likeness,
        scene_count=character.scene_count,
        dialogue_count=character.dialogue_count,
        is_protagonist=character.is_protagonist,
        reference_assets=reference_assets,
        created_at=character.created_at.isoformat(),
        updated_at=character.updated_at.isoformat(),
    )


@router.get(
    "/project/{project_id}",
    response_model=CharacterListResponse,
)
async def get_project_characters(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CharacterListResponse:
    """Get all characters for a project."""
    service = CharacterService(session)
    characters = await service.get_project_characters(
        project_id,
        include_references=True,
    )

    return CharacterListResponse(
        characters=[_character_to_response(c) for c in characters],
        total=len(characters),
        locked_count=sum(1 for c in characters if c.is_locked),
    )


@router.get(
    "/{character_id}",
    response_model=CharacterResponse,
)
async def get_character(
    character_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CharacterResponse:
    """Get a character by ID."""
    service = CharacterService(session)
    character = await service.get_character(character_id, include_references=True)

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    return _character_to_response(character)


@router.patch(
    "/{character_id}",
    response_model=CharacterResponse,
)
async def update_character(
    character_id: UUID,
    request: CharacterUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CharacterResponse:
    """Update a character's details."""
    service = CharacterService(session)

    try:
        character = await service.update_character(
            character_id=character_id,
            name=request.name,
            description=request.description,
            age_range_min=request.age_range_min,
            age_range_max=request.age_range_max,
            gender=request.gender,
            physical_description=(
                request.physical_description.model_dump()
                if request.physical_description
                else None
            ),
            personality_traits=request.personality_traits,
            voice_description=request.voice_description,
            is_protagonist=request.is_protagonist,
        )

        return _character_to_response(character)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{character_id}/generate-description",
    response_model=GenerateDescriptionResponse,
)
async def generate_character_description(
    character_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GenerateDescriptionResponse:
    """Generate character description from screenplay context."""
    service = CharacterService(session)

    try:
        result = await service.generate_character_description(character_id)

        return GenerateDescriptionResponse(
            description=result.get("description", ""),
            estimated_age=result.get("estimated_age"),
            gender=result.get("gender"),
            personality_traits=result.get("personality_traits", []),
            physical_description=result.get("physical_description", {}),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{character_id}/reference",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_reference_image(
    character_id: UUID,
    file: Annotated[UploadFile, File(description="Reference image")],
    session: Annotated[AsyncSession, Depends(get_session)],
    is_primary: bool = False,
) -> AssetResponse:
    """Upload a reference image for a character."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    service = CharacterService(session)

    try:
        asset = await service.upload_reference_image(
            character_id=character_id,
            file=file.file,
            filename=file.filename,
            is_primary=is_primary,
        )

        return AssetResponse(
            id=str(asset.id),
            asset_type=asset.asset_type.value,
            original_filename=asset.original_filename,
            file_path=asset.file_path,
            is_primary=is_primary,
            created_at=asset.created_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{character_id}/reference/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reference_image(
    character_id: UUID,
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a reference image."""
    service = CharacterService(session)

    try:
        deleted = await service.delete_reference_image(character_id, asset_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference image not found",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{character_id}/lock",
    response_model=CharacterResponse,
)
async def lock_character(
    character_id: UUID,
    request: LockCharacterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CharacterResponse:
    """Lock a character's likeness."""
    service = CharacterService(session)

    try:
        primary_ref_id = (
            UUID(request.primary_reference_id)
            if request.primary_reference_id
            else None
        )

        character = await service.lock_character(
            character_id=character_id,
            primary_reference_id=primary_ref_id,
        )

        return _character_to_response(character)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{character_id}/unlock",
    response_model=CharacterResponse,
)
async def unlock_character(
    character_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CharacterResponse:
    """Unlock a character for editing."""
    service = CharacterService(session)

    try:
        character = await service.unlock_character(character_id)
        return _character_to_response(character)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{character_id}/prompt",
    response_model=CharacterPromptResponse,
)
async def get_character_prompt(
    character_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    scene_context: Optional[str] = None,
) -> CharacterPromptResponse:
    """Get AI generation prompts for a character."""
    service = CharacterService(session)
    character = await service.get_character(character_id)

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    prompt = service.generate_character_prompt(character, scene_context)

    return CharacterPromptResponse(
        positive_prompt=prompt.positive_prompt,
        negative_prompt=prompt.negative_prompt,
        style_prompt=prompt.style_prompt,
        consistency_tokens=prompt.consistency_tokens,
    )


# ---- FEAT-023: AI Reference Image Generation ----


class GenerateImageRequest(BaseModel):
    """Request to generate an AI reference image."""

    style: str = "realistic"
    num_images: int = 1
    enhance_for: str = "consistency"


class GenerateImageResponse(BaseModel):
    """Response from image generation."""

    images: List[Dict[str, Any]]
    character_id: str
    style: str


@router.post(
    "/{character_id}/generate-image",
    response_model=GenerateImageResponse,
)
async def generate_character_image(
    character_id: UUID,
    request: GenerateImageRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GenerateImageResponse:
    """Generate an AI reference image for a character.

    Uses the character's description and physical attributes to generate
    a reference image via the configured image generation provider.
    """
    service = CharacterService(session)
    character = await service.get_character(character_id)

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    try:
        from scenemachine.services.character_image_generator import (
            CharacterImageGenerator,
        )

        generator = CharacterImageGenerator()
        images = await generator.generate_reference_images(
            character_description=character.description or character.name,
            physical_description=character.physical_description or {},
            style=request.style,
            num_images=request.num_images,
            enhance_for=request.enhance_for,
        )

        return GenerateImageResponse(
            images=images,
            character_id=str(character_id),
            style=request.style,
        )

    except Exception as e:
        logger.error(f"Image generation failed for character {character_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image generation failed: {str(e)}",
        ) from e


# ---- FEAT-027: Character Consistency Check ----


class ConsistencyCheckResponse(BaseModel):
    """Response from consistency check."""

    character_id: str
    overall_score: float
    tier: str
    frame_scores: List[float]
    suggestions: List[str]


@router.post(
    "/{character_id}/check-consistency",
    response_model=ConsistencyCheckResponse,
)
async def check_character_consistency(
    character_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    video_path: Optional[str] = None,
) -> ConsistencyCheckResponse:
    """Check character visual consistency across generated shots.

    Compares the character's reference images with frames extracted
    from generated video to verify face/appearance consistency.
    """
    service = CharacterService(session)
    character = await service.get_character(character_id, include_references=True)

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    try:
        result = await service.check_character_consistency(
            character=character,
            video_path=video_path,
        )

        return ConsistencyCheckResponse(
            character_id=str(character_id),
            overall_score=result.get("overall_score", 0.0),
            tier=result.get("tier", "unknown"),
            frame_scores=result.get("frame_scores", []),
            suggestions=result.get("suggestions", []),
        )

    except Exception as e:
        logger.error(f"Consistency check failed for {character_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consistency check failed: {str(e)}",
        ) from e


# ---- FEAT-030: Face Similarity Comparison ----


class FaceSimilarityComparisonItem(BaseModel):
    """Similarity comparison for a single shot."""

    shot_id: str
    similarity_score: float
    is_same_person: bool
    thumbnail_url: Optional[str] = None


class FaceSimilarityResponse(BaseModel):
    """Face similarity comparison results for a character."""

    character_id: str
    character_name: str
    comparisons: List[FaceSimilarityComparisonItem]
    average_similarity: float


@router.post(
    "/{character_id}/face-similarity",
    response_model=FaceSimilarityResponse,
)
async def compare_face_similarity(
    character_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FaceSimilarityResponse:
    """Compare a character's face embedding against generated shots.

    Uses the FaceEmbeddingService to compute cosine similarity between
    the character's reference images and frames from generated shots.

    Args:
        character_id: Character UUID

    Returns:
        Per-shot similarity scores and overall average
    """
    service = CharacterService(session)
    character = await service.get_character(character_id, include_references=True)

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    try:
        from scenemachine.services.face_embedding import get_face_embedding_service

        face_service = get_face_embedding_service()

        # Get reference image paths
        ref_paths = []
        if hasattr(character, "reference_assets") and character.reference_assets:
            ref_paths = [a.file_path for a in character.reference_assets]

        if not ref_paths:
            return FaceSimilarityResponse(
                character_id=str(character_id),
                character_name=character.name,
                comparisons=[],
                average_similarity=0.0,
            )

        # Get generated shots for this character's scenes
        from sqlalchemy import select
        from scenemachine.models import Shot

        shot_stmt = select(Shot).where(
            Shot.state.in_(["generated", "approved", "completed"])
        ).limit(20)
        shot_result = await session.execute(shot_stmt)
        shots = shot_result.scalars().all()

        comparisons = []
        total_score = 0.0

        for shot in shots:
            output_path = getattr(shot, "output_path", None) or getattr(shot, "thumbnail_path", None)
            if not output_path:
                continue

            # Compute similarity between reference and shot frame
            try:
                similarity = await face_service.compute_similarity(
                    ref_paths[0], output_path
                )
                score = similarity if isinstance(similarity, float) else similarity.get("score", 0.0)
            except Exception:
                score = 0.0

            comparisons.append(FaceSimilarityComparisonItem(
                shot_id=str(shot.id),
                similarity_score=round(score, 3),
                is_same_person=score >= 0.7,
                thumbnail_url=getattr(shot, "thumbnail_path", None),
            ))
            total_score += score

        avg = total_score / len(comparisons) if comparisons else 0.0

        return FaceSimilarityResponse(
            character_id=str(character_id),
            character_name=character.name,
            comparisons=comparisons,
            average_similarity=round(avg, 3),
        )

    except ImportError:
        # FaceEmbeddingService not available
        return FaceSimilarityResponse(
            character_id=str(character_id),
            character_name=character.name,
            comparisons=[],
            average_similarity=0.0,
        )
    except Exception as e:
        logger.error(f"Face similarity comparison failed for {character_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face similarity comparison failed: {str(e)}",
        ) from e

