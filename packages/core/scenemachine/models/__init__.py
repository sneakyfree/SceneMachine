"""
SceneMachine Data Models

SQLAlchemy ORM models for the SceneMachine database.
"""

from scenemachine.models.asset import Asset, AssetStatus, AssetType
from scenemachine.models.auction import Auction, AuctionBid, AuctionStatus, BidStatus
from scenemachine.models.audio_asset import AudioAsset, AudioAssetType
from scenemachine.models.base import ArrayType, Base, JSONType, TimestampMixin, UUIDMixin
from scenemachine.models.booking import Booking, BookingMode, BookingStatus, PaymentStatus
from scenemachine.models.character import Character, CharacterGender, CharacterLockState
from scenemachine.models.export_history import ExportFormat, ExportHistory, ExportStatus
from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus, JobType
from scenemachine.models.lipsync_job import LipsyncJob, LipsyncJobStatus
from scenemachine.models.performance_take import PerformanceTake, TakeMode, TakeStatus

# ActCore models
from scenemachine.models.performer import (
    Performer,
    PerformerAvailability,
    PerformerType,
    PerformerVerification,
)
from scenemachine.models.performer_rating import PerformerRating
from scenemachine.models.project import Project, ProjectState
from scenemachine.models.scene import Scene, SceneState, SceneType, TimeOfDay
from scenemachine.models.screenplay import Screenplay, ScreenplayFormat
from scenemachine.models.settings import UserSettings
from scenemachine.models.share import ProjectComment, ProjectShare, SharePermission, ShareStatus
from scenemachine.models.shot import CameraMovement, Shot, ShotState, ShotType
from scenemachine.models.text_overlay import TextOverlay, TextOverlayType
from scenemachine.models.user import RefreshToken, User, UserRole

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "JSONType",
    "ArrayType",
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
    "JobType",
    "JobProvider",
    # Settings
    "UserSettings",
    # Share
    "ProjectShare",
    "ProjectComment",
    "SharePermission",
    "ShareStatus",
    # Export History
    "ExportHistory",
    "ExportStatus",
    "ExportFormat",
    # Audio Asset
    "AudioAsset",
    "AudioAssetType",
    # Text Overlay
    "TextOverlay",
    "TextOverlayType",
    # Lipsync Job
    "LipsyncJob",
    "LipsyncJobStatus",
    # ActCore - Performer
    "Performer",
    "PerformerType",
    "PerformerAvailability",
    "PerformerVerification",
    # ActCore - Takes
    "PerformanceTake",
    "TakeMode",
    "TakeStatus",
    # ActCore - Bookings
    "Booking",
    "BookingMode",
    "BookingStatus",
    "PaymentStatus",
    # ActCore - Auctions
    "Auction",
    "AuctionBid",
    "AuctionStatus",
    "BidStatus",
    # ActCore - Ratings
    "PerformerRating",
    # User & Auth
    "User",
    "RefreshToken",
    "UserRole",
]
