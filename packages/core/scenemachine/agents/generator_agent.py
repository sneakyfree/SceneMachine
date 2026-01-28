"""
Generator Agent - Video and audio generation.

Responsibilities:
- Queue and manage video generation jobs
- Generate TTS audio for dialogue
- Apply lip-sync to videos
- Handle provider routing and fallbacks
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from scenemachine.agents.base import (
    BaseAgent,
    AgentType,
    ActionContext,
    ActionResult,
    ActionStatus,
    EscalationReason,
)

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseAgent):
    """
    Agent responsible for video and audio generation.
    
    Autonomous actions:
    - generate_video: Generate video for a shot
    - generate_audio: Generate TTS audio for dialogue
    - apply_lipsync: Apply lip-sync to video
    - retry_failed: Retry failed generations
    
    Requires approval:
    - spend_budget: When generation cost exceeds threshold
    - use_premium_model: When using expensive cloud models
    """
    
    COST_THRESHOLD_USD = 10.0  # Require approval above this
    
    @property
    def agent_type(self) -> AgentType:
        return AgentType.GENERATOR
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "generate_video",
            "generate_audio",
            "apply_lipsync",
            "retry_failed",
            "spend_budget",
            "use_premium_model",
        ]
    
    @property
    def requires_approval(self) -> List[str]:
        return ["spend_budget", "use_premium_model"]
    
    async def _execute_action(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """Execute generation actions."""
        if action_name == "generate_video":
            return await self._generate_video(context, **kwargs)
        elif action_name == "generate_audio":
            return await self._generate_audio(context, **kwargs)
        elif action_name == "apply_lipsync":
            return await self._apply_lipsync(context, **kwargs)
        elif action_name == "retry_failed":
            return await self._retry_failed(context, **kwargs)
        else:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"Unknown action: {action_name}",
            )
    
    async def _generate_video(
        self,
        context: ActionContext,
        shot_id: UUID,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: float = 3.0,
        use_mock: bool = True,
    ) -> ActionResult:
        """Generate video for a shot."""
        try:
            from scenemachine.services.generation import (
                MockGenerationProvider,
                GenerationRequest,
            )
            
            provider = MockGenerationProvider()
            request = GenerationRequest(
                shot_id=shot_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration_seconds=duration_seconds,
            )
            
            result = await provider.generate(request)
            
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED if result.success else ActionStatus.FAILED,
                success=result.success,
                output={
                    "video_path": result.output_path,
                    "thumbnail_path": result.thumbnail_path,
                    "duration": result.duration_seconds,
                },
                cost_usd=result.cost_usd or 0.0,
                confidence=0.85 if result.success else 0.0,
            )
        except Exception as e:
            logger.exception(f"Video generation failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )
    
    async def _generate_audio(
        self,
        context: ActionContext,
        text: str,
        voice_id: str,
    ) -> ActionResult:
        """Generate TTS audio for dialogue."""
        try:
            from scenemachine.services.audio import MockTTSProvider, TTSRequest
            
            provider = MockTTSProvider()
            request = TTSRequest(text=text, voice_id=voice_id)
            
            result = await provider.generate(request)
            
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED if result.success else ActionStatus.FAILED,
                success=result.success,
                output={
                    "audio_path": result.audio_path,
                    "duration": result.duration_seconds,
                },
                cost_usd=result.cost_usd or 0.0,
                confidence=0.9 if result.success else 0.0,
            )
        except Exception as e:
            logger.exception(f"Audio generation failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )
    
    async def _apply_lipsync(
        self,
        context: ActionContext,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> ActionResult:
        """Apply lip-sync to a video."""
        try:
            from scenemachine.services.lipsync import MockLipSyncProvider
            
            provider = MockLipSyncProvider()
            
            # First analyze the audio
            analysis = await provider.analyze_audio(audio_path)
            if not analysis.success:
                return ActionResult(
                    action_id=context.session_id,
                    status=ActionStatus.FAILED,
                    success=False,
                    error_message=analysis.error_message,
                )
            
            # Then apply to video
            result = await provider.apply_to_video(
                video_path=video_path,
                lip_sync_data=analysis.lip_sync_data,
                output_path=output_path,
            )
            
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED if result.success else ActionStatus.FAILED,
                success=result.success,
                output={
                    "output_path": result.output_video_path,
                    "phoneme_count": len(analysis.lip_sync_data.phonemes),
                },
                confidence=0.8 if result.success else 0.0,
            )
        except Exception as e:
            logger.exception(f"Lip-sync failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )
    
    async def _retry_failed(
        self,
        context: ActionContext,
        job_id: UUID,
        max_retries: int = 3,
    ) -> ActionResult:
        """Retry a failed generation job."""
        # This would fetch the job from the queue and retry
        # For now, return a mock success
        
        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "job_id": str(job_id),
                "retry_count": 1,
                "status": "queued",
            },
            confidence=0.7,
        )
