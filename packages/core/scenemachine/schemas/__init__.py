"""Pydantic schemas for API request/response validation.

This module exports all schemas used by the FastAPI application.
"""

from scenemachine.schemas.base import (
    BaseSchema,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    ReadinessResponse,
    SuccessResponse,
    TimestampSchema,
)
from scenemachine.schemas.character import (
    CharacterCreate,
    CharacterDetail,
    CharacterGenerateOptionsRequest,
    CharacterGenerateOptionsResponse,
    CharacterLockRequest,
    CharacterSummary,
    CharacterUpdate,
    ConsentStatus,
    PhysicalDescription,
)
from scenemachine.schemas.generation import (
    CancelGenerationRequest,
    CancelGenerationResponse,
    CostEstimateRequest,
    CostEstimateResponse,
    GenerationJobDetail,
    GenerationSettings,
    GenerationStartRequest,
    GenerationStartResponse,
    GenerationStatusResponse,
    JobProgress,
    RegenerateShotRequest,
)
from scenemachine.schemas.project import (
    CharacterSummaryBrief,
    ProjectCreate,
    ProjectDetail,
    ProjectStateResponse,
    ProjectStateTransition,
    ProjectSummary,
    ProjectUpdate,
    SceneSummaryBrief,
    ScreenplaySummary,
)
from scenemachine.schemas.scene import (
    SceneAnalysis,
    SceneDetail,
    SceneReorderRequest,
    SceneSummary,
    SceneUpdate,
    ShotBreakdownApproval,
    ShotBreakdownRequest,
    ShotBreakdownSummary,
)
from scenemachine.schemas.shot import (
    ShotApproval,
    ShotCreate,
    ShotDetail,
    ShotRejection,
    ShotReorderRequest,
    ShotSummary,
    ShotUpdate,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampSchema",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",
    "HealthResponse",
    "ReadinessResponse",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectSummary",
    "ProjectDetail",
    "ProjectStateTransition",
    "ProjectStateResponse",
    "ScreenplaySummary",
    "CharacterSummaryBrief",
    "SceneSummaryBrief",
    # Character
    "PhysicalDescription",
    "ConsentStatus",
    "CharacterCreate",
    "CharacterUpdate",
    "CharacterSummary",
    "CharacterDetail",
    "CharacterLockRequest",
    "CharacterGenerateOptionsRequest",
    "CharacterGenerateOptionsResponse",
    # Scene
    "SceneAnalysis",
    "ShotBreakdownSummary",
    "SceneSummary",
    "SceneDetail",
    "SceneUpdate",
    "ShotBreakdownRequest",
    "ShotBreakdownApproval",
    "SceneReorderRequest",
    # Shot
    "ShotCreate",
    "ShotUpdate",
    "ShotSummary",
    "ShotDetail",
    "ShotApproval",
    "ShotRejection",
    "ShotReorderRequest",
    # Generation
    "GenerationSettings",
    "GenerationStartRequest",
    "GenerationStartResponse",
    "JobProgress",
    "GenerationStatusResponse",
    "RegenerateShotRequest",
    "GenerationJobDetail",
    "CancelGenerationRequest",
    "CancelGenerationResponse",
    "CostEstimateRequest",
    "CostEstimateResponse",
]
