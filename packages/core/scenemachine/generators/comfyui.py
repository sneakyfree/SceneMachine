"""ComfyUI local provider for video generation.

Connects to a local ComfyUI instance for video generation using
various video models like AnimateDiff, SVD, and Wan2.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from scenemachine.config import get_settings
from scenemachine.models.generation_job import JobProvider

from .base import (
    GenerationProgress,
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    ProgressCallback,
    ProviderCapabilities,
    ProviderFeature,
    ProviderHealth,
    VideoModel,
)

logger = logging.getLogger(__name__)


class ComfyUIProvider(GenerationProvider):
    """Local ComfyUI provider for video generation.

    Submits API-format workflows to a running ComfyUI instance over its
    REST API, polls until completion, downloads the output, and emits a
    thumbnail.

    Default URL: http://127.0.0.1:8188.

    Supported models (registered in ``MODELS``):
        * wan22-t2v-14b-fp8  — primary cinematic text-to-video
        * wan22-i2v-14b-fp8  — image-to-video for shot continuity
        * wan22-animate-14b  — character-ID-preserving (uses
          ``request.character_references`` or ``request.input_image_path``)
        * ltx2-19b-dev-fp8   — alternate cinematic via Lightricks Gemma encoder
        * animatediff-v3, svd-xt — legacy stubs kept for phase-21 tests

    Model-file prerequisites — the running ComfyUI instance MUST have these
    files reachable via its model-path config:

        Wan 2.2 family
            models/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
            models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors
            models/diffusion_models/wan2.2_animate_14B_bf16.safetensors
                (preferred: wan2.2_animate_14B_fp8_e4m3fn_scaled_KJ.safetensors)
            models/text_encoders/umt5_xxl_bf16_from_pth.safetensors
            models/vae/wan_2.1_vae.safetensors
            models/clip_vision/sigclip_vision_patch14_384.safetensors

        LTX-2
            models/checkpoints/ltx-2-19b-dev-fp8.safetensors
            models/text_encoders/gemma/model-00001-of-00005.safetensors

    Required custom nodes (the running ComfyUI must have these installed):
        * ComfyUI-WanVideoWrapper (Kijai)
        * ComfyUI-LTXVideo (Lightricks)
        * ComfyUI-VideoHelperSuite (for VHS_VideoCombine)

    Per-shot overrides — beyond the documented GenerationRequest fields,
    callers may pass these in ``request.extra_params`` to tune the workflow:
        * model_id       : override the provider's default model
        * shift          : float, Wan flow-matching shift (default 5.0)
        * scheduler      : str, Wan sampler scheduler (default "unipc")
        * tile_x, tile_y : int, VAE tile dims (default 272)
        * tile_stride_x  : int, VAE tile stride x (default 144)
        * tile_stride_y  : int, VAE tile stride y (default 128)
        * sampler_name   : str, KSampler sampler name for LTX-2 (default "euler")
        * speed_lora     : bool, Wan-Animate only — attach a Lightx2v 4-step
                           distillation LoRA and run sampler at 4 steps / cfg=1.0
                           (~7× speedup for the sampling phase)
        * speed_lora_file: str, override the LoRA filename (else picked from
                           the model's ``speed_lora_candidates`` list)
        * blocks_to_swap : int, Wan-Animate only — number of transformer
                           blocks to swap to CPU (14B has 40). Required > 0
                           for the BF16 weight on a 32 GB-VRAM card or it
                           OOMs at load. Set to 0 to disable.

    Example:
        provider = ComfyUIProvider(comfyui_url="http://127.0.0.1:8188")
        result = await provider.generate(request)
    """

    # Video workflow templates — maps short keys to internal builder names.
    # Used by the desktop renderer to populate model dropdowns and by
    # _build_workflow() for dispatch.
    WORKFLOWS = {
        "wan22_t2v": "wan2_2_t2v_a14b_fp8",
        "wan22_i2v": "wan2_2_i2v_a14b_fp8",
        "wan_animate": "wan2_2_animate_14b",
        "ltx2": "ltx_2_19b_dev",
        # Legacy stubs (kept for backwards compat with phase-21 tests):
        "animatediff": "animatediff_v3",
        "svd": "stable_video_diffusion",
    }

    MODELS: dict[str, VideoModel] = {
        # ============================================================
        # PRIMARY STACK — Wan 2.2 14B FP8 (fits 32 GB VRAM cleanly)
        # ============================================================
        "wan22-t2v-14b-fp8": VideoModel(
            id="wan22-t2v-14b-fp8",
            name="Wan 2.2 T2V 14B (FP8)",
            version="2.2",
            cost_per_second=0.0,  # Local = electricity only
            supports_text_to_video=True,
            supports_image_to_video=False,
            max_duration=8.0,
            default_fps=24,
            default_steps=30,
            default_cfg_scale=6.0,
            extra_params={
                "model_file": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                "vae_file": "wan_2.1_vae.safetensors",
                "text_encoder_file": "umt5_xxl_bf16_from_pth.safetensors",
                "scheduler": "unipc",
                "shift": 5.0,
                "expected_vram_gb": 22,
                # Cold load can take 8–12 min when the FP8 weight is read
                # off NVMe for the first time and the high/low-noise MoE
                # pair is staged. Warm inference is ~57 s. The default
                # POLL_TIMEOUT (600 s) was too tight for cold start and
                # caused the first shot of an overnight RADAR_LOVE_2 run
                # to spuriously fail (2026-05-14 02:50–03:00). Validated.
                "expected_timeout_seconds": 1200,
            },
        ),
        "wan22-i2v-14b-fp8": VideoModel(
            id="wan22-i2v-14b-fp8",
            name="Wan 2.2 I2V 14B (FP8)",
            version="2.2",
            cost_per_second=0.0,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=8.0,
            default_fps=24,
            default_steps=30,
            default_cfg_scale=6.0,
            extra_params={
                "model_file": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                "vae_file": "wan_2.1_vae.safetensors",
                "text_encoder_file": "umt5_xxl_bf16_from_pth.safetensors",
                "clip_vision_file": "sigclip_vision_patch14_384.safetensors",
                "scheduler": "unipc",
                "shift": 5.0,
                "expected_vram_gb": 24,
                # See T2V note above — same cold-load budget. Per the
                # i2v patient chart, cold-start hit 406 s on 2026-05-13;
                # the safety margin keeps headroom for cache-cold disks.
                "expected_timeout_seconds": 1200,
            },
        ),
        # ============================================================
        # CHARACTER-CONSISTENCY STACK — Wan 2.2 Animate
        # Takes one reference image of a character; preserves identity
        # across the generated shot. Use this for the recurring-character
        # case.
        #
        # VRAM caveat: the BF16 weight is 32 GB; on a 32 GB-VRAM card this
        # means the entire VRAM is consumed by the weight, with no headroom
        # for activations. Practical effect: first-shot inference is slow
        # (~10-30 min) due to aggressive CPU offload, and small batches /
        # short clips work but anything ambitious may OOM.
        #
        # When a public FP8 quant of Wan-Animate is published (Kijai has
        # only the LoRAs as of 2026-05-13; Comfy-Org's repack only ships
        # BF16), register it as ``model_file_fp8`` and the runtime
        # availability resolver in _resolve_first_available() will pick
        # it up automatically.
        #
        # Speed alternative: pair this model with one of Kijai's Lightx2v
        # 4-step distillation LoRAs (see Kijai/WanVideo_comfy LoRAs/
        # Wan22_Lightx2v/) to cut sampling steps from 30 to 4. Opt in via
        # request.extra_params['speed_lora'] = True; candidate filenames
        # are listed in ``speed_lora_candidates`` below and the first one
        # ComfyUI has on disk is selected.
        # ============================================================
        "wan22-animate-14b": VideoModel(
            id="wan22-animate-14b",
            name="Wan 2.2 Animate (Character ID-preserving)",
            version="2.2",
            cost_per_second=0.0,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=5.0,
            default_fps=24,
            default_steps=30,
            default_cfg_scale=6.0,
            extra_params={
                "model_file": "wan2.2_animate_14B_bf16.safetensors",
                # When a public FP8 quant exists, register it here. The
                # runtime resolver checks availability before using it.
                "model_file_fp8": None,
                "vae_file": "wan_2.1_vae.safetensors",
                "text_encoder_file": "umt5_xxl_bf16_from_pth.safetensors",
                # Wan Animate REQUIRES CLIP-ViT-H (1280-dim output) for its
                # face_adapter conditioning. SigLIP (1152-dim) produces
                # ``Given normalized_shape=[1280]`` LayerNorm crashes inside
                # the attention block. The T2V/I2V paths still use SigLIP;
                # Animate is the outlier. Validated 2026-05-13.
                "clip_vision_file": "clip_vision_h.safetensors",
                "scheduler": "unipc",
                "shift": 5.0,
                "expected_vram_gb": 32,
                "expected_timeout_seconds": 1800,  # 30 min — CPU-offload is slow
                "requires_character_reference": True,
                # load_device + block_swap together make Wan Animate BF16
                # work on a 32 GB-VRAM card. The model weight is 32 GB and
                # the device usable limit is ~31.4 GB, so:
                #
                #   1. load_device="offload_device" tells Kijai's loader to
                #      stage weights into RAM (we have 256 GB) instead of
                #      copying them straight to GPU. Without this, the
                #      loader OOMs at nodes_model_loading.py:921 on
                #      set_module_tensor_to_device after allocating
                #      ~29.4 GiB. Validated 2026-05-13.
                #
                #   2. blocks_to_swap=20 (14B has 40 blocks) keeps half the
                #      transformer blocks on CPU during inference and pages
                #      them in as needed. Without this, peak inference
                #      memory exceeds VRAM.
                #
                # Override either via request.extra_params for power-users
                # on different-VRAM hardware.
                "load_device": "offload_device",
                "blocks_to_swap": 20,
                "offload_img_emb": False,
                "offload_txt_emb": False,
                # Lightx2v 4-step distillation LoRA. Validated end-to-end
                # on 2026-05-13: with this LoRA enabled the same shot
                # generates in 101.6s vs 844.1s without — an 8.3× wall-
                # clock speedup. The earlier "speed_lora incompatible
                # with Animate" hypothesis was wrong; failures pre-PR
                # #38 were the conditioning/CLIP-shape bug, not the LoRA.
                # Default ON — Grant's screenwriter workflow doesn't
                # need the 14 min/shot baseline when 1.7 min/shot
                # produces equivalent character ID + motion quality.
                "speed_lora_candidates": [
                    "wan2.2_lightx2v_4step_rank64_HIGH_fp16.safetensors",
                    "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
                ],
                "speed_lora_strength": 1.0,
                "speed_lora_steps": 4,
                "speed_lora_cfg": 1.0,
                "speed_lora_enabled_by_default": True,
            },
        ),
        # ============================================================
        # ALTERNATE CINEMATIC — LTX-2 19B (slower, larger, fallback)
        # Note: tight on 32 GB VRAM; first-load involves weight staging.
        # ============================================================
        "ltx2-19b-dev-fp8": VideoModel(
            id="ltx2-19b-dev-fp8",
            name="LTX-2 19B Dev (FP8)",
            version="2.0",
            cost_per_second=0.0,
            supports_text_to_video=True,
            supports_image_to_video=False,
            max_duration=5.0,
            default_fps=24,
            default_steps=30,
            default_cfg_scale=7.0,
            extra_params={
                "checkpoint_file": "ltx-2-19b-dev-fp8.safetensors",
                "gemma_file": "gemma/model-00001-of-00005.safetensors",
                "max_token_length": 256,
                "sampler": "euler",
                "scheduler": "normal",
                "expected_vram_gb": 28,
                # LTX-2 19B + Gemma encoder is the heaviest cold load
                # in the stack — be generous.
                "expected_timeout_seconds": 1500,
            },
        ),
        # ============================================================
        # LEGACY STUBS (kept for backwards compat; require their own
        # weights to be installed before they will work).
        # ============================================================
        "animatediff-v3": VideoModel(
            id="animatediff-v3",
            name="AnimateDiff v3 (legacy)",
            version="3.0",
            cost_per_second=0.0,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=8,
            default_steps=25,
            default_cfg_scale=7.5,
            extra_params={"motion_module": "mm_sd_v15_v3"},
        ),
        "svd-xt": VideoModel(
            id="svd-xt",
            name="Stable Video Diffusion XT (legacy)",
            version="1.1",
            cost_per_second=0.0,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=14,
            default_steps=25,
            default_cfg_scale=2.5,
        ),
    }

    DEFAULT_MODEL = "wan22-t2v-14b-fp8"
    POLL_INTERVAL = 1.0  # seconds
    POLL_TIMEOUT = 600.0  # 10 minutes

    def __init__(
        self,
        comfyui_url: str = "http://127.0.0.1:8188",
        model_id: str | None = None,
        output_format: str = "mp4",
    ) -> None:
        """Initialize ComfyUI provider.

        Args:
            comfyui_url: URL of the ComfyUI instance
            model_id: Default model to use
            output_format: Output video format (mp4, webm, gif)
        """
        self.comfyui_url = comfyui_url.rstrip("/")
        self.model_id = model_id or self.DEFAULT_MODEL
        self.output_format = output_format
        self._client_id = str(uuid.uuid4())
        self._active_prompts: dict[str, str] = {}  # shot_id -> prompt_id

    @property
    def name(self) -> str:
        return "ComfyUI Local"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.CUSTOM

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            features=[
                ProviderFeature.TEXT_TO_VIDEO,
                ProviderFeature.IMAGE_TO_VIDEO,
                ProviderFeature.CHARACTER_CONSISTENCY,  # via Wan Animate
                ProviderFeature.LORA_SUPPORT,
                ProviderFeature.CONTROLNET,
            ],
            min_width=256,
            max_width=1920,
            min_height=256,
            max_height=1080,
            min_duration=0.5,
            max_duration=10.0,
            supported_fps=[8, 12, 14, 16, 24, 30],
            max_concurrent_jobs=1,  # Usually limited by VRAM
            supports_cost_estimation=True,
        )

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Generate video using ComfyUI."""
        try:
            import httpx
        except ImportError:
            return GenerationResult(
                success=False,
                error_message="httpx package not installed. Run: pip install httpx",
                error_code="MISSING_DEPENDENCY",
            )

        model = self.get_model(request.extra_params.get("model_id", self.model_id))
        if not model:
            model = self.MODELS[self.DEFAULT_MODEL]

        try:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=5,
                        message="Connecting to ComfyUI",
                        stage="preparing",
                    )
                )

            # Check ComfyUI availability
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    resp = await client.get(f"{self.comfyui_url}/system_stats")
                    if resp.status_code != 200:
                        return GenerationResult(
                            success=False,
                            error_message=f"ComfyUI not responding (status {resp.status_code})",
                            error_code="COMFYUI_UNAVAILABLE",
                        )
                except httpx.ConnectError:
                    return GenerationResult(
                        success=False,
                        error_message=f"Cannot connect to ComfyUI at {self.comfyui_url}",
                        error_code="CONNECTION_FAILED",
                    )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message="Building workflow",
                        stage="preparing",
                    )
                )

            # Build workflow based on model
            workflow = self._build_workflow(request, model)

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=15,
                        message="Submitting to ComfyUI queue",
                        stage="submitting",
                    )
                )

            # Submit workflow
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.comfyui_url}/prompt",
                    json={
                        "prompt": workflow,
                        "client_id": self._client_id,
                    },
                )

                if resp.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"Failed to submit workflow: {resp.text}",
                        error_code="SUBMISSION_FAILED",
                    )

                result = resp.json()
                prompt_id = result.get("prompt_id")

                if not prompt_id:
                    return GenerationResult(
                        success=False,
                        error_message="No prompt_id returned from ComfyUI",
                        error_code="NO_PROMPT_ID",
                    )

            self._active_prompts[str(request.shot_id)] = prompt_id

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=20,
                        message=f"Queued (ID: {prompt_id[:8]}...)",
                        stage="queued",
                    )
                )

            # Poll for completion, with a per-model timeout. Models that run
            # on borderline VRAM (e.g. Wan Animate BF16 on a 32 GB card)
            # need longer than the 10-minute default because their weight-
            # staging is slow. Override priority:
            #   request.extra_params['expected_timeout_seconds']
            #     > model.extra_params['expected_timeout_seconds']
            #     > self.POLL_TIMEOUT
            poll_timeout = self._p(request, model, "expected_timeout_seconds", self.POLL_TIMEOUT)
            output_files = await self._poll_completion(
                prompt_id,
                request.shot_id,
                progress_callback,
                timeout=float(poll_timeout),
            )

            if not output_files:
                return GenerationResult(
                    success=False,
                    error_message="No output files generated",
                    error_code="NO_OUTPUT",
                )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=90,
                        message="Downloading output",
                        stage="downloading",
                    )
                )

            # Download and save output
            settings = get_settings()
            shot_dir = settings.output_dir / "shots" / str(request.shot_id)
            shot_dir.mkdir(parents=True, exist_ok=True)

            output_path = await self._download_output(
                output_files[0],
                shot_dir / f"output.{self.output_format}",
            )

            # Generate thumbnail
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=95,
                        message="Generating thumbnail",
                        stage="thumbnail",
                    )
                )

            thumbnail_path = await self._generate_thumbnail(
                Path(output_path),
                shot_dir / "thumbnail.jpg",
            )

            # Cleanup
            self._active_prompts.pop(str(request.shot_id), None)

            return GenerationResult(
                success=True,
                output_path=f"shots/{request.shot_id}/output.{self.output_format}",
                thumbnail_path=f"shots/{request.shot_id}/thumbnail.jpg" if thumbnail_path else None,
                duration_seconds=request.duration_seconds,
                cost_usd=0.0,  # Local = free
                metadata={
                    "model": model.id,
                    "model_name": model.name,
                    "provider": "comfyui",
                    "prompt_id": prompt_id,
                    "seed": request.seed,
                    "prompt": request.prompt[:200],
                    "comfyui_url": self.comfyui_url,
                },
            )

        except TimeoutError:
            self._active_prompts.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message="Generation timed out",
                error_code="TIMEOUT",
            )

        except Exception as e:
            logger.exception("ComfyUI generation failed")
            self._active_prompts.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    def _build_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
    ) -> dict[str, Any]:
        """Build a ComfyUI API-format workflow for the given model + request.

        Dispatches to a model-specific builder. The builders produce dicts in
        ComfyUI's API format ({node_id: {class_type, inputs}}) ready to POST
        to /prompt.

        Notes on resolution: Wan 2.2 expects width/height divisible by 16,
        and num_frames in (4k+1) — we round in each builder.
        """
        num_frames = int(request.duration_seconds * request.fps)
        # Wan-family wants (4k+1) frames so it can produce K full latent groups
        if model.id.startswith("wan22") or model.id == "wan22-animate-14b":
            num_frames = ((num_frames - 1) // 4) * 4 + 1

        if model.id == "wan22-t2v-14b-fp8":
            return self._build_wan22_t2v_workflow(request, model, num_frames)
        if model.id == "wan22-i2v-14b-fp8":
            return self._build_wan22_i2v_workflow(request, model, num_frames)
        if model.id == "wan22-animate-14b":
            return self._build_wan_animate_workflow(request, model, num_frames)
        if model.id == "ltx2-19b-dev-fp8":
            return self._build_ltx2_workflow(request, model, num_frames)

        # Legacy stubs:
        if model.id.startswith("animatediff"):
            return self._build_animatediff_workflow(request, model, num_frames)
        if model.id.startswith("svd"):
            return self._build_svd_workflow(request, model, num_frames)
        # Unknown model — fall back to the primary stack:
        return self._build_wan22_t2v_workflow(
            request,
            self.MODELS["wan22-t2v-14b-fp8"],
            num_frames,
        )

    def _build_animatediff_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
        num_frames: int,
    ) -> dict[str, Any]:
        """Build AnimateDiff workflow."""
        seed = request.seed or 42

        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            },
            "2": {
                "class_type": "ADE_LoadAnimateDiffModel",
                "inputs": {
                    "model_name": model.extra_params.get(
                        "motion_module", "mm_sd_v15_v3.safetensors"
                    ),
                },
            },
            "3": {
                "class_type": "ADE_ApplyAnimateDiffModel",
                "inputs": {
                    "model": ["1", 0],
                    "motion_model": ["2", 0],
                },
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["1", 1],
                    "text": request.prompt,
                },
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["1", 1],
                    "text": request.negative_prompt or "bad quality, blurry, distorted",
                },
            },
            "6": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": request.width,
                    "height": request.height,
                    "batch_size": num_frames,
                },
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["3", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0],
                    "seed": seed,
                    "steps": request.num_inference_steps or model.default_steps,
                    "cfg": request.guidance_scale or model.default_cfg_scale,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["1", 2],
                },
            },
            "9": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["8", 0],
                    "frame_rate": request.fps,
                    "loop_count": 0,
                    "filename_prefix": f"shot_{request.shot_id}",
                    "format": "video/h264-mp4",
                    "pingpong": False,
                    "save_output": True,
                },
            },
        }

    def _build_svd_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
        num_frames: int,
    ) -> dict[str, Any]:
        """Build Stable Video Diffusion workflow."""
        if not request.input_image_path:
            raise ValueError("SVD requires an input image")

        seed = request.seed or 42

        return {
            "1": {
                "class_type": "ImageOnlyCheckpointLoader",
                "inputs": {"ckpt_name": "svd_xt_1_1.safetensors"},
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {"image": request.input_image_path},
            },
            "3": {
                "class_type": "SVD_img2vid_Conditioning",
                "inputs": {
                    "clip_vision": ["1", 1],
                    "init_image": ["2", 0],
                    "vae": ["1", 2],
                    "width": request.width,
                    "height": request.height,
                    "video_frames": num_frames,
                    "motion_bucket_id": 127,
                    "fps": request.fps,
                    "augmentation_level": 0.0,
                },
            },
            "4": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["3", 0],
                    "negative": ["3", 1],
                    "latent_image": ["3", 2],
                    "seed": seed,
                    "steps": request.num_inference_steps or model.default_steps,
                    "cfg": request.guidance_scale or model.default_cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "karras",
                    "denoise": 1.0,
                },
            },
            "5": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["4", 0],
                    "vae": ["1", 2],
                },
            },
            "6": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["5", 0],
                    "frame_rate": request.fps,
                    "loop_count": 0,
                    "filename_prefix": f"shot_{request.shot_id}",
                    "format": "video/h264-mp4",
                    "save_output": True,
                },
            },
        }

    @staticmethod
    def _p(
        request: GenerationRequest,
        model: VideoModel,
        key: str,
        default: Any,
    ) -> Any:
        """Resolve a workflow parameter with this priority:
        request.extra_params[key]  >>  model.extra_params[key]  >>  default
        """
        if key in request.extra_params:
            return request.extra_params[key]
        if key in model.extra_params:
            return model.extra_params[key]
        return default

    def _fetch_available_models(self) -> dict[str, set]:
        """Query the live ComfyUI for which model files are actually loadable.

        Returns a dict keyed by ComfyUI node type (e.g. "WanVideoModelLoader",
        "CheckpointLoaderSimple") whose values are the set of filenames that
        that node's dropdown would show.

        Cached on the provider instance for the lifetime of the process. If
        ComfyUI is unreachable, returns an empty cache and we fall back to
        whatever the registry says — letting ComfyUI itself reject invalid
        names with a clear error, instead of us silently misrouting.

        Why this exists: at registration time we may want to promise a
        preferred quantization (e.g. Kijai's FP8 Wan-Animate) before the
        file has actually been downloaded. This method lets us pick whichever
        candidate is genuinely on disk right now.
        """
        if hasattr(self, "_available_models_cache"):
            return self._available_models_cache
        try:
            import httpx

            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.comfyui_url}/api/object_info")
                if resp.status_code != 200:
                    return {}
                oi = resp.json()
        except Exception as e:
            logger.warning(f"Could not fetch ComfyUI object_info: {e}")
            return {}

        out: dict[str, set] = {}
        # Each loader's first-arg dropdown is the canonical "what files exist"
        for node_name, spec in oi.items():
            inputs = (spec.get("input") or {}).get("required") or {}
            for _input_name, input_spec in inputs.items():
                if not isinstance(input_spec, list) or not input_spec:
                    continue
                choices = input_spec[0]
                if (
                    isinstance(choices, list)
                    and choices
                    and all(isinstance(c, str) for c in choices)
                ):
                    # This is an enum/dropdown — record its options.
                    out.setdefault(node_name, set()).update(choices)
        self._available_models_cache = out
        return out

    @staticmethod
    def _infer_wan_quantization(filename: str) -> str:
        """Pick the right WanVideoModelLoader `quantization` enum value for
        a given model filename. The loader will refuse mismatched combos
        (e.g. fp8_e4m3fn_scaled on a BF16 weight raises ValueError).

        Conservative defaults: anything we can't classify reads as
        ``disabled``, which works for BF16/FP16 weights.
        """
        f = filename.lower()
        if "fp8_e4m3fn_scaled" in f or "fp8_scaled" in f:
            return "fp8_e4m3fn_scaled"
        if "fp8_e5m2_scaled" in f:
            return "fp8_e5m2_scaled"
        if "fp8_e4m3fn" in f:
            return "fp8_e4m3fn"
        if "fp8_e5m2" in f:
            return "fp8_e5m2"
        # bf16 / fp16 / unquantized
        return "disabled"

    def _resolve_first_available(self, node_type: str, candidates: list[str]) -> str | None:
        """Return the first candidate filename that ComfyUI's node loader of
        type ``node_type`` actually has. If ComfyUI is unreachable or none of
        the candidates are present, falls back to the FIRST candidate (so
        ComfyUI itself surfaces the missing-file error cleanly).
        """
        available = self._fetch_available_models().get(node_type, set())
        for candidate in candidates:
            if candidate and candidate in available:
                return candidate
        # Last resort: return the first non-falsy candidate so the error
        # surfaces with a real filename instead of None.
        for candidate in candidates:
            if candidate:
                return candidate
        return None

    @staticmethod
    def _should_use_speed_lora(request: GenerationRequest, model: VideoModel) -> bool:
        """Return True when the workflow should inject a Lightx2v-style
        distillation LoRA for ~7× sampling speedup.

        Override priority (matches ``_p``):
            request.extra_params['speed_lora']
              > model.extra_params['speed_lora_enabled_by_default']
              > False
        """
        if "speed_lora" in request.extra_params:
            return bool(request.extra_params["speed_lora"])
        return bool(model.extra_params.get("speed_lora_enabled_by_default", False))

    def _resolve_speed_lora_file(
        self,
        request: GenerationRequest,
        model: VideoModel,
    ) -> str | None:
        """Pick the LoRA filename to use, preferring an explicit override.

        Returns None when no candidate exists on disk and no override
        was supplied — callers should treat that as "skip the LoRA".
        """
        override = request.extra_params.get("speed_lora_file")
        if override:
            return override
        candidates = list(model.extra_params.get("speed_lora_candidates") or [])
        if not candidates:
            return None
        resolved = self._resolve_first_available("WanVideoLoraSelect", candidates)
        # _resolve_first_available falls back to the first candidate even
        # when ComfyUI is unreachable; that's fine — ComfyUI itself will
        # surface a clean missing-file error if it doesn't exist.
        return resolved

    @staticmethod
    def _extract_reference_image(request: GenerationRequest) -> str | None:
        """Get the first usable character-reference image path from a request.

        Looks in this order:
          1. request.character_references[*]['reference_image_path']
          2. request.character_references[*]['image_path']
          3. request.input_image_path
        Returns None if nothing is found.
        """
        for ref in request.character_references or []:
            if isinstance(ref, dict):
                p = ref.get("reference_image_path") or ref.get("image_path")
                if p:
                    return p
        return request.input_image_path

    # ============================================================
    # WAN 2.2 T2V — primary text-to-video stack (FP8, 14B)
    # Validated 2026-05-13 against local ComfyUI; produces real mp4.
    # Node graph mirrors /opt/ai/workflows/api/wan22_t2v.json.
    # ============================================================
    def _build_wan22_t2v_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
        num_frames: int,
    ) -> dict[str, Any]:
        """Build Wan 2.2 T2V (14B FP8) workflow.

        Uses the Kijai WanVideoWrapper custom nodes:
          ModelLoader → T5TextEncoder → TextEncode → VAELoader →
          EmptyEmbeds → Sampler → Decode → VideoCombine
        """
        seed = request.seed if request.seed is not None else 42
        params = model.extra_params

        return {
            "1": {
                "class_type": "WanVideoModelLoader",
                "inputs": {
                    "model": params["model_file"],
                    "base_precision": "fp16",
                    "quantization": self._infer_wan_quantization(params["model_file"]),
                    "load_device": "main_device",
                },
            },
            "2": {
                "class_type": "LoadWanVideoT5TextEncoder",
                "inputs": {
                    "model_name": params["text_encoder_file"],
                    "precision": "bf16",
                    "load_device": "offload_device",
                    "quantization": "disabled",
                },
            },
            "3": {
                "class_type": "WanVideoTextEncode",
                "inputs": {
                    "positive_prompt": request.prompt,
                    "negative_prompt": (
                        request.negative_prompt
                        or "ugly, blurry, low quality, watermark, text, distorted"
                    ),
                    "t5": ["2", 0],
                    "force_offload": True,
                    "use_disk_cache": False,
                    "device": "gpu",
                },
            },
            "4": {
                "class_type": "WanVideoVAELoader",
                "inputs": {
                    "model_name": params["vae_file"],
                    "precision": "bf16",
                },
            },
            "5": {
                "class_type": "WanVideoEmptyEmbeds",
                "inputs": {
                    "width": request.width,
                    "height": request.height,
                    "num_frames": num_frames,
                },
            },
            "6": {
                "class_type": "WanVideoSampler",
                "inputs": {
                    "model": ["1", 0],
                    "image_embeds": ["5", 0],
                    "text_embeds": ["3", 0],
                    "steps": request.num_inference_steps or model.default_steps,
                    "cfg": request.guidance_scale or model.default_cfg_scale,
                    "shift": self._p(request, model, "shift", 5.0),
                    "seed": seed,
                    "force_offload": True,
                    "scheduler": self._p(request, model, "scheduler", "unipc"),
                    "riflex_freq_index": 0,
                },
            },
            "7": {
                "class_type": "WanVideoDecode",
                "inputs": {
                    "vae": ["4", 0],
                    "samples": ["6", 0],
                    "enable_vae_tiling": True,
                    "tile_x": self._p(request, model, "tile_x", 272),
                    "tile_y": self._p(request, model, "tile_y", 272),
                    "tile_stride_x": self._p(request, model, "tile_stride_x", 144),
                    "tile_stride_y": self._p(request, model, "tile_stride_y", 128),
                },
            },
            "8": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["7", 0],
                    "frame_rate": float(request.fps),
                    "loop_count": 0,
                    "filename_prefix": f"shot_{request.shot_id}",
                    "format": "video/nvenc_av1-mp4",
                    "pingpong": False,
                    "save_output": True,
                },
            },
        }

    # ============================================================
    # WAN 2.2 I2V — image-to-video (FP8, 14B). Needs a starter image.
    # ============================================================
    def _build_wan22_i2v_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
        num_frames: int,
    ) -> dict[str, Any]:
        """Build Wan 2.2 I2V workflow.

        Uses CLIP-Vision to encode the input image, then I2V sampling.
        Requires `request.input_image_path` to be a filename already in
        ComfyUI's input directory (the provider's caller is expected to
        upload via /upload/image first if working from an arbitrary path).
        """
        seed = request.seed if request.seed is not None else 42
        params = model.extra_params
        image_name = request.input_image_path or "input.png"

        return {
            "1": {
                "class_type": "WanVideoModelLoader",
                "inputs": {
                    "model": params["model_file"],
                    "base_precision": "fp16",
                    "quantization": self._infer_wan_quantization(params["model_file"]),
                    "load_device": "main_device",
                },
            },
            "2": {
                "class_type": "LoadWanVideoT5TextEncoder",
                "inputs": {
                    "model_name": params["text_encoder_file"],
                    "precision": "bf16",
                    "load_device": "offload_device",
                    "quantization": "disabled",
                },
            },
            "3": {
                "class_type": "WanVideoTextEncode",
                "inputs": {
                    "positive_prompt": request.prompt,
                    "negative_prompt": (
                        request.negative_prompt
                        or "ugly, blurry, low quality, watermark, text, distorted"
                    ),
                    "t5": ["2", 0],
                    "force_offload": True,
                    "use_disk_cache": False,
                    "device": "gpu",
                },
            },
            "4": {
                "class_type": "WanVideoVAELoader",
                "inputs": {
                    "model_name": params["vae_file"],
                    "precision": "bf16",
                },
            },
            "5": {
                "class_type": "LoadImage",
                "inputs": {"image": image_name},
            },
            "6": {
                "class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": params["clip_vision_file"]},
            },
            "7": {
                "class_type": "WanVideoImageClipEncode",
                "inputs": {
                    "clip_vision": ["6", 0],
                    "image": ["5", 0],
                    "vae": ["4", 0],
                    "generation_width": request.width,
                    "generation_height": request.height,
                    "num_frames": num_frames,
                },
            },
            "8": {
                "class_type": "WanVideoSampler",
                "inputs": {
                    "model": ["1", 0],
                    "image_embeds": ["7", 0],
                    "text_embeds": ["3", 0],
                    "steps": request.num_inference_steps or model.default_steps,
                    "cfg": request.guidance_scale or model.default_cfg_scale,
                    "shift": self._p(request, model, "shift", 5.0),
                    "seed": seed,
                    "force_offload": True,
                    "scheduler": self._p(request, model, "scheduler", "unipc"),
                    "riflex_freq_index": 0,
                },
            },
            "9": {
                "class_type": "WanVideoDecode",
                "inputs": {
                    "vae": ["4", 0],
                    "samples": ["8", 0],
                    "enable_vae_tiling": True,
                    "tile_x": self._p(request, model, "tile_x", 272),
                    "tile_y": self._p(request, model, "tile_y", 272),
                    "tile_stride_x": self._p(request, model, "tile_stride_x", 144),
                    "tile_stride_y": self._p(request, model, "tile_stride_y", 128),
                },
            },
            "10": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["9", 0],
                    "frame_rate": float(request.fps),
                    "loop_count": 0,
                    "filename_prefix": f"shot_{request.shot_id}",
                    "format": "video/nvenc_av1-mp4",
                    "pingpong": False,
                    "save_output": True,
                },
            },
        }

    # ============================================================
    # WAN 2.2 ANIMATE — character-consistency. Takes a reference
    # image of the character (from request.character_references or
    # request.input_image_path). Identity is preserved across the shot.
    # ============================================================
    def _build_wan_animate_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
        num_frames: int,
    ) -> dict[str, Any]:
        """Build Wan 2.2 Animate workflow for ID-preserving generation.

        Reference image is required. Priority order:
          1. request.character_references[*]['reference_image_path']
          2. request.character_references[*]['image_path']
          3. request.input_image_path

        Prefers the FP8 model weight if ``model_file_fp8`` is registered
        in the model's extra_params, falling back to the (larger) BF16
        weight. Keep this builder structurally independent of the I2V
        builder so changes there don't silently break Animate.

        Conditioning chain: Animate's sampler expects a
        ``WANVIDIMAGE_EMBEDS`` value that came from
        ``WanVideoAnimateEmbeds``, NOT from the I2V
        ``WanVideoImageClipEncode``. The Animate compound embed bundles
        VAE-encoded ref/pose/face/bg/mask alongside the CLIP-vision
        embedding so the transformer's first-block LayerNorm sees the
        shape it was trained on. Reading ``WanVideoImageClipEncode``'s
        output into Animate's sampler crashes inside
        ``wanvideo/modules/model.py`` with ``Given
        normalized_shape=[1280], expected ...``. Source-of-truth for the
        graph: Kijai's
        ``ComfyUI-WanVideoWrapper/example_workflows/wanvideo_WanAnimate_example_01.json``.

        Minimal-conditioning use case (text + ref → video, no source
        motion video): pass only ``ref_images`` to
        ``WanVideoAnimateEmbeds``; pose_images, face_images, bg_images
        and mask are all genuinely optional in
        ``WanVideoAnimateEmbeds.process()`` (None-checked), and the
        background latent is auto-filled with zeros when bg_images is
        None.

        Raises:
            ValueError: when no reference image is supplied via any source.
        """
        ref_image = self._extract_reference_image(request)
        if not ref_image:
            raise ValueError(
                "Wan Animate requires a character reference image. Provide "
                "request.character_references[0]['reference_image_path'] or "
                "request.input_image_path."
            )

        seed = request.seed if request.seed is not None else 42
        params = model.extra_params
        # Pick whichever Animate weight ComfyUI actually has on disk. The
        # Kijai FP8 quant (~14 GB) is preferred when present because the BF16
        # weight is 32 GB and tight on a 32 GB-VRAM card, but we fall back to
        # BF16 cleanly when the FP8 hasn't been downloaded yet.
        animate_weight = (
            self._resolve_first_available(
                "WanVideoModelLoader",
                [params.get("model_file_fp8"), params["model_file"]],
            )
            or params["model_file"]
        )

        # Lightx2v 4-step distillation LoRA. When enabled this attaches a
        # WanVideoLoraSelect node and feeds its WANVIDLORA output into the
        # ModelLoader's optional `lora` input. The sampler then runs in
        # ~4 steps instead of 30, an ~7× speedup for the sampling phase.
        # Weight-load time is unchanged.
        use_speed_lora = self._should_use_speed_lora(request, model)
        speed_lora_file = self._resolve_speed_lora_file(request, model) if use_speed_lora else None
        speed_lora_active = use_speed_lora and bool(speed_lora_file)

        model_loader_inputs: dict[str, Any] = {
            "model": animate_weight,
            "base_precision": "fp16",
            "quantization": self._infer_wan_quantization(animate_weight),
            "load_device": self._p(request, model, "load_device", "main_device"),
        }
        if speed_lora_active:
            # WanVideoLoraSelect → ModelLoader.lora (a WANVIDLORA link).
            model_loader_inputs["lora"] = ["11", 0]

        # Block-swap is required for Animate BF16 to load on a 32 GB card.
        # When blocks_to_swap > 0, attach a WanVideoBlockSwap node and wire
        # its BLOCKSWAPARGS into ModelLoader.block_swap_args. The model can
        # then load with ~half its transformer blocks resident on CPU.
        # Set blocks_to_swap=0 to disable (only safe for FP8 weights or
        # larger-VRAM cards).
        blocks_to_swap = int(self._p(request, model, "blocks_to_swap", 0))
        block_swap_active = blocks_to_swap > 0
        if block_swap_active:
            model_loader_inputs["block_swap_args"] = ["12", 0]

        # When the speed LoRA is active, replace the model's documented
        # defaults with Lightx2v's calibrated 4 steps / cfg≈1.0. Anything
        # else (e.g. cfg=6) will silently produce mush — Lightx2v expects
        # near-zero CFG. An explicit num_inference_steps / guidance_scale
        # on the request still wins, mirroring T2V/I2V semantics.
        if speed_lora_active:
            sampler_steps = request.num_inference_steps or self._p(
                request, model, "speed_lora_steps", 4
            )
            sampler_cfg = request.guidance_scale or self._p(request, model, "speed_lora_cfg", 1.0)
        else:
            sampler_steps = request.num_inference_steps or model.default_steps
            sampler_cfg = request.guidance_scale or model.default_cfg_scale

        workflow: dict[str, Any] = {
            "1": {
                "class_type": "WanVideoModelLoader",
                "inputs": model_loader_inputs,
            },
            "2": {
                "class_type": "LoadWanVideoT5TextEncoder",
                "inputs": {
                    "model_name": params["text_encoder_file"],
                    "precision": "bf16",
                    "load_device": "offload_device",
                    "quantization": "disabled",
                },
            },
            "3": {
                "class_type": "WanVideoTextEncode",
                "inputs": {
                    "positive_prompt": request.prompt,
                    "negative_prompt": (
                        request.negative_prompt
                        or "ugly, blurry, low quality, watermark, text, distorted"
                    ),
                    "t5": ["2", 0],
                    "force_offload": True,
                    "use_disk_cache": False,
                    "device": "gpu",
                },
            },
            "4": {
                "class_type": "WanVideoVAELoader",
                "inputs": {
                    "model_name": params["vae_file"],
                    "precision": "bf16",
                },
            },
            "5": {
                "class_type": "LoadImage",
                "inputs": {"image": ref_image},
            },
            "6": {
                "class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": params["clip_vision_file"]},
            },
            "7": {
                "class_type": "WanVideoClipVisionEncode",
                "inputs": {
                    "clip_vision": ["6", 0],
                    "image_1": ["5", 0],
                    "strength_1": float(self._p(request, model, "clip_vision_strength", 1.0)),
                    "strength_2": float(self._p(request, model, "clip_vision_strength", 1.0)),
                    "crop": "center",
                    "combine_embeds": "average",
                    "force_offload": True,
                },
            },
            "14": {
                "class_type": "WanVideoAnimateEmbeds",
                "inputs": {
                    "vae": ["4", 0],
                    "clip_embeds": ["7", 0],
                    "ref_images": ["5", 0],
                    "width": request.width,
                    "height": request.height,
                    "num_frames": num_frames,
                    "force_offload": True,
                    "frame_window_size": int(self._p(request, model, "frame_window_size", 77)),
                    "colormatch": "disabled",
                    "pose_strength": float(self._p(request, model, "pose_strength", 1.0)),
                    "face_strength": float(self._p(request, model, "face_strength", 1.0)),
                },
            },
            "8": {
                "class_type": "WanVideoSampler",
                "inputs": {
                    "model": ["1", 0],
                    "image_embeds": ["14", 0],
                    "text_embeds": ["3", 0],
                    "steps": sampler_steps,
                    "cfg": sampler_cfg,
                    "shift": self._p(request, model, "shift", 5.0),
                    "seed": seed,
                    "force_offload": True,
                    "scheduler": self._p(request, model, "scheduler", "unipc"),
                    "riflex_freq_index": 0,
                },
            },
            "9": {
                "class_type": "WanVideoDecode",
                "inputs": {
                    "vae": ["4", 0],
                    "samples": ["8", 0],
                    "enable_vae_tiling": True,
                    "tile_x": self._p(request, model, "tile_x", 272),
                    "tile_y": self._p(request, model, "tile_y", 272),
                    "tile_stride_x": self._p(request, model, "tile_stride_x", 144),
                    "tile_stride_y": self._p(request, model, "tile_stride_y", 128),
                },
            },
            "10": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["9", 0],
                    "frame_rate": float(request.fps),
                    "loop_count": 0,
                    "filename_prefix": f"shot_{request.shot_id}",
                    "format": "video/nvenc_av1-mp4",
                    "pingpong": False,
                    "save_output": True,
                },
            },
        }

        if speed_lora_active:
            workflow["11"] = {
                "class_type": "WanVideoLoraSelect",
                "inputs": {
                    "lora": speed_lora_file,
                    "strength": float(self._p(request, model, "speed_lora_strength", 1.0)),
                },
            }

        if block_swap_active:
            # We pass ALL the WanVideoBlockSwap inputs explicitly — including
            # the "optional" ones — because Kijai's loader does not always
            # propagate ComfyUI defaults: leaving vace_blocks_to_swap unset
            # crashes the sampler at wanvideo/modules/model.py:2068 with
            # ``'>' not supported between instances of 'NoneType' and 'int'``.
            # Validated 2026-05-13. Pass zeros for the VACE/prefetch knobs
            # so the comparison sees real ints.
            workflow["12"] = {
                "class_type": "WanVideoBlockSwap",
                "inputs": {
                    "blocks_to_swap": blocks_to_swap,
                    "offload_img_emb": bool(self._p(request, model, "offload_img_emb", False)),
                    "offload_txt_emb": bool(self._p(request, model, "offload_txt_emb", False)),
                    "use_non_blocking": bool(self._p(request, model, "use_non_blocking", False)),
                    "vace_blocks_to_swap": int(self._p(request, model, "vace_blocks_to_swap", 0)),
                    "prefetch_blocks": int(self._p(request, model, "prefetch_blocks", 0)),
                    "block_swap_debug": bool(self._p(request, model, "block_swap_debug", False)),
                },
            }

        return workflow

    # ============================================================
    # LTX-2 19B Dev (FP8) — alternate cinematic. Slower first-load on
    # 32 GB VRAM (model is 26 GB FP8 + Gemma encoder + activations).
    # ============================================================
    def _build_ltx2_workflow(
        self,
        request: GenerationRequest,
        model: VideoModel,
        num_frames: int,
    ) -> dict[str, Any]:
        """Build LTX-2 19B Dev workflow using Lightricks Gemma encoder."""
        seed = request.seed if request.seed is not None else 42
        params = model.extra_params

        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": params["checkpoint_file"]},
            },
            "2": {
                "class_type": "LTXVGemmaCLIPModelLoader",
                "inputs": {
                    "gemma_path": params["gemma_file"],
                    "ltxv_path": params["checkpoint_file"],
                    "max_length": params.get("max_token_length", 256),
                },
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 0],
                    "text": request.prompt,
                },
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 0],
                    "text": (
                        request.negative_prompt
                        or "ugly, blurry, low quality, watermark, text, distorted"
                    ),
                },
            },
            "5": {
                "class_type": "LTXVConditioning",
                "inputs": {
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "frame_rate": float(request.fps),
                },
            },
            "6": {
                "class_type": "EmptyLTXVLatentVideo",
                "inputs": {
                    "width": request.width,
                    "height": request.height,
                    "length": num_frames,
                    "batch_size": 1,
                },
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "seed": seed,
                    "steps": request.num_inference_steps or model.default_steps,
                    "cfg": request.guidance_scale or model.default_cfg_scale,
                    "sampler_name": params.get("sampler", "euler"),
                    "scheduler": params.get("scheduler", "normal"),
                    "positive": ["5", 0],
                    "negative": ["5", 1],
                    "latent_image": ["6", 0],
                    "denoise": 1.0,
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["1", 2],
                },
            },
            "9": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["8", 0],
                    "frame_rate": float(request.fps),
                    "loop_count": 0,
                    "filename_prefix": f"shot_{request.shot_id}",
                    "format": "video/nvenc_av1-mp4",
                    "pingpong": False,
                    "save_output": True,
                },
            },
        }

    async def _poll_completion(
        self,
        prompt_id: str,
        shot_id: Any,
        progress_callback: ProgressCallback | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Poll ComfyUI for workflow completion.

        Args:
            prompt_id: ComfyUI's prompt UUID.
            shot_id: SceneMachine's shot UUID, for progress callbacks.
            progress_callback: Async callable for progress updates.
            timeout: Hard ceiling in seconds. Defaults to ``self.POLL_TIMEOUT``
                (10 min). Wan-Animate-style borderline-VRAM models can
                exceed 10 min just on the weight-staging step; pass a
                larger value (e.g. 1800) for those.
        """
        import httpx

        effective_timeout = timeout if timeout is not None else self.POLL_TIMEOUT
        elapsed = 0.0
        last_progress = 20

        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < effective_timeout:
                # Check history for completion
                resp = await client.get(f"{self.comfyui_url}/history/{prompt_id}")

                if resp.status_code == 200:
                    history = resp.json()

                    if prompt_id in history:
                        prompt_data = history[prompt_id]

                        # Check for errors
                        if prompt_data.get("status", {}).get("status_str") == "error":
                            messages = prompt_data.get("status", {}).get("messages", [])
                            error_msg = "; ".join(str(m) for m in messages)
                            raise Exception(f"ComfyUI workflow error: {error_msg}")

                        # Check for outputs
                        outputs = prompt_data.get("outputs", {})
                        for _node_id, node_output in outputs.items():
                            if "gifs" in node_output:
                                return node_output["gifs"]
                            if "videos" in node_output:
                                return node_output["videos"]
                            if "images" in node_output:
                                # Fallback to image sequence
                                return node_output["images"]

                # Check queue status for progress
                queue_resp = await client.get(f"{self.comfyui_url}/queue")
                if queue_resp.status_code == 200:
                    queue = queue_resp.json()
                    running = queue.get("queue_running", [])

                    # Find our prompt in running queue
                    for item in running:
                        if item[1] == prompt_id:
                            # Estimate progress based on time
                            progress = min(85, 20 + int(elapsed / effective_timeout * 65))
                            if progress > last_progress and progress_callback:
                                await progress_callback(
                                    GenerationProgress(
                                        job_id=shot_id,
                                        percent=progress,
                                        message="Generating video...",
                                        stage="generating",
                                    )
                                )
                                last_progress = progress
                            break

                await asyncio.sleep(self.POLL_INTERVAL)
                elapsed += self.POLL_INTERVAL

        raise TimeoutError("ComfyUI workflow polling timed out")

    async def _download_output(
        self,
        file_info: dict[str, Any],
        output_path: Path,
    ) -> str:
        """Download output file from ComfyUI."""
        import httpx

        filename = file_info.get("filename")
        subfolder = file_info.get("subfolder", "")
        file_type = file_info.get("type", "output")

        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": file_type,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{self.comfyui_url}/view", params=params)
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

        return str(output_path)

    async def _generate_thumbnail(
        self,
        video_path: Path,
        thumbnail_path: Path,
    ) -> str | None:
        """Generate thumbnail from video using ffmpeg."""
        if not video_path.exists():
            return None

        try:
            from scenemachine.utils.ffmpeg import get_ffmpeg

            ffmpeg = get_ffmpeg()
            await ffmpeg.extract_frame(
                video_path=video_path,
                output_path=thumbnail_path,
                timestamp=1.0,
                quality=2,
            )

            if thumbnail_path.exists():
                return str(thumbnail_path)
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        return None

    async def check_availability(self) -> bool:
        """Check if ComfyUI is available."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.comfyui_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    async def check_health(self) -> ProviderHealth:
        """Detailed health check for ComfyUI."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get system stats
                resp = await client.get(f"{self.comfyui_url}/system_stats")
                if resp.status_code != 200:
                    return ProviderHealth(
                        available=False,
                        message=f"ComfyUI returned status {resp.status_code}",
                        error_code="BAD_STATUS",
                    )

                resp.json()

                # Get queue info
                queue_resp = await client.get(f"{self.comfyui_url}/queue")
                queue_length = 0
                if queue_resp.status_code == 200:
                    queue = queue_resp.json()
                    queue_length = len(queue.get("queue_pending", []))

                return ProviderHealth(
                    available=True,
                    message="ComfyUI is running",
                    latency_ms=None,  # Would need to measure
                    models_available=len(self.MODELS),
                    queue_length=queue_length,
                )

        except Exception as e:
            return ProviderHealth(
                available=False,
                message=f"Cannot connect to ComfyUI: {e}",
                error_code="CONNECTION_FAILED",
            )

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running workflow."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.comfyui_url}/interrupt",
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to cancel ComfyUI workflow: {e}")
            return False

    def estimate_cost(
        self,
        duration_seconds: float = 3.0,
        model_id: str | None = None,
    ) -> float:
        """Local generation is free (just electricity)."""
        return 0.0

    def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        return [
            {
                "id": model_id,
                "name": model.name,
                "cost_per_second": model.cost_per_second,
                "supports_text_to_video": model.supports_text_to_video,
                "supports_image_to_video": model.supports_image_to_video,
                "max_duration": model.max_duration,
                "default_fps": model.default_fps,
            }
            for model_id, model in self.MODELS.items()
        ]

    def get_model(self, model_id: str) -> VideoModel | None:
        """Get model by ID."""
        return self.MODELS.get(model_id)
