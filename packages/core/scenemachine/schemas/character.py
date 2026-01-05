"""Pydantic schemas for Character API endpoints."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from scenemachine.models.character import CharacterGender, CharacterLockState

from .base import BaseSchema, TimestampSchema


class PhysicalDescription(BaseSchema):
    """Structured physical description for character generation."""

    hair_color: Optional[str] = None
    hair_style: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    height: Optional[str] = None
    build: Optional[str] = None
    distinguishing_features: List[str] = Field(default_factory=list)
    clothing_style: Optional[str] = None
    additional_notes: Optional[str] = None


class ConsentStatus(BaseSchema):
    """Consent and ethics tracking for character likeness."""

    is_real_person: bool = False
    consent_obtained: Optional[bool] = None
    consent_document_path: Optional[str] = None
    likeness_rights_confirmed: bool = False
    notes: Optional[str] = None


class CharacterCreate(BaseSchema):
    """Schema for creating a character."""

    name: str = Field(..., min_length=1, max_length=255)
    screenplay_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    age_range_min: Optional[int] = Field(None, ge=0, le=120)
    age_range_max: Optional[int] = Field(None, ge=0, le=120)
    gender: CharacterGender = CharacterGender.UNSPECIFIED
    physical_description: Optional[PhysicalDescription] = None
    personality_traits: List[str] = Field(default_factory=list)
    voice_description: Optional[str] = None
    is_protagonist: bool = False
    consent_status: Optional[ConsentStatus] = None

    @field_validator("age_range_max")
    @classmethod
    def validate_age_range(cls, v: Optional[int], info: Any) -> Optional[int]:
        """Ensure age_range_max >= age_range_min."""
        if v is not None:
            age_min = info.data.get("age_range_min")
            if age_min is not None and v < age_min:
                raise ValueError("age_range_max must be >= age_range_min")
        return v


# Import Any for validator
from typing import Any


class CharacterUpdate(BaseSchema):
    """Schema for updating a character."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    age_range_min: Optional[int] = Field(None, ge=0, le=120)
    age_range_max: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[CharacterGender] = None
    physical_description: Optional[PhysicalDescription] = None
    personality_traits: Optional[List[str]] = None
    voice_description: Optional[str] = None
    is_protagonist: Optional[bool] = None
    consent_status: Optional[ConsentStatus] = None


class CharacterSummary(TimestampSchema):
    """Brief character information for lists."""

    id: UUID
    project_id: UUID
    name: str
    screenplay_name: str
    lock_state: CharacterLockState
    is_locked: bool
    scene_count: int
    dialogue_count: int
    is_protagonist: bool
    reference_asset_count: int = 0


class CharacterDetail(TimestampSchema):
    """Full character information."""

    id: UUID
    project_id: UUID
    name: str
    screenplay_name: str
    description: Optional[str]
    age_range_min: Optional[int]
    age_range_max: Optional[int]
    age_range_display: Optional[str]
    gender: CharacterGender
    physical_description: Optional[PhysicalDescription]
    personality_traits: Optional[List[str]]
    voice_description: Optional[str]
    lock_state: CharacterLockState
    is_locked: bool
    locked_likeness: Optional[dict]
    scene_count: int
    dialogue_count: int
    is_protagonist: bool
    consent_status: Optional[ConsentStatus]
    reference_asset_count: int = 0


class CharacterLockRequest(BaseSchema):
    """Request to lock a character's likeness."""

    primary_reference_asset_id: UUID
    secondary_reference_asset_ids: List[UUID] = Field(default_factory=list)
    generation_prompt: str = Field(..., min_length=10, max_length=2000)
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    confirm_consent: bool = Field(
        ..., description="User confirms they have rights to use this likeness"
    )

    @field_validator("confirm_consent")
    @classmethod
    def must_confirm_consent(cls, v: bool) -> bool:
        """Ensure consent is confirmed."""
        if not v:
            raise ValueError("You must confirm you have rights to use this likeness")
        return v


class CharacterGenerateOptionsRequest(BaseSchema):
    """Request to generate likeness options for review."""

    count: int = Field(4, ge=1, le=8, description="Number of options to generate")
    style_preset: Optional[str] = None
    additional_prompt: Optional[str] = Field(None, max_length=500)


class CharacterGenerateOptionsResponse(BaseSchema):
    """Response with generated likeness options."""

    character_id: UUID
    generated_asset_ids: List[UUID]
    generation_prompt_used: str
