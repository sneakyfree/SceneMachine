"""Pydantic schemas for Project API endpoints."""

from typing import Any
from uuid import UUID

from pydantic import Field

from scenemachine.models.project import ProjectState

from .base import BaseSchema, TimestampSchema


class ProjectCreate(BaseSchema):
    """Schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Project description")
    settings: dict[str, Any] | None = Field(
        default_factory=dict, description="Initial project settings"
    )


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    settings: dict[str, Any] | None = None


class ProjectSummary(TimestampSchema):
    """Brief project information for lists."""

    id: UUID
    name: str
    description: str | None
    state: ProjectState
    screenplay_title: str | None = None
    character_count: int = 0
    scene_count: int = 0
    locked_character_count: int = 0
    approved_scene_count: int = 0


class ScreenplaySummary(BaseSchema):
    """Brief screenplay information for project detail."""

    id: UUID
    title: str | None
    original_filename: str
    is_parsed: bool
    movie_plan_approved: bool
    page_count: int | None


class CharacterSummaryBrief(BaseSchema):
    """Brief character information for project detail."""

    id: UUID
    name: str
    screenplay_name: str
    is_locked: bool
    is_protagonist: bool


class SceneSummaryBrief(BaseSchema):
    """Brief scene information for project detail."""

    id: UUID
    scene_number: str
    heading: str
    shot_breakdown_approved: bool


class ProjectDetail(TimestampSchema):
    """Full project information with relationships."""

    id: UUID
    name: str
    description: str | None
    state: ProjectState
    settings: dict[str, Any]
    can_advance: bool

    # Nested summaries
    screenplay: ScreenplaySummary | None = None
    characters: list[CharacterSummaryBrief] = []
    scenes: list[SceneSummaryBrief] = []

    # Counts
    character_count: int = 0
    scene_count: int = 0
    locked_character_count: int = 0
    approved_scene_count: int = 0


class ProjectStateTransition(BaseSchema):
    """Request to transition project state."""

    target_state: ProjectState
    force: bool = Field(
        False, description="Skip validation checks (use with caution)"
    )


class ProjectStateResponse(BaseSchema):
    """Response after state transition."""

    id: UUID
    previous_state: ProjectState
    current_state: ProjectState
    can_advance: bool
