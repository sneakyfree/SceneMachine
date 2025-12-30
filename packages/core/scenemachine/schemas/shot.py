"""Pydantic schemas for Shot API endpoints."""

from typing import Any, List, Optional
from uuid import UUID

from pydantic import Field

from scenemachine.models.shot import CameraMovement, ShotState, ShotType

from .base import BaseSchema, TimestampSchema


class ShotCreate(BaseSchema):
    """Schema for creating a shot (usually AI-generated)."""

    scene_id: UUID
    shot_number: str = Field(..., min_length=1, max_length=20)
    sequence_number: int = Field(..., ge=0)
    shot_type: ShotType
    camera_movement: CameraMovement = CameraMovement.STATIC
    description: str = Field(..., min_length=1)
    dialogue: Optional[str] = None
    action: Optional[str] = None
    character_ids: List[UUID] = Field(default_factory=list)
    composition_notes: Optional[str] = None
    lighting_notes: Optional[str] = None
    duration_seconds: float = Field(3.0, ge=0.5, le=60.0)


class ShotUpdate(BaseSchema):
    """Schema for updating a shot."""

    shot_type: Optional[ShotType] = None
    camera_movement: Optional[CameraMovement] = None
    description: Optional[str] = Field(None, min_length=1)
    dialogue: Optional[str] = None
    action: Optional[str] = None
    character_ids: Optional[List[UUID]] = None
    composition_notes: Optional[str] = None
    lighting_notes: Optional[str] = None
    generation_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    duration_seconds: Optional[float] = Field(None, ge=0.5, le=60.0)
    user_notes: Optional[str] = None


class ShotSummary(TimestampSchema):
    """Brief shot information for lists."""

    id: UUID
    scene_id: UUID
    shot_number: str
    sequence_number: int
    shot_type: ShotType
    camera_movement: CameraMovement
    description: str
    duration_seconds: float
    state: ShotState
    has_output: bool = False


class ShotDetail(TimestampSchema):
    """Full shot information."""

    id: UUID
    scene_id: UUID
    shot_number: str
    sequence_number: int
    shot_type: ShotType
    camera_movement: CameraMovement
    description: str
    dialogue: Optional[str]
    action: Optional[str]
    character_ids: List[UUID]
    composition_notes: Optional[str]
    lighting_notes: Optional[str]
    generation_prompt: Optional[str]
    negative_prompt: Optional[str]
    duration_seconds: float
    state: ShotState
    output_video_path: Optional[str]
    output_thumbnail_path: Optional[str]
    generation_metadata: Optional[dict[str, Any]]
    user_notes: Optional[str]
    rating: Optional[int]
    is_generated: bool
    is_approved: bool
    needs_regeneration: bool
    attempt_count: int


class ShotApproval(BaseSchema):
    """Request to approve a shot."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = Field(None, max_length=1000)


class ShotRejection(BaseSchema):
    """Request to reject a shot for regeneration."""

    reason: str = Field(..., min_length=1, max_length=1000)
    suggestions: Optional[str] = Field(None, max_length=1000)


class ShotReorderRequest(BaseSchema):
    """Request to reorder shots within a scene."""

    shot_ids: List[UUID] = Field(..., min_length=1)
