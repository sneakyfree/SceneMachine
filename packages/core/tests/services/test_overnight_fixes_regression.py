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
        assert 'shot_data.get("num_inference_steps")' in src, (
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
        assert 'shot_data.get("guidance_scale")' in src, (
            "_generate_videos must read guidance_scale from shot_data."
        )


# ----------------------------------------------------------------------
# PR #46 — robust _assemble_movie + no silent first-shot lie
# ----------------------------------------------------------------------


class TestPR46AssemblyRobustness:
    """Two-phase fix:

    Phase 1 (PR #46, 2026-05-14): removed the silent first-shot copy
    that emitted a 3-second "movie" passing as the final output. The
    replacement was a 0-byte placeholder + loud log error — a 50% fix.

    Phase 2 (this PR, 2026-05-20): replaces the 0-byte placeholder
    with raising ``AssemblyError``. The placeholder was indistinguishable
    from success at the file-existence layer — every downstream poller
    (wait_and_analyze.sh's MIN_MP4_BYTES guard was the only check that
    caught it) and the harness's RESULTS.json all reported a "real"
    final_mp4_path. Three incidents in 48h on 2026-05-19/20 all
    surfaced the same way (ComfyUI-down, ComfyUI VRAM leak, original
    first-shot fallback) despite different root causes.

    The Phase-2 fix:
      1. Removes ALL ``write_bytes(b"")`` placeholders
      2. Raises ``AssemblyError`` on: no completed shots, both
         strategies failed, generic exception during assembly
      3. Callers must catch — run_benchmark.py records the failure
         as ``assembly_error`` in the screenplay result dict
      4. Preserves the concat-filter + libx264 re-encode fallback
         from Phase 1 (slow-but-correct path stays)
      5. Preserves the 4096-char stderr capture from Phase 1
    """

    def test_no_silent_first_shot_fallback(self):
        from scenemachine.services.production_pipeline import ProductionPipeline

        src = inspect.getsource(ProductionPipeline._assemble_movie)
        # The original (pre-PR #46) bad pattern was a
        # `shutil.copy2(video_paths[0], output_path)` inside the
        # concat-failure exception branch (not the legitimate single-shot
        # copy when ``len(video_paths) == 1``). PR #46 replaced that with
        # an empty-placeholder write. This PR replaces the placeholder
        # with raising AssemblyError. We pin both:
        #   (a) no write_bytes placeholder anywhere
        #   (b) AssemblyError is raised on the failure paths
        assert 'output_path.write_bytes(b"")' not in src, (
            "_assemble_movie must NOT write a 0-byte placeholder on "
            "assembly failure — the empty file is indistinguishable from "
            "success at every downstream file-existence check. Raise "
            "AssemblyError instead. See [[feedback-no-silent-fallbacks]]."
        )

    def test_assembly_raises_on_failure(self):
        from scenemachine.services.production_pipeline import ProductionPipeline

        src = inspect.getsource(ProductionPipeline._assemble_movie)
        # At least three raise-sites: empty input, both strategies failed,
        # generic exception. Plus a defensive trailing raise for the
        # unreachable-fall-through guard.
        n_raises = src.count("raise AssemblyError")
        assert n_raises >= 3, (
            f"Expected at least 3 `raise AssemblyError` sites in "
            f"_assemble_movie (empty-input, both-strategies-failed, "
            f"generic-exception), found {n_raises}. Reverting to a "
            f"placeholder write reduces this count."
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


class TestAssemblyRaisesOnFailure:
    """Functional tests for the Phase-2 fix (this PR, 2026-05-20).

    Drive ``_assemble_movie`` end-to-end through the three failure modes
    and assert that:
      (a) ``AssemblyError`` is raised
      (b) no 0-byte file is written at the would-be output path

    These complement the source-grep tests above with behavioral
    coverage that catches refactors which keep the textual `raise
    AssemblyError` lines but reintroduce the write_bytes placeholder
    via some other route.
    """

    @pytest.fixture
    def pipeline(self, tmp_path):
        from scenemachine.services.production_pipeline import ProductionPipeline

        return ProductionPipeline(
            project_id="test-no-silent-fail",
            output_dir=tmp_path,
        )

    @pytest.mark.asyncio
    async def test_empty_shots_list_raises(self, pipeline):
        from scenemachine.services.production_pipeline import AssemblyError

        with pytest.raises(AssemblyError) as excinfo:
            await pipeline._assemble_movie([])
        assert "no completed shots" in str(excinfo.value).lower()

        expected_path = pipeline.output_dir / f"output_{pipeline.project_id}.mp4"
        assert not expected_path.exists(), (
            f"_assemble_movie wrote a placeholder at {expected_path} "
            f"despite raising. The whole point of the Phase-2 fix is to "
            f"leave no file behind on failure."
        )

    @pytest.mark.asyncio
    async def test_all_shots_failed_raises(self, pipeline):
        from scenemachine.services.production_pipeline import (
            AssemblyError,
            ShotGenerationStatus,
        )

        shots = [
            ShotGenerationStatus(
                shot_id=f"shot-{i}",
                scene_id=f"scene-{i}",
                status="failed",
                error="upstream gen failed",
            )
            for i in range(5)
        ]
        with pytest.raises(AssemblyError) as excinfo:
            await pipeline._assemble_movie(shots)
        # Message should mention the input count for forensics.
        assert "5 shots" in str(excinfo.value) or "received 5" in str(excinfo.value)

        expected_path = pipeline.output_dir / f"output_{pipeline.project_id}.mp4"
        assert not expected_path.exists()

    @pytest.mark.asyncio
    async def test_completed_shots_with_no_video_paths_raises(self, pipeline):
        from scenemachine.services.production_pipeline import (
            AssemblyError,
            ShotGenerationStatus,
        )

        # The harness's path-existence filter inside _assemble_movie drops
        # shots that lack a video_path or whose video_path doesn't exist.
        # If every shot is in this state, video_paths == [] and we should
        # raise — the failed-shot test above only exercises the
        # status="failed" filter; this one exercises the
        # video_path-doesn't-exist filter independently.
        shots = [
            ShotGenerationStatus(
                shot_id=f"shot-{i}",
                scene_id=f"scene-{i}",
                status="completed",
                video_path="/nonexistent/path/that/should/not/be/there.mp4",
            )
            for i in range(3)
        ]
        with pytest.raises(AssemblyError):
            await pipeline._assemble_movie(shots)

        expected_path = pipeline.output_dir / f"output_{pipeline.project_id}.mp4"
        assert not expected_path.exists()


class TestHarnessRecordsAssemblyError:
    """The harness side of the Phase-2 fix: run_benchmark.py's
    ``run_one_screenplay`` now catches AssemblyError and records it
    in the screenplay's result dict, preserving shot stats.

    Pre-fix, the harness called ``_assemble_movie`` unwrapped — if it
    had raised, the whole screenplay would have ended up as
    ``{"screenplay", "error", "preset"}`` only, losing shots_total /
    shots_completed / shots_failed needed for forensics. The wrapper
    keeps those fields.
    """

    def test_run_one_screenplay_catches_assembly_error(self):
        import inspect

        # The harness script lives outside the package so we read source
        # directly. This is the same approach the test_pr46* tests use
        # for production_pipeline.
        from pathlib import Path as _Path

        harness_path = (
            _Path(__file__).parent.parent.parent.parent.parent / "scripts" / "run_benchmark.py"
        )
        src = harness_path.read_text()
        # Look for the AssemblyError catch in run_one_screenplay.
        assert "AssemblyError" in src, (
            "scripts/run_benchmark.py must import AssemblyError and catch "
            "it in run_one_screenplay so RESULTS.json reflects assembly "
            "failure as a structured field rather than swallowing it."
        )
        assert "except AssemblyError" in src, (
            "Expected `except AssemblyError` block in run_one_screenplay."
        )
        assert "assembly_error" in src, (
            "Expected `assembly_error` key in the screenplay result dict "
            "so downstream tools can distinguish assembly failure from "
            "shot-level failure."
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
        assert "-update" in src and '"1"' in src, (
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
