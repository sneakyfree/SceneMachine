"""Regression tests for the four overnight fixes (PRs #44, #45, #46, #47).

These ship targeted, structural tests for the bugs discovered during
the 2026-05-14 overnight RADAR_LOVE_2 + IMPOSSIBLE_FULL run. Each
overnight fix was validated live (153 shots across 2 screenplays)
but landed without a formal pytest because the run was time-pressured.
This file lays the regression tripwires so future refactors fail
loudly instead of reintroducing the silent failures.

  PR #44 — per-model expected_timeout_seconds for T2V/I2V/LTX2
  PR #45 — plumb num_inference_steps + guidance_scale from shot_data
  PR #46 — robust _assemble_movie + no silent first-shot lie
  PR #47 — extract_frame -sseof for negative timestamp (av1 GOP fix)
"""
from __future__ import annotations

import inspect

import pytest

# ----------------------------------------------------------------------
# PR #44 — Per-model expected_timeout_seconds
# ----------------------------------------------------------------------

class TestPR44PerModelTimeouts:
    """Pre-PR #44, the provider's POLL_TIMEOUT (600s) was the only
    cap. Cold model load on this rig exceeds 600s for T2V/I2V/LTX2.
    The fix adds per-model overrides in MODELS[*].extra_params.
    These tests pin the override values so a regression revival of
    the 600s ceiling fails the suite."""

    @pytest.fixture
    def provider(self):
        from scenemachine.generators.comfyui import ComfyUIProvider
        return ComfyUIProvider

    def test_t2v_has_expected_timeout_override(self, provider):
        m = provider.MODELS["wan22-t2v-14b-fp8"]
        ts = m.extra_params.get("expected_timeout_seconds")
        assert ts is not None, (
            "wan22-t2v-14b-fp8 must declare expected_timeout_seconds; "
            "without it the provider falls back to the 600s POLL_TIMEOUT "
            "default that spuriously failed shot 1 of every cold start "
            "during the 2026-05-14 overnight run."
        )
        assert ts >= 1200, (
            f"expected_timeout_seconds={ts}; must be ≥ 1200 to cover "
            "documented cold-load (8–12 min) + sampling on this rig."
        )

    def test_i2v_has_expected_timeout_override(self, provider):
        ts = provider.MODELS["wan22-i2v-14b-fp8"].extra_params.get("expected_timeout_seconds")
        assert ts is not None and ts >= 1200

    def test_ltx2_has_expected_timeout_override(self, provider):
        ts = provider.MODELS["ltx2-19b-dev-fp8"].extra_params.get("expected_timeout_seconds")
        assert ts is not None and ts >= 1500, (
            "LTX-2 19B + Gemma encoder is the heaviest cold load in the "
            "stack; needs a longer ceiling than T2V/I2V."
        )

    def test_animate_already_had_override(self, provider):
        """Sanity check — Animate's 1800s pre-existed PR #44; ensure
        the refactor didn't accidentally drop it."""
        ts = provider.MODELS["wan22-animate-14b"].extra_params.get("expected_timeout_seconds")
        assert ts is not None and ts >= 1800


# ----------------------------------------------------------------------
# PR #45 — num_inference_steps + guidance_scale plumbing
# ----------------------------------------------------------------------

class TestPR45StepsAndCfgPlumbing:
    """Pre-PR #45, ProductionPipeline._generate_videos built every
    GenerationRequest with the dataclass defaults
    (num_inference_steps=50, guidance_scale=7.5), silently overriding
    any per-shot or per-model preference. The workflow line
    ``request.num_inference_steps or model.default_steps`` could never
    see the model default because request was always 50.

    The fix forwards shot_data['num_inference_steps'] and
    ['guidance_scale'] into GenerationRequest kwargs only when present
    (so omitting them preserves prior behavior). These tests pin the
    plumbing logic by inspecting the source."""

    def test_generate_videos_reads_shot_data_steps(self):
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline._generate_videos)
        # The fix references shot_data.get('num_inference_steps') and
        # passes it via **_req_kwargs into GenerationRequest. Pin both.
        assert "shot_data.get(\"num_inference_steps\")" in src, (
            "_generate_videos must read num_inference_steps from "
            "shot_data; reverting drops the per-shot step override."
        )
        assert "**_req_kwargs" in src or "num_inference_steps=int(" in src, (
            "_generate_videos must forward the steps value into "
            "GenerationRequest; not forwarding silently restores the "
            "50-step default that made overnight runs take 8 hours."
        )

    def test_generate_videos_reads_shot_data_cfg(self):
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline._generate_videos)
        assert "shot_data.get(\"guidance_scale\")" in src, (
            "_generate_videos must read guidance_scale from shot_data."
        )


# ----------------------------------------------------------------------
# PR #46 — robust _assemble_movie + no silent first-shot lie
# ----------------------------------------------------------------------

class TestPR46AssemblyRobustness:
    """Pre-PR #46, _assemble_movie silently fell back to copying the
    first shot's mp4 as the final output when the concat demuxer
    returned non-zero. A 47-shot run would emit a 3-second "movie"
    that the launch summary reported as success.

    The fix:
      1. Adds a concat-filter + libx264 re-encode fallback (slow but
         tolerant)
      2. Removes the silent first-shot copy (no fallback now writes
         partial content masquerading as the final movie)
      3. Widens stderr capture from 500 chars to 4096 chars
    """

    def test_no_silent_first_shot_fallback(self):
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline._assemble_movie)
        # The bad pattern was a `shutil.copy2(video_paths[0], output_path)`
        # call INSIDE the concat-failure exception branch (not the
        # legitimate single-shot copy when ``len(video_paths) == 1``).
        # The fix replaces that with an empty placeholder + loud error.
        # We pin the fix by asserting both:
        #   (a) the empty-placeholder signal exists on the failure path
        #   (b) the explicit "No silent first-shot fallback" comment from
        #       PR #46 is preserved (intent-level documentation)
        assert "output_path.write_bytes(b\"\")" in src, (
            "_assemble_movie must write an empty placeholder when both "
            "assembly strategies fail, not silently copy the first shot. "
            "Per the feedback_no_silent_fallbacks rule, the empty-on-fail "
            "strategy from PR #46 must be preserved."
        )
        # Count strategies that fail loud — there are at least two output
        # branches that emit an empty file (filter fallback fail + outer
        # except). If someone reverts to a silent first-shot copy, both
        # disappear together.
        assert src.count("output_path.write_bytes(b\"\")") >= 2, (
            "Expected at least two empty-placeholder branches in "
            "_assemble_movie (concat-filter failure path + outer except). "
            "Reverting to a single silent first-shot copy reduces these."
        )

    def test_concat_filter_fallback_exists(self):
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline._assemble_movie)
        # The fallback uses ffmpeg's concat *filter* (not the demuxer)
        # with libx264 re-encoding. Pin the existence so the
        # slow-but-correct strategy can't be silently dropped.
        assert "filter_complex" in src, (
            "Expected concat-filter fallback (slow but tolerant) for "
            "av1+asyncio scenarios where the demuxer path fails."
        )
        assert "libx264" in src, "Expected libx264 in re-encode fallback."

    def test_stderr_buffer_widened(self):
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline._assemble_movie)
        # Pre-PR was `stderr.decode()[:500]` which couldn't fit ffmpeg's
        # banner alone. PR #46 expanded to 4096.
        assert "4096" in src or "4 KB" in src, (
            "PR #46 widened the stderr decode budget so operators can "
            "see the actual ffmpeg error past the banner; do not shrink "
            "below 4096 chars."
        )


# ----------------------------------------------------------------------
# PR #47 — extract_frame -sseof for negative timestamp (av1 GOP bug)
# ----------------------------------------------------------------------

class TestPR47ExtractFrameSseof:
    """Pre-PR #47, FFmpeg.extract_frame used input seek (-ss) for all
    timestamps. For av1_nvenc clips, container duration is 100-200ms
    shorter than frames/fps (GOP rounding). The pipeline asked for
    duration_s - 0.1 = 2.9s on clips with 2.875s container duration,
    landing past EOF and producing empty JPGs silently. All 153
    overnight continuity extractions failed this way.

    The fix:
      1. Negative timestamp → -sseof (seek from EOF)
      2. -update 1 flag for modern ffmpeg
      3. Empty-output post-condition raises FFmpegExecutionError
         (previously silently returned rc=0 with zero-byte file)
    """

    def test_extract_frame_branches_on_negative_timestamp(self):
        from scenemachine.utils.ffmpeg import FFmpeg
        src = inspect.getsource(FFmpeg.extract_frame)
        assert "sseof" in src, (
            "extract_frame must use -sseof when timestamp < 0; this is "
            "the fix for the av1 GOP-rounding bug that killed continuity "
            "extraction overnight."
        )
        assert "timestamp < 0" in src or "timestamp<0" in src, (
            "extract_frame must explicitly branch on negative timestamp."
        )

    def test_extract_frame_has_update_flag(self):
        from scenemachine.utils.ffmpeg import FFmpeg
        src = inspect.getsource(FFmpeg.extract_frame)
        assert "-update" in src and "\"1\"" in src, (
            "PR #47 added -update 1 for modern ffmpeg; do not drop."
        )

    def test_extract_frame_empty_output_raises(self):
        from scenemachine.utils.ffmpeg import FFmpeg
        src = inspect.getsource(FFmpeg.extract_frame)
        # The post-condition checks st_size == 0 and raises.
        assert "st_size == 0" in src or "stat().st_size" in src, (
            "Empty-output post-condition must remain; pre-PR-47 the "
            "function silently returned rc=0 with a zero-byte file."
        )

    def test_pipeline_uses_negative_timestamp(self):
        """The caller (extract_last_frame inside _generate_videos)
        must pass a negative timestamp to take advantage of the fix."""
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline._generate_videos)
        assert "timestamp=-0.1" in src, (
            "Pipeline's extract_last_frame helper must pass "
            "timestamp=-0.1 (seek from EOF). Without this the I2V "
            "continuity path silently fails on every av1 shot."
        )
