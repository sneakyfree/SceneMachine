"""Pydantic schemas for Scene API endpoints."""

from typing import Any, List, Optional
from uuid import UUID

from pydantic import Field

from scenemachine.models.scene import SceneState, SceneType, TimeOfDay

from .base import BaseSchema, TimestampSchema


class SceneAnalysis(BaseSchema):
    """AI-generated scene analysis."""

    summary: str
    mood: str
    emotional_arc: List[str] = Field(default_factory=list)
    key_moments: List[dict[str, Any]] = Field(default_factory=list)
    visual_style_suggestions: List[str] = Field(default_factory=list)
    pacing: Optional[str] = None
    importance: int = Field(ge=1, le=10)


class ShotBreakdownSummary(BaseSchema):
    """Summary of shot breakdown for a scene."""

    approach: str
    shot_count: int
    coverage_style: str
    notes: Optional[str] = None


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
    estimated_duration_seconds: Optional[float]


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
    action_lines: List[str]
    character_ids: List[UUID]
    analysis: Optional[SceneAnalysis]
    shot_breakdown: Optional[ShotBreakdownSummary]
    shot_breakdown_approved: bool
    generation_settings: Optional[dict[str, Any]]
    estimated_duration_seconds: Optional[float]
    actual_duration_seconds: Optional[float]
    state: SceneState
    shot_count: int
    completed_shot_count: int
    generation_progress: float


class SceneUpdate(BaseSchema):
    """Schema for updating scene metadata."""

    generation_settings: Optional[dict[str, Any]] = None
    estimated_duration_seconds: Optional[float] = Field(None, ge=0)


class ShotBreakdownRequest(BaseSchema):
    """Request to generate shot breakdown for a scene."""

    style_preference: Optional[str] = Field(
        None, description="Preferred coverage style (e.g., 'classical', 'modern', 'minimal')"
    )
    target_shot_count: Optional[int] = Field(
        None, ge=1, le=50, description="Target number of shots"
    )
    focus_characters: Optional[List[UUID]] = Field(
        None, description="Character IDs to prioritize in coverage"
    )


class ShotBreakdownApproval(BaseSchema):
    """Request to approve shot breakdown."""

    notes: Optional[str] = Field(None, max_length=1000)


class SceneReorderRequest(BaseSchema):
    """Request to reorder scenes."""

    scene_ids: List[UUID] = Field(..., min_length=1)
