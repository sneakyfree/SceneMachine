"""Pydantic schemas for Shot API endpoints."""

from typing import Any
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
    dialogue: str | None = None
    action: str | None = None
    character_ids: list[UUID] = Field(default_factory=list)
    composition_notes: str | None = None
    lighting_notes: str | None = None
    duration_seconds: float = Field(3.0, ge=0.5, le=60.0)


class ShotUpdate(BaseSchema):
    """Schema for updating a shot."""

    shot_type: ShotType | None = None
    camera_movement: CameraMovement | None = None
    description: str | None = Field(None, min_length=1)
    dialogue: str | None = None
    action: str | None = None
    character_ids: list[UUID] | None = None
    composition_notes: str | None = None
    lighting_notes: str | None = None
    generation_prompt: str | None = None
    negative_prompt: str | None = None
    duration_seconds: float | None = Field(None, ge=0.5, le=60.0)
    user_notes: str | None = None


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
    dialogue: str | None
    action: str | None
    character_ids: list[UUID]
    composition_notes: str | None
    lighting_notes: str | None
    generation_prompt: str | None
    negative_prompt: str | None
    duration_seconds: float
    state: ShotState
    output_video_path: str | None
    output_thumbnail_path: str | None
    generation_metadata: dict[str, Any] | None
    user_notes: str | None
    rating: int | None
    is_generated: bool
    is_approved: bool
    needs_regeneration: bool
    attempt_count: int


class ShotApproval(BaseSchema):
    """Request to approve a shot."""

    rating: int | None = Field(None, ge=1, le=5)
    notes: str | None = Field(None, max_length=1000)


class ShotRejection(BaseSchema):
    """Request to reject a shot for regeneration."""

    reason: str = Field(..., min_length=1, max_length=1000)
    suggestions: str | None = Field(None, max_length=1000)


class ShotReorderRequest(BaseSchema):
    """Request to reorder shots within a scene."""

    shot_ids: list[UUID] = Field(..., min_length=1)
