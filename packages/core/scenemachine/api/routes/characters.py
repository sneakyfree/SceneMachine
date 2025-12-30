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
