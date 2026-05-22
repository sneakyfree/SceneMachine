"""Screenplay API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from scenemachine.models.screenplay import ScreenplayFormat


class ScreenplayCreate(BaseModel):
    """Schema for creating a screenplay (via file upload)."""

    project_id: UUID


class ScreenplayResponse(BaseModel):
    """Basic screenplay response."""

    id: UUID
    project_id: UUID
    original_filename: str
    original_format: ScreenplayFormat
    is_parsed: bool
    parse_errors: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScreenplaySummary(BaseModel):
    """Summary screenplay info for lists."""

    id: UUID
    project_id: UUID
    original_filename: str
    original_format: ScreenplayFormat
    is_parsed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CharacterSummary(BaseModel):
    """Character summary in screenplay context."""

    id: str
    name: str
    dialogue_count: int
    scene_count: int


class SceneSummary(BaseModel):
    """Scene summary in screenplay context."""

    id: str
    scene_number: str
    sequence_number: int
    scene_type: str
    location: str
    time_of_day: str


class ScreenplayDetail(BaseModel):
    """Detailed screenplay with parsed content."""

    id: UUID
    project_id: UUID
    original_filename: str
    original_format: ScreenplayFormat
    is_parsed: bool
    parse_errors: list[str] | None = None
    parsed_content: dict[str, Any] | None = None
    character_count: int = 0
    scene_count: int = 0
    characters: list[dict[str, Any]] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParseResult(BaseModel):
    """Result of screenplay parsing."""

    success: bool
    screenplay_id: UUID
    character_count: int
    scene_count: int
    element_count: int
    errors: list[str] | None = None
    warnings: list[str] | None = None
