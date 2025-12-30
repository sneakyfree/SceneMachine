"""SQLAlchemy data models for SceneMachine.

This module exports all database models and their associated enums.
"""

from scenemachine.models.asset import Asset, AssetStatus, AssetType
from scenemachine.models.base import Base, TimestampMixin, UUIDMixin
from scenemachine.models.character import Character, CharacterGender, CharacterLockState
from scenemachine.models.export_history import (
    ExportHistory,
    ExportFormat,
    ExportQuality,
    ExportStatus,
)
from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus
from scenemachine.models.project import Project, ProjectState
from scenemachine.models.scene import Scene, SceneState, SceneType, TimeOfDay
from scenemachine.models.screenplay import Screenplay, ScreenplayFormat
from scenemachine.models.settings import LLMProvider, ThemeMode, UserSettings, VideoProvider
from scenemachine.models.share import ProjectComment, ProjectShare, SharePermission, ShareStatus
from scenemachine.models.shot import CameraMovement, Shot, ShotState, ShotType

__all__ = [
    # Base classes
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # Project
    "Project",
    "ProjectState",
    # Screenplay
    "Screenplay",
    "ScreenplayFormat",
    # Character
    "Character",
    "CharacterGender",
    "CharacterLockState",
    # Scene
    "Scene",
    "SceneType",
    "TimeOfDay",
    "SceneState",
    # Shot
    "Shot",
    "ShotType",
    "CameraMovement",
    "ShotState",
    # Asset
    "Asset",
    "AssetType",
    "AssetStatus",
    # GenerationJob
    "GenerationJob",
    "JobStatus",
    "JobProvider",
    # ExportHistory
    "ExportHistory",
    "ExportFormat",
    "ExportQuality",
    "ExportStatus",
    # Settings
    "UserSettings",
    "LLMProvider",
    "VideoProvider",
    "ThemeMode",
    # Share
    "ProjectShare",
    "ProjectComment",
    "SharePermission",
    "ShareStatus",
]
