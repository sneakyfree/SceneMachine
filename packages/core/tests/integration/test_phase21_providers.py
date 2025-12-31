"""Phase 21 Integration Tests - Video Generation Providers.

Tests for the provider registry system and individual providers.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from scenemachine.models.generation_job import JobProvider


# =============================================================================
# Provider Registry Tests
# =============================================================================


class TestProviderRegistry:
    """Test the provider registry system."""

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        from scenemachine.generators.base import ProviderRegistry

        ProviderRegistry.reset()
        registry1 = ProviderRegistry.get_instance()
        registry2 = ProviderRegistry.get_instance()
        assert registry1 is registry2
        ProviderRegistry.reset()

    def test_register_provider(self):
        """Test registering a provider."""
        from scenemachine.generators.base import (
            GenerationProvider,
            ProviderRegistry,
        )
        from scenemachine.generators.mock import MockGenerationProvider

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()

        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        assert registry.is_registered(JobProvider.LOCAL)
        assert JobProvider.LOCAL in registry.list_providers()

        ProviderRegistry.reset()

    def test_get_provider(self):
        """Test getting a provider instance."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        provider = registry.get_provider(JobProvider.LOCAL)
        assert provider is not None
        assert isinstance(provider, MockGenerationProvider)
        assert provider.name == "Mock Provider"

        ProviderRegistry.reset()

    def test_get_unregistered_provider(self):
        """Test getting an unregistered provider returns None."""
        from scenemachine.generators.base import ProviderRegistry

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()

        provider = registry.get_provider(JobProvider.REPLICATE)
        assert provider is None

        ProviderRegistry.reset()

    def test_unregister_provider(self):
        """Test unregistering a provider."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        assert registry.is_registered(JobProvider.LOCAL)

        registry.unregister(JobProvider.LOCAL)

        assert not registry.is_registered(JobProvider.LOCAL)
        assert registry.get_provider(JobProvider.LOCAL) is None

        ProviderRegistry.reset()

    def test_provider_with_config(self):
        """Test registering provider with default config."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()

        registry.register(
            JobProvider.LOCAL,
            MockGenerationProvider,
            config={"simulate_delay": 5.0},
        )

        provider = registry.get_provider(JobProvider.LOCAL)
        assert provider is not None
        assert provider.simulate_delay == 5.0

        ProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_list_available_providers(self):
        """Test listing available providers."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        available = await registry.list_available_providers()
        assert JobProvider.LOCAL in available

        ProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_get_all_health(self):
        """Test getting health status of all providers."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        health = await registry.get_all_health()

        assert JobProvider.LOCAL in health
        assert health[JobProvider.LOCAL].available is True

        ProviderRegistry.reset()


# =============================================================================
# Mock Provider Tests
# =============================================================================


class TestMockProvider:
    """Test the mock generation provider."""

    def test_mock_provider_properties(self):
        """Test mock provider basic properties."""
        from scenemachine.generators.mock import MockGenerationProvider

        provider = MockGenerationProvider()

        assert provider.name == "Mock Provider"
        assert provider.provider_type == JobProvider.LOCAL

    def test_mock_provider_capabilities(self):
        """Test mock provider capabilities."""
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.generators.base import ProviderFeature

        provider = MockGenerationProvider()
        caps = provider.capabilities

        assert ProviderFeature.TEXT_TO_VIDEO in caps.features
        assert ProviderFeature.IMAGE_TO_VIDEO in caps.features
        assert caps.max_width >= 1920
        assert caps.max_duration >= 10.0

    @pytest.mark.asyncio
    async def test_mock_provider_availability(self):
        """Test mock provider is always available."""
        from scenemachine.generators.mock import MockGenerationProvider

        provider = MockGenerationProvider()
        available = await provider.check_availability()
        assert available is True

    def test_mock_provider_list_models(self):
        """Test listing mock models."""
        from scenemachine.generators.mock import MockGenerationProvider

        provider = MockGenerationProvider()
        models = provider.list_models()

        assert len(models) >= 1
        assert any(m["id"] == "mock-fast" for m in models)

    def test_mock_provider_estimate_cost(self):
        """Test mock provider cost estimation (always free)."""
        from scenemachine.generators.mock import MockGenerationProvider

        provider = MockGenerationProvider()
        cost = provider.estimate_cost(duration_seconds=10.0)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_mock_provider_generate(self, tmp_path):
        """Test mock provider generation."""
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.generators.base import GenerationRequest

        # Patch settings to use tmp_path
        with patch("scenemachine.generators.mock.get_settings") as mock_settings:
            settings = MagicMock()
            settings.output_dir = tmp_path
            mock_settings.return_value = settings

            provider = MockGenerationProvider(simulate_delay=0.1)
            shot_id = uuid4()

            request = GenerationRequest(
                shot_id=shot_id,
                prompt="A beautiful sunset",
                width=1280,
                height=720,
                duration_seconds=3.0,
            )

            progress_updates = []

            async def progress_callback(progress):
                progress_updates.append(progress)

            result = await provider.generate(request, progress_callback)

            assert result.success is True
            assert result.output_path is not None
            assert result.cost_usd == 0.0
            assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_mock_provider_simulated_failure(self, tmp_path):
        """Test mock provider simulated failures."""
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.generators.base import GenerationRequest

        with patch("scenemachine.generators.mock.get_settings") as mock_settings:
            settings = MagicMock()
            settings.output_dir = tmp_path
            mock_settings.return_value = settings

            # Configure to always fail
            provider = MockGenerationProvider(
                simulate_delay=0.1,
                simulate_failures=True,
                failure_rate=1.0,  # 100% failure rate
            )

            request = GenerationRequest(
                shot_id=uuid4(),
                prompt="Test prompt",
            )

            result = await provider.generate(request)

            assert result.success is False
            assert result.error_code == "MOCK_FAILURE"


# =============================================================================
# Replicate Provider Tests
# =============================================================================


class TestReplicateProvider:
    """Test the Replicate provider."""

    def test_replicate_provider_properties(self):
        """Test Replicate provider basic properties."""
        from scenemachine.generators.replicate import ReplicateProvider

        provider = ReplicateProvider()

        assert provider.name == "Replicate"
        assert provider.provider_type == JobProvider.REPLICATE

    def test_replicate_provider_models(self):
        """Test Replicate provider available models."""
        from scenemachine.generators.replicate import ReplicateProvider

        provider = ReplicateProvider()
        models = provider.list_models()

        assert len(models) >= 3
        model_ids = [m["id"] for m in models]
        assert "minimax" in model_ids
        assert "luma" in model_ids

    def test_replicate_provider_cost_estimation(self):
        """Test Replicate provider cost estimation."""
        from scenemachine.generators.replicate import ReplicateProvider

        provider = ReplicateProvider(model_id="minimax")
        cost = provider.estimate_cost(duration_seconds=3.0)

        assert cost > 0
        assert cost == 0.08 * 3.0  # minimax is $0.08/sec

    @pytest.mark.asyncio
    async def test_replicate_unavailable_without_token(self):
        """Test Replicate is unavailable without API token."""
        from scenemachine.generators.replicate import ReplicateProvider

        provider = ReplicateProvider(api_token=None)
        available = await provider.check_availability()
        assert available is False

    @pytest.mark.asyncio
    async def test_replicate_generate_without_token(self):
        """Test Replicate generation fails without token."""
        from scenemachine.generators.replicate import ReplicateProvider
        from scenemachine.generators.base import GenerationRequest

        provider = ReplicateProvider(api_token=None)
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test prompt",
        )

        result = await provider.generate(request)

        assert result.success is False
        assert result.error_code == "MISSING_API_TOKEN"


# =============================================================================
# Fal Provider Tests
# =============================================================================


class TestFalProvider:
    """Test the Fal.ai provider."""

    def test_fal_provider_properties(self):
        """Test Fal provider basic properties."""
        from scenemachine.generators.fal import FalProvider

        provider = FalProvider()

        assert provider.name == "Fal.ai"
        assert provider.provider_type == JobProvider.FAL

    def test_fal_provider_models(self):
        """Test Fal provider available models."""
        from scenemachine.generators.fal import FalProvider

        provider = FalProvider()
        models = provider.list_models()

        assert len(models) >= 4
        model_ids = [m["id"] for m in models]
        assert "ltx" in model_ids
        assert "cogvideox" in model_ids

    def test_fal_provider_cost_estimation(self):
        """Test Fal provider cost estimation."""
        from scenemachine.generators.fal import FalProvider

        provider = FalProvider(model_id="ltx")
        cost = provider.estimate_cost(duration_seconds=3.0)

        assert cost > 0
        assert cost == 0.04 * 3.0  # LTX is $0.04/sec

    @pytest.mark.asyncio
    async def test_fal_unavailable_without_key(self):
        """Test Fal is unavailable without API key."""
        from scenemachine.generators.fal import FalProvider

        provider = FalProvider(api_key=None)
        available = await provider.check_availability()
        assert available is False

    @pytest.mark.asyncio
    async def test_fal_generate_without_key(self):
        """Test Fal generation fails without API key."""
        from scenemachine.generators.fal import FalProvider
        from scenemachine.generators.base import GenerationRequest

        provider = FalProvider(api_key=None)
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test prompt",
        )

        result = await provider.generate(request)

        assert result.success is False
        assert result.error_code == "MISSING_API_TOKEN"


# =============================================================================
# ComfyUI Provider Tests
# =============================================================================


class TestComfyUIProvider:
    """Test the ComfyUI local provider."""

    def test_comfyui_provider_properties(self):
        """Test ComfyUI provider basic properties."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()

        assert provider.name == "ComfyUI Local"
        assert provider.provider_type == JobProvider.CUSTOM

    def test_comfyui_provider_models(self):
        """Test ComfyUI provider available models."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        models = provider.list_models()

        assert len(models) >= 3
        model_ids = [m["id"] for m in models]
        assert "animatediff-v3" in model_ids
        assert "svd-xt" in model_ids

    def test_comfyui_provider_cost_estimation(self):
        """Test ComfyUI provider cost estimation (free)."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        cost = provider.estimate_cost(duration_seconds=10.0)
        assert cost == 0.0  # Local is free

    @pytest.mark.asyncio
    async def test_comfyui_unavailable_when_not_running(self):
        """Test ComfyUI is unavailable when not running."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        # Use an invalid URL
        provider = ComfyUIProvider(comfyui_url="http://127.0.0.1:99999")
        available = await provider.check_availability()
        assert available is False

    def test_comfyui_workflow_building(self):
        """Test ComfyUI workflow building."""
        from scenemachine.generators.comfyui import ComfyUIProvider
        from scenemachine.generators.base import GenerationRequest

        provider = ComfyUIProvider()
        model = provider.get_model("animatediff-v3")

        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="A cat walking",
            width=512,
            height=512,
            duration_seconds=2.0,
            fps=8,
        )

        workflow = provider._build_workflow(request, model)

        assert isinstance(workflow, dict)
        assert len(workflow) > 0
        # Check for key nodes
        assert any("KSampler" in str(v) for v in workflow.values())


# =============================================================================
# RunPod Provider Tests
# =============================================================================


class TestRunPodProvider:
    """Test the RunPod serverless provider."""

    def test_runpod_provider_properties(self):
        """Test RunPod provider basic properties."""
        from scenemachine.generators.runpod import RunPodProvider

        provider = RunPodProvider()

        assert provider.name == "RunPod Serverless"
        assert provider.provider_type == JobProvider.RUNPOD

    def test_runpod_provider_models(self):
        """Test RunPod provider available models."""
        from scenemachine.generators.runpod import RunPodProvider

        provider = RunPodProvider()
        models = provider.list_models()

        assert len(models) >= 3
        model_ids = [m["id"] for m in models]
        assert "animatediff-v3" in model_ids
        assert "cogvideox-5b" in model_ids

    def test_runpod_provider_cost_estimation(self):
        """Test RunPod provider cost estimation."""
        from scenemachine.generators.runpod import RunPodProvider

        provider = RunPodProvider(model_id="animatediff-v3")
        cost = provider.estimate_cost(duration_seconds=3.0)

        assert cost > 0
        assert cost == 0.02 * 3.0  # animatediff is $0.02/sec

    @pytest.mark.asyncio
    async def test_runpod_unavailable_without_config(self):
        """Test RunPod is unavailable without API key and endpoint."""
        from scenemachine.generators.runpod import RunPodProvider

        provider = RunPodProvider(api_key=None, endpoint_id=None)
        available = await provider.check_availability()
        assert available is False

    @pytest.mark.asyncio
    async def test_runpod_generate_without_key(self):
        """Test RunPod generation fails without API key."""
        from scenemachine.generators.runpod import RunPodProvider
        from scenemachine.generators.base import GenerationRequest

        provider = RunPodProvider(api_key=None)
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test prompt",
        )

        result = await provider.generate(request)

        assert result.success is False
        assert result.error_code == "MISSING_API_KEY"

    @pytest.mark.asyncio
    async def test_runpod_generate_without_endpoint(self):
        """Test RunPod generation fails without endpoint ID."""
        from scenemachine.generators.runpod import RunPodProvider
        from scenemachine.generators.base import GenerationRequest

        provider = RunPodProvider(api_key="test-key", endpoint_id=None)
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test prompt",
        )

        result = await provider.generate(request)

        assert result.success is False
        assert result.error_code == "MISSING_ENDPOINT"


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Test generation request validation."""

    def test_validate_request_width(self):
        """Test request width validation."""
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.generators.base import GenerationRequest

        provider = MockGenerationProvider()

        # Valid request
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test",
            width=1280,
            height=720,
        )
        errors = provider.validate_request(request)
        assert len(errors) == 0

        # Invalid width (too large)
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test",
            width=10000,
            height=720,
        )
        errors = provider.validate_request(request)
        assert any("width" in e.lower() for e in errors)

    def test_validate_request_duration(self):
        """Test request duration validation."""
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.generators.base import GenerationRequest

        provider = MockGenerationProvider()

        # Valid duration
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test",
            duration_seconds=3.0,
        )
        errors = provider.validate_request(request)
        assert not any("duration" in e.lower() for e in errors)

        # Invalid duration (too long for some providers)
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test",
            duration_seconds=100.0,
        )
        errors = provider.validate_request(request)
        assert any("duration" in e.lower() for e in errors)


# =============================================================================
# Setup/Registry Integration Tests
# =============================================================================


class TestRegistrySetup:
    """Test the provider registry setup."""

    def test_setup_providers(self):
        """Test setting up all providers."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.registry import setup_providers

        ProviderRegistry.reset()

        with patch("scenemachine.generators.registry.get_settings") as mock_settings:
            settings = MagicMock()
            settings.replicate_api_token = "test-token"
            settings.replicate_video_model = "minimax"
            settings.fal_api_key = "test-key"
            settings.fal_video_model = "ltx"
            settings.comfyui_url = "http://127.0.0.1:8188"
            settings.runpod_api_key = None
            mock_settings.return_value = settings

            registry = setup_providers()

            assert registry is not None
            providers = registry.list_providers()
            assert len(providers) >= 4  # At least mock, replicate, fal, comfyui

        ProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_check_provider_status(self):
        """Test checking all provider status."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.registry import (
            check_provider_status,
            setup_providers,
        )

        ProviderRegistry.reset()

        with patch("scenemachine.generators.registry.get_settings") as mock_settings:
            settings = MagicMock()
            settings.replicate_api_token = None
            settings.replicate_video_model = None
            settings.fal_api_key = None
            settings.fal_video_model = None
            settings.comfyui_url = "http://127.0.0.1:8188"
            settings.runpod_api_key = None
            mock_settings.return_value = settings

            setup_providers()
            status = await check_provider_status()

            assert "providers" in status
            assert "total_registered" in status
            assert "total_available" in status
            assert status["total_registered"] >= 1

        ProviderRegistry.reset()


# =============================================================================
# Health Endpoint Tests
# =============================================================================


class TestProviderHealthEndpoints:
    """Test the provider health check endpoints."""

    @pytest.mark.asyncio
    async def test_providers_health_endpoint(self):
        """Test the /health/providers endpoint."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.api.routes.health import providers_health_check

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        response = await providers_health_check()

        assert response.total_registered >= 1
        assert response.total_available >= 1
        assert len(response.providers) >= 1
        assert any(p.provider == "local" for p in response.providers)

        ProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_single_provider_health_endpoint(self):
        """Test the /health/providers/{provider_type} endpoint."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider
        from scenemachine.api.routes.health import provider_health_check

        ProviderRegistry.reset()
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.LOCAL, MockGenerationProvider)

        response = await provider_health_check("local")

        assert response.provider == "local"
        assert response.name == "Mock Provider"
        assert response.available is True

        ProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_unknown_provider_health_endpoint(self):
        """Test health check for unknown provider."""
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.api.routes.health import provider_health_check

        ProviderRegistry.reset()

        response = await provider_health_check("nonexistent")

        assert response.available is False
        assert "unknown" in response.message.lower()

        ProviderRegistry.reset()
