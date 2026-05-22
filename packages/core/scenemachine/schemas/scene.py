"""Pydantic schemas for Scene API endpoints."""

from typing import Any
from uuid import UUID

from pydantic import Field

from scenemachine.models.scene import SceneState, SceneType, TimeOfDay

from .base import BaseSchema, TimestampSchema


class SceneAnalysis(BaseSchema):
    """AI-generated scene analysis."""

    summary: str
    mood: str
    emotional_arc: list[str] = Field(default_factory=list)
    key_moments: list[dict[str, Any]] = Field(default_factory=list)
    visual_style_suggestions: list[str] = Field(default_factory=list)
    pacing: str | None = None
    importance: int = Field(ge=1, le=10)


class ShotBreakdownSummary(BaseSchema):
    """Summary of shot breakdown for a scene."""

    approach: str
    shot_count: int
    coverage_style: str
    notes: str | None = None


class SceneSummary(TimestampSchema):
    """Brief scene information for lists."""

    id: UUID
    project_id: UUID
    scene_number: str
    sequence_number: int
    heading: str
    scene_type: SceneType
    location: str
    time_of_day: TimeOfDay
    state: SceneState
    shot_count: int
    shot_breakdown_approved: bool
    estimated_duration_seconds: float | None


class SceneDetail(TimestampSchema):
    """Full scene information."""

    id: UUID
    project_id: UUID
    scene_number: str
    sequence_number: int
    heading: str
    scene_type: SceneType
    location: str
    time_of_day: TimeOfDay
    raw_content: str
    action_lines: list[str]
    character_ids: list[UUID]
    analysis: SceneAnalysis | None
    shot_breakdown: ShotBreakdownSummary | None
    shot_breakdown_approved: bool
    generation_settings: dict[str, Any] | None
    estimated_duration_seconds: float | None
    actual_duration_seconds: float | None
    state: SceneState
    shot_count: int
    completed_shot_count: int
    generation_progress: float


class SceneUpdate(BaseSchema):
    """Schema for updating scene metadata."""

    generation_settings: dict[str, Any] | None = None
    estimated_duration_seconds: float | None = Field(None, ge=0)


class ShotBreakdownRequest(BaseSchema):
    """Request to generate shot breakdown for a scene."""

    style_preference: str | None = Field(
        None, description="Preferred coverage style (e.g., 'classical', 'modern', 'minimal')"
    )
    target_shot_count: int | None = Field(None, ge=1, le=50, description="Target number of shots")
    focus_characters: list[UUID] | None = Field(
        None, description="Character IDs to prioritize in coverage"
    )


class ShotBreakdownApproval(BaseSchema):
    """Request to approve shot breakdown."""

    notes: str | None = Field(None, max_length=1000)


class SceneReorderRequest(BaseSchema):
    """Request to reorder scenes."""

    scene_ids: list[UUID] = Field(..., min_length=1)
