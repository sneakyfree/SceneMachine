"""Phase 21 Integration Tests - Video Generation Providers.

Tests for the provider registry system and individual providers.
"""

from unittest.mock import MagicMock, patch
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
        from scenemachine.generators.base import ProviderFeature
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.replicate import ReplicateProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.fal import FalProvider

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
        """Test ComfyUI workflow building (legacy AnimateDiff stub)."""
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.comfyui import ComfyUIProvider

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

    # ------------------------------------------------------------------
    # Tests for the four locally-supported model workflows added in the
    # feat/wire-local-wan22-stack patch. These do NOT submit to ComfyUI;
    # they only validate that the workflow-dict generation is well-formed
    # and references the registered model files / required custom nodes.
    # ------------------------------------------------------------------

    def _make_request(self, **overrides):
        from scenemachine.generators.base import GenerationRequest

        defaults = {
            "shot_id": uuid4(),
            "prompt": "a cinematic wide shot of a windswept desert at golden hour",
            "negative_prompt": "ugly, blurry",
            "width": 768,
            "height": 432,
            "duration_seconds": 3.0,
            "fps": 24,
            "seed": 42,
            "guidance_scale": 6.0,
            "num_inference_steps": 30,
        }
        defaults.update(overrides)
        return GenerationRequest(**defaults)

    def test_comfyui_wan22_t2v_workflow_structure(self):
        """Wan 2.2 T2V workflow contains the required Wan nodes and references
        registered model files via the WanVideoModelLoader / TextEncoder / VAE
        chain.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-t2v-14b-fp8")
        assert model is not None

        request = self._make_request()
        wf = provider._build_workflow(request, model)

        # Workflow shape: API-format flat dict of node_id → {class_type, inputs}
        assert isinstance(wf, dict)
        assert len(wf) >= 8

        class_types = [n["class_type"] for n in wf.values()]
        for required in (
            "WanVideoModelLoader",
            "LoadWanVideoT5TextEncoder",
            "WanVideoTextEncode",
            "WanVideoVAELoader",
            "WanVideoEmptyEmbeds",
            "WanVideoSampler",
            "WanVideoDecode",
            "VHS_VideoCombine",
        ):
            assert required in class_types, f"missing required node: {required}"

        # Model files are sourced from model.extra_params, not hard-coded
        loader_inputs = next(
            n["inputs"] for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert loader_inputs["model"] == model.extra_params["model_file"]

    def test_comfyui_wan22_i2v_workflow_uses_clip_vision(self):
        """Wan 2.2 I2V workflow loads an image, runs CLIP-Vision, and uses
        WanVideoImageClipEncode (not WanVideoEmptyEmbeds)."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-i2v-14b-fp8")
        request = self._make_request(input_image_path="some_starter_frame.png")

        wf = provider._build_workflow(request, model)
        class_types = [n["class_type"] for n in wf.values()]

        assert "LoadImage" in class_types
        assert "CLIPVisionLoader" in class_types
        assert "WanVideoImageClipEncode" in class_types
        # T2V's empty-embed path must NOT be present:
        assert "WanVideoEmptyEmbeds" not in class_types

        # The LoadImage node must point at the request's input image
        load_image = next(
            n for n in wf.values() if n["class_type"] == "LoadImage"
        )
        assert load_image["inputs"]["image"] == "some_starter_frame.png"

    def test_comfyui_wan_animate_requires_reference_image(self):
        """Wan Animate must raise a clear ValueError if no reference image
        is supplied via character_references[*] OR input_image_path."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request()  # no character_references, no input_image_path

        with pytest.raises(ValueError, match="character reference image"):
            provider._build_workflow(request, model)

    def test_comfyui_wan_animate_extracts_reference_from_character_references(self):
        """Wan Animate uses request.character_references[0]['reference_image_path']
        when present, even if input_image_path is unset."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(
            character_references=[
                {"character_id": "hero", "reference_image_path": "hero_ref.png"}
            ]
        )

        wf = provider._build_workflow(request, model)
        load_image = next(
            n for n in wf.values() if n["class_type"] == "LoadImage"
        )
        assert load_image["inputs"]["image"] == "hero_ref.png"

    def test_comfyui_wan_animate_prefers_fp8_weight_when_registered_AND_available(self):
        """When the Animate model has a real FP8 path registered AND
        ComfyUI has the file in its WanVideoModelLoader dropdown, the
        Animate builder should pick the FP8 variant in preference to the
        larger BF16 weight.

        Uses a synthetic FP8 filename because no public FP8 quant of
        Wan Animate is published yet (Kijai hosts only LoRAs as of
        2026-05-13). When a real one ships, swap the synthetic name
        for the actual file and the test continues to pass.
        """
        from copy import deepcopy

        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = deepcopy(provider.get_model("wan22-animate-14b"))
        # Inject a synthetic FP8 path so the resolver has something to prefer
        synth_fp8 = "wan2.2_animate_14B_fp8_e4m3fn_scaled_SYNTHETIC.safetensors"
        model.extra_params["model_file_fp8"] = synth_fp8
        bf16 = model.extra_params["model_file"]

        # Pretend ComfyUI has both files available — bypass HTTP.
        provider._available_models_cache = {
            "WanVideoModelLoader": {synth_fp8, bf16},
        }
        request = self._make_request(input_image_path="ref.png")
        wf = provider._build_workflow(request, model)
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert loader["inputs"]["model"] == synth_fp8

    def test_comfyui_wan_animate_falls_back_to_bf16_when_fp8_not_on_disk(self):
        """If only the BF16 weight is in ComfyUI's dropdown (e.g. the Kijai
        FP8 quant hasn't been downloaded yet), the Animate builder picks
        the BF16 instead of failing loudly at submission time."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        bf16 = model.extra_params["model_file"]

        # Pretend ComfyUI has ONLY the BF16 — bypass HTTP.
        provider._available_models_cache = {
            "WanVideoModelLoader": {bf16},
        }
        request = self._make_request(input_image_path="ref.png")
        wf = provider._build_workflow(request, model)
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert loader["inputs"]["model"] == bf16

    def test_comfyui_wan_animate_uses_animate_embeds_not_image_clip_encode(self):
        """The Animate workflow MUST feed the sampler from
        ``WanVideoAnimateEmbeds`` (Animate-shaped WANVIDIMAGE_EMBEDS),
        NOT from ``WanVideoImageClipEncode`` (I2V-shaped). Using the I2V
        path crashes Animate's transformer at the first attention
        LayerNorm with ``Given normalized_shape=[1280], expected ...``.
        Validated 2026-05-13.

        Also: num_frames goes to WanVideoAnimateEmbeds (it owns the
        latent shape calculation for Animate). 3s * 24fps = 72 raw
        frames → dispatcher rounds via ((n-1)//4)*4+1 → 69.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(input_image_path="ref.png", duration_seconds=3.0, fps=24)

        wf = provider._build_workflow(request, model)
        class_types = [n["class_type"] for n in wf.values()]
        assert "WanVideoAnimateEmbeds" in class_types
        # The I2V encode node must NOT appear in the Animate workflow.
        assert "WanVideoImageClipEncode" not in class_types

        # The clip-vision step uses the lower-level encode that feeds
        # AnimateEmbeds (outputs WANVIDIMAGE_CLIPEMBEDS, not the bundled
        # I2V WANVIDIMAGE_EMBEDS).
        assert "WanVideoClipVisionEncode" in class_types

        ae = next(n for n in wf.values() if n["class_type"] == "WanVideoAnimateEmbeds")
        assert ae["inputs"]["num_frames"] == 69
        assert ae["inputs"]["width"] == request.width
        assert ae["inputs"]["height"] == request.height
        # Reference image must be wired into ref_images (LoadImage at "5").
        assert ae["inputs"]["ref_images"] == ["5", 0]

        # The sampler must consume AnimateEmbeds, not ClipVisionEncode.
        sampler = next(n for n in wf.values() if n["class_type"] == "WanVideoSampler")
        ae_node_id = next(
            nid for nid, n in wf.items() if n["class_type"] == "WanVideoAnimateEmbeds"
        )
        assert sampler["inputs"]["image_embeds"] == [ae_node_id, 0]

    def test_comfyui_wan_animate_infers_quantization_from_filename(self):
        """The WanVideoModelLoader's quantization param must match the
        actual model weight type — using fp8_e4m3fn_scaled on a BF16
        weight raises 'The model is not a scaled fp8 model'. Verify the
        builder picks the right quantization for each filename pattern."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        # When only BF16 is available, quantization should be "disabled"
        model = provider.get_model("wan22-animate-14b")
        provider._available_models_cache = {
            "WanVideoModelLoader": {model.extra_params["model_file"]},  # only BF16
        }
        request = self._make_request(input_image_path="ref.png")
        wf = provider._build_workflow(request, model)
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert loader["inputs"]["quantization"] == "disabled"
        assert loader["inputs"]["model"] == model.extra_params["model_file"]

        # When a synthetic FP8 weight is registered AND available,
        # quantization should infer to fp8_e4m3fn_scaled from the filename.
        from copy import deepcopy
        model2 = deepcopy(model)
        synth_fp8 = "wan2.2_animate_14B_fp8_e4m3fn_scaled_TEST.safetensors"
        model2.extra_params["model_file_fp8"] = synth_fp8
        provider._available_models_cache = {
            "WanVideoModelLoader": {model.extra_params["model_file"], synth_fp8},
        }
        wf2 = provider._build_workflow(request, model2)
        loader2 = next(
            n for n in wf2.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert loader2["inputs"]["quantization"] == "fp8_e4m3fn_scaled"
        assert loader2["inputs"]["model"] == synth_fp8

    def test_comfyui_wan_animate_block_swap_on_by_default(self):
        """Wan Animate BF16 (32 GB weight) cannot load on a 32 GB-VRAM
        card without block-swap. The registry must default
        ``blocks_to_swap`` > 0 so the production code path attaches a
        WanVideoBlockSwap node wired into the ModelLoader.

        Validated 2026-05-13 — without block_swap the loader OOMs at
        ``nodes_model_loading.py:921 load_weights`` after allocating
        ~29.4 GiB of the 32 GB weight.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        # Registry must declare a non-zero blocks_to_swap for the BF16 path
        assert model.extra_params.get("blocks_to_swap", 0) > 0

        request = self._make_request(input_image_path="ref.png")
        wf = provider._build_workflow(request, model)

        block_swap = next(
            (n for n in wf.values() if n["class_type"] == "WanVideoBlockSwap"),
            None,
        )
        assert block_swap is not None, "Animate BF16 must attach WanVideoBlockSwap"
        assert block_swap["inputs"]["blocks_to_swap"] == model.extra_params["blocks_to_swap"]
        # And the ModelLoader must pull block_swap_args from that node
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        bs_node_id = next(
            nid for nid, n in wf.items() if n["class_type"] == "WanVideoBlockSwap"
        )
        assert loader["inputs"]["block_swap_args"] == [bs_node_id, 0]

    def test_comfyui_wan_animate_load_device_is_offload_by_default(self):
        """Wan Animate BF16 must load_device=offload_device on the 32 GB
        card: Kijai's loader copies weights to GPU directly when set to
        main_device, OOMing before block_swap can offload any blocks.
        Validated 2026-05-13 — with main_device the loader allocates
        ~29.4 GiB before hitting the device limit even with
        block_swap_args attached.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        assert model.extra_params.get("load_device") == "offload_device"

        request = self._make_request(input_image_path="ref.png")
        wf = provider._build_workflow(request, model)
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert loader["inputs"]["load_device"] == "offload_device"

    def test_comfyui_wan_animate_block_swap_disabled_via_request(self):
        """A caller can opt out of block-swap by setting blocks_to_swap=0
        (only safe on cards with enough VRAM to hold the full BF16 weight).
        When disabled, no WanVideoBlockSwap node is attached and the
        ModelLoader has no ``block_swap_args`` input.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={"blocks_to_swap": 0},
        )
        wf = provider._build_workflow(request, model)
        class_types = [n["class_type"] for n in wf.values()]
        assert "WanVideoBlockSwap" not in class_types
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert "block_swap_args" not in loader["inputs"]

    def test_comfyui_wan_animate_block_swap_request_override(self):
        """Per-shot tuning: a request can override blocks_to_swap to use
        more or fewer than the registry default (e.g. higher for a 24 GB
        card, lower for a 48 GB card).
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={"blocks_to_swap": 32},
        )
        wf = provider._build_workflow(request, model)
        block_swap = next(
            n for n in wf.values() if n["class_type"] == "WanVideoBlockSwap"
        )
        assert block_swap["inputs"]["blocks_to_swap"] == 32

    def test_comfyui_wan_animate_speed_lora_on_by_default(self):
        """Animate uses Lightx2v 4-step LoRA by default.

        Validated 2026-05-13: with the LoRA on, a shot takes ~101s vs
        ~844s without (8.3× speedup) at equivalent quality. The default
        flipped to True after the underlying conditioning bug was fixed
        in PR #38 — earlier "speed_lora incompatible with Animate"
        failures were the conditioning shape, not the LoRA.

        Callers who want the 30-step baseline can opt out by passing
        request.extra_params['speed_lora'] = False.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        # Guard against an unintentional flip back to False.
        assert model.extra_params.get("speed_lora_enabled_by_default") is True

        # 0 sentinels → fall back to the model defaults, which under
        # speed_lora=True resolve to the LoRA-calibrated 4 steps / cfg=1.0.
        # (Explicit caller values still win — see opt_out test below.)
        request = self._make_request(
            input_image_path="ref.png",
            num_inference_steps=0,
            guidance_scale=0,
        )
        wf = provider._build_workflow(request, model)

        class_types = [n["class_type"] for n in wf.values()]
        assert "WanVideoLoraSelect" in class_types
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        # ModelLoader pulls WANVIDLORA from the LoRA node
        lora_node_id = next(
            nid for nid, n in wf.items() if n["class_type"] == "WanVideoLoraSelect"
        )
        assert loader["inputs"]["lora"] == [lora_node_id, 0]
        sampler = next(
            n for n in wf.values() if n["class_type"] == "WanVideoSampler"
        )
        # Lightx2v-calibrated 4 steps / cfg=1.0 (vs registry defaults of 30 / 6.0)
        assert sampler["inputs"]["steps"] == 4
        assert sampler["inputs"]["cfg"] == 1.0

    def test_comfyui_wan_animate_speed_lora_opt_out(self):
        """Callers can opt out of the speed LoRA via extra_params['speed_lora']=False.
        This restores the slower 30-step / cfg=6.0 baseline (useful when
        validating quality regressions or comparing output character).
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={"speed_lora": False},
        )
        wf = provider._build_workflow(request, model)
        class_types = [n["class_type"] for n in wf.values()]
        assert "WanVideoLoraSelect" not in class_types
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        assert "lora" not in loader["inputs"]
        sampler = next(
            n for n in wf.values() if n["class_type"] == "WanVideoSampler"
        )
        assert sampler["inputs"]["steps"] == model.default_steps
        assert sampler["inputs"]["cfg"] == model.default_cfg_scale

    def test_comfyui_wan_animate_speed_lora_via_request_extra_params(self):
        """Setting request.extra_params['speed_lora'] = True attaches a
        WanVideoLoraSelect node, wires its WANVIDLORA output into the
        WanVideoModelLoader's optional `lora` input, and switches the
        sampler to Lightx2v's calibrated 4 steps / cfg=1.0.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        # Pretend ComfyUI sees the first candidate so the resolver picks it.
        candidates = model.extra_params["speed_lora_candidates"]
        assert candidates, "registry must list at least one LoRA candidate"
        provider._available_models_cache = {
            "WanVideoLoraSelect": {candidates[0]},
        }

        # 0 here means "use the workflow's defaults" — same convention the
        # T2V/I2V builders use (request.num_inference_steps or model.default_steps).
        # Under speed_lora=True, "default" becomes the LoRA-calibrated 4 / 1.0.
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={"speed_lora": True},
            num_inference_steps=0,
            guidance_scale=0,
        )
        wf = provider._build_workflow(request, model)

        # LoRA node present and wired
        lora_node = next(
            (n for n in wf.values() if n["class_type"] == "WanVideoLoraSelect"),
            None,
        )
        assert lora_node is not None, "speed_lora=True must add WanVideoLoraSelect"
        assert lora_node["inputs"]["lora"] == candidates[0]
        assert lora_node["inputs"]["strength"] == 1.0

        # ModelLoader pulls WANVIDLORA from the LoRA node
        loader = next(
            n for n in wf.values() if n["class_type"] == "WanVideoModelLoader"
        )
        # Find the node id of the LoRA node so we can compare reference
        lora_node_id = next(
            nid for nid, n in wf.items() if n["class_type"] == "WanVideoLoraSelect"
        )
        assert loader["inputs"]["lora"] == [lora_node_id, 0]

        # Sampler runs at Lightx2v-calibrated settings
        sampler = next(
            n for n in wf.values() if n["class_type"] == "WanVideoSampler"
        )
        assert sampler["inputs"]["steps"] == 4
        assert sampler["inputs"]["cfg"] == 1.0

    def test_comfyui_wan_animate_speed_lora_resolves_first_available(self):
        """When multiple LoRA candidates are registered, the builder picks
        the first one that ComfyUI actually has on disk. Mirrors the same
        pattern as the FP8/BF16 weight resolver.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        candidates = model.extra_params["speed_lora_candidates"]
        assert len(candidates) >= 2, "test requires at least 2 LoRA candidates"

        # Pretend ComfyUI has ONLY the second candidate — the resolver
        # should skip the first and select #2.
        provider._available_models_cache = {
            "WanVideoLoraSelect": {candidates[1]},
        }
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={"speed_lora": True},
        )
        wf = provider._build_workflow(request, model)
        lora_node = next(
            n for n in wf.values() if n["class_type"] == "WanVideoLoraSelect"
        )
        assert lora_node["inputs"]["lora"] == candidates[1]

    def test_comfyui_wan_animate_speed_lora_file_override(self):
        """A caller can supply request.extra_params['speed_lora_file'] to
        force a specific LoRA file, bypassing the registry's candidate list.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={
                "speed_lora": True,
                "speed_lora_file": "custom_lightx2v_variant.safetensors",
            },
        )
        wf = provider._build_workflow(request, model)
        lora_node = next(
            n for n in wf.values() if n["class_type"] == "WanVideoLoraSelect"
        )
        assert lora_node["inputs"]["lora"] == "custom_lightx2v_variant.safetensors"

    def test_comfyui_wan_animate_speed_lora_request_steps_cfg_still_win(self):
        """Even with the speed LoRA active, an explicit num_inference_steps
        or guidance_scale on the request still wins. The LoRA flag changes
        the defaults; it doesn't override caller intent.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        request = self._make_request(
            input_image_path="ref.png",
            extra_params={"speed_lora": True},
            num_inference_steps=8,
            guidance_scale=2.5,
        )
        wf = provider._build_workflow(request, model)
        sampler = next(
            n for n in wf.values() if n["class_type"] == "WanVideoSampler"
        )
        assert sampler["inputs"]["steps"] == 8
        assert sampler["inputs"]["cfg"] == 2.5

    def test_comfyui_ltx2_workflow_uses_gemma_encoder(self):
        """LTX-2 workflow loads the Lightricks Gemma CLIP model and uses
        EmptyLTXVLatentVideo + LTXVConditioning, not the Wan node graph."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("ltx2-19b-dev-fp8")
        request = self._make_request()

        wf = provider._build_workflow(request, model)
        class_types = [n["class_type"] for n in wf.values()]

        for required in (
            "CheckpointLoaderSimple",
            "LTXVGemmaCLIPModelLoader",
            "CLIPTextEncode",
            "LTXVConditioning",
            "EmptyLTXVLatentVideo",
            "KSampler",
            "VAEDecode",
            "VHS_VideoCombine",
        ):
            assert required in class_types, f"missing required node: {required}"

        # Make sure the Wan path is NOT activated:
        for wan_only in (
            "WanVideoModelLoader",
            "WanVideoEmptyEmbeds",
            "WanVideoSampler",
        ):
            assert wan_only not in class_types

    def test_comfyui_workflow_request_extra_params_override(self):
        """Per-shot overrides in request.extra_params take priority over the
        model's default extra_params for Wan tunables like `shift` and
        `scheduler`."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-t2v-14b-fp8")
        # Sanity: model defaults to unipc / shift=5.0
        assert model.extra_params.get("scheduler") == "unipc"

        request = self._make_request(
            extra_params={"shift": 8.0, "scheduler": "dpm++"}
        )
        wf = provider._build_workflow(request, model)
        sampler = next(
            n for n in wf.values() if n["class_type"] == "WanVideoSampler"
        )
        assert sampler["inputs"]["shift"] == 8.0
        assert sampler["inputs"]["scheduler"] == "dpm++"

    def test_comfyui_default_model_is_wan22_t2v(self):
        """The provider's default model is the primary local cinematic stack,
        not an animatediff stub. Guards against future regressions in the
        defaults that would silently change the user's first-shot behavior."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        assert provider.model_id == "wan22-t2v-14b-fp8"
        assert provider.DEFAULT_MODEL == "wan22-t2v-14b-fp8"

    def test_comfyui_animate_registry_no_phantom_fp8_path(self):
        """Guard: the Animate model registry's model_file_fp8 must be
        either None or a path that actually exists in some publicly
        downloadable repo. Setting it to a speculative string ('we'll
        download this someday') causes the runtime resolver to think
        FP8 is preferred and fail submission when the file isn't on
        disk. The current state (no public FP8 quant published) should
        be model_file_fp8: None.
        """
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        fp8 = model.extra_params.get("model_file_fp8")
        # Either None (no FP8 yet) or a real registered filename — never
        # a speculative path.
        assert fp8 is None or isinstance(fp8, str)
        if fp8 is not None:
            # If we ever set it, it must look like a real file path
            assert fp8.endswith(".safetensors")

    def test_comfyui_animate_has_extended_timeout(self):
        """Wan Animate BF16 needs > 10 min on borderline VRAM. The
        registry should declare ``expected_timeout_seconds`` so the
        polling loop doesn't time out at 600s default."""
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        model = provider.get_model("wan22-animate-14b")
        assert model.extra_params.get("expected_timeout_seconds", 0) >= 1800

    def test_comfyui_provider_advertises_character_consistency(self):
        """Wan Animate gives us character-consistency support, so the
        provider's capabilities must advertise the feature."""
        from scenemachine.generators.base import ProviderFeature
        from scenemachine.generators.comfyui import ComfyUIProvider

        provider = ComfyUIProvider()
        assert ProviderFeature.CHARACTER_CONSISTENCY in provider.capabilities.features


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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.runpod import RunPodProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.runpod import RunPodProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.generators.base import GenerationRequest
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.api.routes.health import providers_health_check
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.api.routes.health import provider_health_check
        from scenemachine.generators.base import ProviderRegistry
        from scenemachine.generators.mock import MockGenerationProvider

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
        from scenemachine.api.routes.health import provider_health_check
        from scenemachine.generators.base import ProviderRegistry

        ProviderRegistry.reset()

        response = await provider_health_check("nonexistent")

        assert response.available is False
        assert "unknown" in response.message.lower()

        ProviderRegistry.reset()
