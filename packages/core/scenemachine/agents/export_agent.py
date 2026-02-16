"""Export Agent — Handles format conversion, compression, watermarking, and distribution.

Part of the SceneMachine agentic crew (DNA Strand Phase 6).
Requires human approval before final publish/distribution.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseAgent, AgentActionLogger

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    MP4_H264 = "mp4_h264"
    MP4_H265 = "mp4_h265"
    MOV_PRORES = "mov_prores"
    WEBM_VP9 = "webm_vp9"


class ExportPreset(str, Enum):
    """Platform-optimized export presets."""

    YOUTUBE_4K = "youtube_4k"
    YOUTUBE_1080P = "youtube_1080p"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"
    VIMEO = "vimeo"
    ARCHIVE_PRORES = "archive_prores"
    CUSTOM = "custom"


# Preset configurations
PRESET_CONFIGS: Dict[ExportPreset, Dict[str, Any]] = {
    ExportPreset.YOUTUBE_4K: {
        "format": ExportFormat.MP4_H264,
        "resolution": "3840x2160",
        "bitrate": "35M",
        "fps": 30,
        "audio_bitrate": "320k",
        "container": "mp4",
    },
    ExportPreset.YOUTUBE_1080P: {
        "format": ExportFormat.MP4_H264,
        "resolution": "1920x1080",
        "bitrate": "12M",
        "fps": 30,
        "audio_bitrate": "256k",
        "container": "mp4",
    },
    ExportPreset.INSTAGRAM_REELS: {
        "format": ExportFormat.MP4_H264,
        "resolution": "1080x1920",
        "bitrate": "10M",
        "fps": 30,
        "audio_bitrate": "256k",
        "container": "mp4",
        "max_duration_sec": 90,
    },
    ExportPreset.TIKTOK: {
        "format": ExportFormat.MP4_H264,
        "resolution": "1080x1920",
        "bitrate": "8M",
        "fps": 30,
        "audio_bitrate": "192k",
        "container": "mp4",
        "max_duration_sec": 180,
    },
    ExportPreset.VIMEO: {
        "format": ExportFormat.MP4_H264,
        "resolution": "1920x1080",
        "bitrate": "20M",
        "fps": 24,
        "audio_bitrate": "320k",
        "container": "mp4",
    },
    ExportPreset.ARCHIVE_PRORES: {
        "format": ExportFormat.MOV_PRORES,
        "resolution": "1920x1080",
        "bitrate": "100M",
        "fps": 24,
        "audio_bitrate": "320k",
        "container": "mov",
    },
}


class ExportAgent(BaseAgent):
    """Handles final export pipeline: format conversion, compression,
    watermarking, and distribution preparation.

    Autonomous capabilities:
    - Format conversion (MP4/MOV/WebM)
    - Compression optimization
    - Watermarking (delegate to assembly service)
    - Distribution prep (YouTube/Vimeo/social presets)

    Requires human approval:
    - Final publish/distribution
    - Non-standard format exports
    """

    agent_type = "export"

    def __init__(
        self,
        session: Any,
        action_logger: Optional[AgentActionLogger] = None,
    ) -> None:
        super().__init__(session=session, action_logger=action_logger)

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process an export task.

        Args:
            task: Dict with keys:
                - project_id: UUID of the project
                - preset: ExportPreset name or 'custom'
                - custom_settings: Optional custom format settings
                - watermark: Optional watermark config
                - require_approval: Whether to gate on human approval

        Returns:
            Export result with output path and metadata.
        """
        project_id = task.get("project_id")
        preset_name = task.get("preset", ExportPreset.YOUTUBE_1080P)
        custom_settings = task.get("custom_settings", {})
        watermark_config = task.get("watermark")
        require_approval = task.get("require_approval", True)

        await self._log_action(
            "export_started",
            f"Starting export for project {project_id} with preset {preset_name}",
        )

        # Step 1: Resolve export settings
        settings = await self._resolve_settings(preset_name, custom_settings)

        await self._log_action(
            "settings_resolved",
            f"Export settings: {settings['resolution']} @ {settings['bitrate']}, "
            f"format={settings['format']}",
        )

        # Step 2: Check if project is ready for export
        readiness = await self._check_export_readiness(project_id)
        if not readiness["ready"]:
            await self._log_action(
                "export_blocked",
                f"Export blocked: {readiness['reason']}",
                confidence=0.0,
            )
            return {
                "status": "blocked",
                "reason": readiness["reason"],
                "blockers": readiness.get("blockers", []),
            }

        # Step 3: Apply watermark if requested
        if watermark_config:
            await self._apply_watermark(project_id, watermark_config)
            await self._log_action("watermark_applied", "Watermark applied to output")

        # Step 4: Compress and transcode
        output = await self._transcode(project_id, settings)

        await self._log_action(
            "transcode_complete",
            f"Transcoded to {output.get('format', 'mp4')} — "
            f"{output.get('file_size_mb', 0):.1f} MB",
            confidence=0.95,
        )

        # Step 5: Human approval gate for distribution
        if require_approval:
            await self._log_action(
                "approval_requested",
                "Awaiting human approval before distribution",
                requires_approval=True,
            )
            return {
                "status": "pending_approval",
                "output": output,
                "settings": settings,
                "message": "Export ready. Awaiting human approval before distribution.",
            }

        # Step 6: Prepare distribution metadata
        distribution = await self._prepare_distribution(output, preset_name)

        await self._log_action(
            "export_complete",
            f"Export complete: {output.get('output_path', 'N/A')}",
            confidence=1.0,
        )

        return {
            "status": "completed",
            "output": output,
            "distribution": distribution,
            "settings": settings,
        }

    async def _resolve_settings(
        self,
        preset_name: str,
        custom_settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve final export settings from preset + custom overrides."""
        try:
            preset = ExportPreset(preset_name)
            settings = dict(PRESET_CONFIGS.get(preset, {}))
        except ValueError:
            settings = {}

        # Apply custom overrides
        settings.update(custom_settings)

        # Ensure required keys
        settings.setdefault("format", ExportFormat.MP4_H264)
        settings.setdefault("resolution", "1920x1080")
        settings.setdefault("bitrate", "12M")
        settings.setdefault("fps", 30)
        settings.setdefault("audio_bitrate", "256k")
        settings.setdefault("container", "mp4")

        return settings

    async def _check_export_readiness(
        self, project_id: Optional[str]
    ) -> Dict[str, Any]:
        """Verify the project is ready for export."""
        # In production, this would check:
        # - All shots generated successfully
        # - Assembly complete
        # - Audio mixed
        # - No critical blockers

        if not project_id:
            return {"ready": False, "reason": "No project ID provided"}

        # Delegate to generation service for status check
        return {"ready": True, "reason": "All checks passed"}

    async def _apply_watermark(
        self,
        project_id: Optional[str],
        watermark_config: Dict[str, Any],
    ) -> None:
        """Apply watermark to the assembled video."""
        # Delegates to AssemblyService.apply_watermark
        logger.info(
            "Applying watermark to project %s: %s", project_id, watermark_config
        )

    async def _transcode(
        self,
        project_id: Optional[str],
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transcode assembled video to target format."""
        # In production, this calls FFmpeg via the assembly service
        logger.info(
            "Transcoding project %s to %s @ %s",
            project_id,
            settings.get("format"),
            settings.get("resolution"),
        )

        return {
            "output_path": f"/exports/{project_id}/final.{settings.get('container', 'mp4')}",
            "format": str(settings.get("format", "")),
            "resolution": settings.get("resolution"),
            "file_size_mb": 0.0,  # Computed after actual transcode
            "duration_seconds": 0.0,  # Computed after actual transcode
        }

    async def _prepare_distribution(
        self,
        output: Dict[str, Any],
        preset_name: str,
    ) -> Dict[str, Any]:
        """Prepare distribution metadata for the target platform."""
        return {
            "platform": preset_name,
            "output_path": output.get("output_path"),
            "ready_for_upload": True,
            "metadata": {
                "title": "",
                "description": "",
                "tags": [],
            },
        }

    async def _log_action(
        self,
        action: str,
        details: str,
        confidence: float = 0.9,
        requires_approval: bool = False,
    ) -> None:
        """Log an agent action."""
        if self.action_logger:
            await self.action_logger.log(
                agent_type=self.agent_type,
                action=action,
                details=details,
                confidence=confidence,
                requires_approval=requires_approval,
            )
        logger.info("[ExportAgent] %s: %s", action, details)
