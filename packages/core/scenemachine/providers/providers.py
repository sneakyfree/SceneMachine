"""Provider configuration module.

Centralizes configuration for all external providers:
- LLM providers (Anthropic, OpenAI)
- Video providers (Fal, Replicate, ComfyUI, RunPod)
- Image providers (Flux via Fal)
- Voice providers (Kokoro built-in, ElevenLabs)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Provider category types."""
    LLM = "llm"
    VIDEO = "video"
    IMAGE = "image"
    VOICE = "voice"
    LIPSYNC = "lipsync"


class ProviderStatus(str, Enum):
    """Provider availability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    name: str
    provider_type: ProviderType
    api_key_env: str
    is_enabled: bool = True
    default_model: Optional[str] = None
    base_url: Optional[str] = None
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment."""
        return os.environ.get(self.api_key_env)
    
    @property
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return bool(self.api_key)
    
    @property
    def status(self) -> ProviderStatus:
        """Get provider status."""
        if not self.is_enabled:
            return ProviderStatus.UNAVAILABLE
        if not self.is_configured:
            return ProviderStatus.NOT_CONFIGURED
        return ProviderStatus.AVAILABLE


@dataclass
class ProvidersRegistry:
    """Registry of all available providers."""
    
    # LLM Providers
    LLM_PROVIDERS: List[ProviderConfig] = field(default_factory=lambda: [
        ProviderConfig(
            name="anthropic",
            provider_type=ProviderType.LLM,
            api_key_env="ANTHROPIC_API_KEY",
            default_model="claude-sonnet-4-20250514",
        ),
        ProviderConfig(
            name="openai",
            provider_type=ProviderType.LLM,
            api_key_env="OPENAI_API_KEY",
            default_model="gpt-4o",
        ),
    ])
    
    # Video Providers
    VIDEO_PROVIDERS: List[ProviderConfig] = field(default_factory=lambda: [
        ProviderConfig(
            name="fal",
            provider_type=ProviderType.VIDEO,
            api_key_env="FAL_KEY",
            default_model="fal-ai/cogvideox-5b",
            extra_config={
                "models": [
                    "fal-ai/cogvideox-5b",
                    "fal-ai/hunyuan-video",
                    "fal-ai/ltx-video",
                    "fal-ai/mochi-1",
                    "fal-ai/fast-svd-lcm",
                ]
            }
        ),
        ProviderConfig(
            name="replicate",
            provider_type=ProviderType.VIDEO,
            api_key_env="REPLICATE_API_TOKEN",
            default_model="minimax/video-01",
            extra_config={
                "models": [
                    "minimax/video-01",
                    "lumalabs/dream-machine",
                    "stability-ai/stable-video-diffusion",
                    "wavymulder/animatediff",
                ]
            }
        ),
        ProviderConfig(
            name="comfyui",
            provider_type=ProviderType.VIDEO,
            api_key_env="COMFYUI_URL",  # Not really a key, but URL
            default_model="wan2-t2v",
            base_url=os.environ.get("COMFYUI_URL", "http://localhost:8188"),
            extra_config={
                "models": [
                    "wan2-t2v",  # Wan 2.1 Text-to-Video
                    "animatediff-v3",
                    "animatediff-lightning",
                    "svd-xt",
                ]
            }
        ),
        ProviderConfig(
            name="runpod",
            provider_type=ProviderType.VIDEO,
            api_key_env="RUNPOD_API_KEY",
            extra_config={
                "endpoint_id_env": "RUNPOD_ENDPOINT_ID"
            }
        ),
    ])
    
    # Image Providers
    IMAGE_PROVIDERS: List[ProviderConfig] = field(default_factory=lambda: [
        ProviderConfig(
            name="flux_fal",
            provider_type=ProviderType.IMAGE,
            api_key_env="FAL_KEY",
            default_model="fal-ai/flux/schnell",
            extra_config={
                "models": [
                    "fal-ai/flux/schnell",
                    "fal-ai/flux/dev",
                    "fal-ai/flux/pro",
                ]
            }
        ),
        ProviderConfig(
            name="replicate_sdxl",
            provider_type=ProviderType.IMAGE,
            api_key_env="REPLICATE_API_TOKEN",
            default_model="stability-ai/sdxl",
        ),
    ])
    
    # Voice Providers
    VOICE_PROVIDERS: List[ProviderConfig] = field(default_factory=lambda: [
        ProviderConfig(
            name="kokoro",
            provider_type=ProviderType.VOICE,
            api_key_env="KOKORO_ENABLED",  # Not actually needed, always enabled
            is_enabled=True,
            extra_config={
                "voices_count": 20,
                "languages": ["en", "es"],
                "built_in": True,  # Mark as built-in
            }
        ),
        ProviderConfig(
            name="elevenlabs",
            provider_type=ProviderType.VOICE,
            api_key_env="ELEVENLABS_API_KEY",
            extra_config={
                "voice_cloning": True,
            }
        ),
    ])
    
    # LipSync Providers
    LIPSYNC_PROVIDERS: List[ProviderConfig] = field(default_factory=lambda: [
        ProviderConfig(
            name="latentsync",
            provider_type=ProviderType.LIPSYNC,
            api_key_env="REPLICATE_API_TOKEN",
        ),
        ProviderConfig(
            name="wav2lip",
            provider_type=ProviderType.LIPSYNC,
            api_key_env="WAV2LIP_MODEL_PATH",  # Local model path
        ),
    ])
    
    def get_configured_providers(self, provider_type: ProviderType) -> List[ProviderConfig]:
        """Get all configured providers of a type."""
        providers = self._get_providers_by_type(provider_type)
        return [p for p in providers if p.is_configured or p.name == "kokoro"]
    
    def get_best_available(self, provider_type: ProviderType) -> Optional[ProviderConfig]:
        """Get the first available provider of a type."""
        providers = self.get_configured_providers(provider_type)
        return providers[0] if providers else None
    
    def _get_providers_by_type(self, provider_type: ProviderType) -> List[ProviderConfig]:
        """Get provider list by type."""
        mapping = {
            ProviderType.LLM: self.LLM_PROVIDERS,
            ProviderType.VIDEO: self.VIDEO_PROVIDERS,
            ProviderType.IMAGE: self.IMAGE_PROVIDERS,
            ProviderType.VOICE: self.VOICE_PROVIDERS,
            ProviderType.LIPSYNC: self.LIPSYNC_PROVIDERS,
        }
        return mapping.get(provider_type, [])
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get configuration status for all providers."""
        report = {}
        
        for ptype in ProviderType:
            providers = self._get_providers_by_type(ptype)
            report[ptype.value] = {
                "configured": [p.name for p in providers if p.is_configured or p.name == "kokoro"],
                "available": [p.name for p in providers if p.status == ProviderStatus.AVAILABLE],
                "not_configured": [p.name for p in providers if p.status == ProviderStatus.NOT_CONFIGURED],
            }
        
        return report


# Singleton instance
_registry: Optional[ProvidersRegistry] = None


def get_providers_registry() -> ProvidersRegistry:
    """Get the providers registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProvidersRegistry()
    return _registry


def check_provider_status() -> Dict[str, Any]:
    """Check status of all providers and return report."""
    registry = get_providers_registry()
    report = registry.get_status_report()
    
    # Add summary
    total_configured = sum(len(v.get("configured", [])) for v in report.values())
    total_available = sum(len(v.get("available", [])) for v in report.values())
    
    report["summary"] = {
        "total_configured": total_configured,
        "total_available": total_available,
        "ready_for_generation": total_available > 0,
    }
    
    return report


def get_llm_config() -> Optional[ProviderConfig]:
    """Get the configured LLM provider."""
    registry = get_providers_registry()
    
    # Check environment for preferred provider
    preferred = os.environ.get("DEFAULT_LLM_PROVIDER", "anthropic")
    
    for provider in registry.LLM_PROVIDERS:
        if provider.name == preferred and provider.is_configured:
            return provider
    
    # Fall back to any configured provider
    return registry.get_best_available(ProviderType.LLM)


def get_video_config() -> Optional[ProviderConfig]:
    """Get the configured video provider."""
    registry = get_providers_registry()
    
    # Check environment for preferred provider
    preferred = os.environ.get("DEFAULT_VIDEO_MODEL", "local")
    
    if preferred == "local":
        for provider in registry.VIDEO_PROVIDERS:
            if provider.name == "comfyui":
                # Check if ComfyUI is running
                return provider
    
    # Check cloud providers
    for preferred_name in ["fal", "replicate", "runpod"]:
        for provider in registry.VIDEO_PROVIDERS:
            if provider.name == preferred_name and provider.is_configured:
                return provider
    
    return registry.get_best_available(ProviderType.VIDEO)


def get_image_config() -> Optional[ProviderConfig]:
    """Get the configured image provider."""
    registry = get_providers_registry()
    return registry.get_best_available(ProviderType.IMAGE)


def get_voice_config() -> Optional[ProviderConfig]:
    """Get the configured voice provider."""
    registry = get_providers_registry()
    
    # Kokoro is always available as it's built-in
    for provider in registry.VOICE_PROVIDERS:
        if provider.name == "kokoro":
            return provider
    
    return registry.get_best_available(ProviderType.VOICE)


# Quick availability checks
def is_llm_available() -> bool:
    """Check if any LLM provider is available."""
    return get_llm_config() is not None


def is_video_available() -> bool:
    """Check if any video provider is available."""
    return get_video_config() is not None


def is_ready_for_generation() -> bool:
    """Check if system is ready for full generation pipeline."""
    return is_llm_available() and is_video_available()
