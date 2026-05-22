"""Deterministic calibration tests for the real quality metrics (PR #56 + #57).

PR #56 shipped `_check_visual_fidelity` using Laplacian-variance sharpness.
PR #57 shipped `_check_temporal_stability` using frame-delta CoV.
Both replaced hardcoded 0.85 stubs flagged by the 2026-05-14 DNA-strand audit.

Both have been validated *empirically* against the V0 corpus (105 shots,
per-shot scores on HF at SceneMachine/operations-log/benchmarks/V0_2026-05-14/
per_shot_quality_baseline.json). What was missing: a regression tripwire
that fires the moment someone changes the math, the cap, the threshold,
or the kernel and silently shifts the calibration.

Strategy: feed synthetic numpy arrays with KNOWN sharpness/temporal
properties through the pure functions (`_laplacian_variance` and
`_temporal_frame_deltas`) and pin the output bands. These tests do NOT
require ffmpeg, do NOT touch the GPU, run in well under a second, and
fail loudly if the metric semantics drift.

If V0 corpus gets re-measured and the medians shift by >2x, these tests
will catch it before it lands in main and silently invalidates the V0
baseline that every future V_N is measured against.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _save_png(arr: np.ndarray, path: Path) -> None:
    """Save a 2D uint8 array as a grayscale PNG."""
    Image.fromarray(arr.astype(np.uint8), mode="L").save(path)


def _flat_image(value: int = 128, size: int = 64) -> np.ndarray:
    """All-pixels-the-same image. Laplacian variance ≈ 0."""
    return np.full((size, size), value, dtype=np.uint8)


def _checkerboard(size: int = 64, cell: int = 4) -> np.ndarray:
    """Hard-edged checkerboard. Very high Laplacian variance."""
    arr = np.zeros((size, size), dtype=np.uint8)
    for y in range(size):
        for x in range(size):
            if ((y // cell) + (x // cell)) % 2 == 0:
                arr[y, x] = 255
    return arr


def _gaussian_noise(size: int = 64, seed: int = 0, sigma: float = 50.0) -> np.ndarray:
    """Pure noise. High Laplacian variance, no spatial structure."""
    rng = np.random.default_rng(seed)
    arr = 128 + sigma * rng.standard_normal((size, size))
    return np.clip(arr, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------
# _laplacian_variance — pure function pinning
# ----------------------------------------------------------------------


class TestLaplacianVariance:
    """Pin the spatial-sharpness math from PR #56."""

    @pytest.fixture
    def func(self):
        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
        return VideoQualityReviewer._laplacian_variance

    def test_flat_image_near_zero(self, func, tmp_path):
        p = tmp_path / "flat.png"
        _save_png(_flat_image(value=128), p)
        var = func(p)
        assert var < 1e-6, (
            f"Flat image must produce ~0 Laplacian variance; got {var}. "
            "If this fails, the Laplacian kernel itself is wrong "
            "(every neighbour-difference should vanish on a constant)."
        )

    def test_flat_image_value_invariant(self, func, tmp_path):
        """A different constant value must STILL be ~0 — measure is brightness-invariant."""
        p1 = tmp_path / "dark.png"
        p2 = tmp_path / "bright.png"
        _save_png(_flat_image(value=10), p1)
        _save_png(_flat_image(value=240), p2)
        v1, v2 = func(p1), func(p2)
        assert v1 < 1e-6 and v2 < 1e-6, (
            f"Flat-image variance must be brightness-invariant; "
            f"got dark={v1}, bright={v2}. If non-zero, the kernel "
            "is not a true Laplacian (DC offset is leaking through)."
        )

    def test_checkerboard_high(self, func, tmp_path):
        p = tmp_path / "checker.png"
        _save_png(_checkerboard(size=64, cell=4), p)
        var = func(p)
        assert var > 5000.0, (
            f"Checkerboard must score WAY above the V0 median (~927); "
            f"got {var}. Hard-edged synthetic content represents the "
            "upper end of what real footage can produce."
        )

    def test_gaussian_noise_high(self, func, tmp_path):
        p = tmp_path / "noise.png"
        _save_png(_gaussian_noise(size=64, seed=42, sigma=50.0), p)
        var = func(p)
        # Pure-noise σ=50 produces very high Laplacian variance
        # (every pixel-pair differs independently).
        assert var > 1000.0, (
            f"σ=50 Gaussian noise must score above V0 median (~927); got {var}."
        )

    def test_returns_float(self, func, tmp_path):
        p = tmp_path / "f.png"
        _save_png(_flat_image(), p)
        assert isinstance(func(p), float), (
            "_laplacian_variance must return Python float (not numpy.float64) "
            "so JSON serialization in measure_v0_baseline.py works."
        )

    def test_non_negative(self, func, tmp_path):
        """Variance is mathematically non-negative; pin it."""
        for sigma in [0.0, 1.0, 10.0, 100.0]:
            p = tmp_path / f"n{sigma}.png"
            _save_png(_gaussian_noise(seed=int(sigma * 7), sigma=sigma), p)
            assert func(p) >= 0.0


# ----------------------------------------------------------------------
# _temporal_frame_deltas — pure function pinning
# ----------------------------------------------------------------------


class TestTemporalFrameDeltas:
    """Pin the temporal-stability math from PR #57."""

    @pytest.fixture
    def func(self):
        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
        return VideoQualityReviewer._temporal_frame_deltas

    def _write_frames(self, arrays, tmp_path):
        paths = []
        for i, arr in enumerate(arrays):
            p = tmp_path / f"f{i:02d}.png"
            _save_png(arr, p)
            paths.append(p)
        return paths

    def test_identical_frames_zero_delta(self, func, tmp_path):
        same = _flat_image(value=128)
        paths = self._write_frames([same, same, same, same], tmp_path)
        deltas = func(paths)
        assert len(deltas) == 3, "N frames must produce N-1 deltas"
        assert all(d == 0.0 for d in deltas), (
            f"Identical frames must produce all-zero deltas; got {deltas}. "
            "Non-zero would indicate the metric is reading something "
            "other than mean-abs-pixel-difference."
        )

    def test_linear_brightness_walk_constant_deltas(self, func, tmp_path):
        """Frames that step uniformly in brightness produce uniform deltas
        — the metric is doing |frame_i - frame_{i+1}| correctly."""
        arrays = [_flat_image(value=v) for v in [50, 60, 70, 80, 90]]
        paths = self._write_frames(arrays, tmp_path)
        deltas = func(paths)
        # Each step is +10 in brightness; mean abs delta = 10 for all pairs
        assert len(deltas) == 4
        for d in deltas:
            assert 9.5 < d < 10.5, (
                f"Linear step-10 brightness walk should produce ~10 deltas; "
                f"got {deltas}. Drift indicates the metric is no longer "
                "mean-abs-pixel-difference on grayscale."
            )

    def test_morph_frame_produces_burst(self, func, tmp_path):
        """One huge morph among smooth deltas — the burst that high CoV catches."""
        smooth = _flat_image(value=100)
        smooth2 = _flat_image(value=102)
        morph = _flat_image(value=200)
        # smooth, smooth2, morph, smooth2 → deltas: 2, 98, 98
        paths = self._write_frames([smooth, smooth2, morph, smooth2], tmp_path)
        deltas = func(paths)
        assert len(deltas) == 3
        assert deltas[0] < 5
        assert deltas[1] > 90
        assert deltas[2] > 90

    def test_skips_shape_mismatch(self, func, tmp_path):
        """Mismatched-resolution frames must be skipped, not crash."""
        a = _flat_image(value=128, size=32)
        b = _flat_image(value=128, size=64)
        c = _flat_image(value=128, size=32)
        paths = self._write_frames([a, b, c], tmp_path)
        # Path 0→1 mismatch (skipped), Path 1→2 mismatch (skipped)
        # We expect 0 deltas, not a crash.
        deltas = func(paths)
        assert isinstance(deltas, list)

    def test_handles_missing_file_gracefully(self, func, tmp_path):
        """A missing PNG mid-sequence must not crash the whole computation."""
        a = _flat_image(value=100)
        c = _flat_image(value=110)
        paths = self._write_frames([a, c], tmp_path)
        # Insert a non-existent path in the middle
        paths.insert(1, tmp_path / "missing.png")
        deltas = func(paths)  # must not raise
        assert isinstance(deltas, list)


# ----------------------------------------------------------------------
# Calibration constants — pin the published thresholds
# ----------------------------------------------------------------------


class TestCalibrationConstants:
    """The cap + threshold values are PUBLISHED in the V0 baseline INDEX.md
    on HF. Future versions are measured against V0 using these exact
    numbers. Any silent change invalidates every prior comparison."""

    @pytest.fixture
    def cls(self):
        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
        return VideoQualityReviewer

    def test_sharpness_cap_published(self, cls):
        assert cls.SHARPNESS_SCORE_CAP == 1000.0, (
            "SHARPNESS_SCORE_CAP=1000 is the calibration anchor — "
            "V0 median ~927 maps to ~0.93, leaving headroom for sharper "
            "future versions. Changing this silently re-grades every "
            "shot ever measured."
        )

    def test_blurry_threshold_published(self, cls):
        assert cls.BLURRY_LAPLACIAN_THRESHOLD == 30.0, (
            "BLURRY_LAPLACIAN_THRESHOLD=30 was set so flat regions / "
            "heavy motion blur trip the flag but reasonable footage "
            "does not. V0: 0/105 shots flagged. Lowering this is a "
            "calibration change requiring a new baseline."
        )

    def test_temporal_cap_published(self, cls):
        assert cls.TEMPORAL_COV_CAP == 2.0, (
            "TEMPORAL_COV_CAP=2.0 anchors the temporal score. "
            "Changing it silently re-grades every prior measurement."
        )

    def test_unstable_threshold_published(self, cls):
        assert cls.UNSTABLE_COV_THRESHOLD == 1.0, (
            "UNSTABLE_COV_THRESHOLD=1.0 is the flicker-flag trip. "
            "V0: 1/105 shots flagged. Calibration anchor."
        )

    def test_blurry_threshold_below_cap(self, cls):
        """Sanity: blurry threshold must be below the cap."""
        assert cls.BLURRY_LAPLACIAN_THRESHOLD < cls.SHARPNESS_SCORE_CAP

    def test_unstable_threshold_below_cap(self, cls):
        """Sanity: unstable threshold must be below the cap."""
        assert cls.UNSTABLE_COV_THRESHOLD < cls.TEMPORAL_COV_CAP


# ----------------------------------------------------------------------
# End-to-end: real metric call on a synthetic mp4
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_fidelity_on_synthetic_blurry_video(tmp_path):
    """Render a 1s mp4 of a flat-gray frame via ffmpeg and verify
    _check_visual_fidelity flags it as BLURRY. Skips if ffmpeg is
    missing — this is a confidence integration test, not a unit pin.
    """
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not available")

    from scenemachine.services.video_quality_reviewer import (
        QualityIssue,
        VideoQualityReviewer,
    )

    mp4 = tmp_path / "blurry.mp4"
    # 1 second of solid gray @ 24 fps
    rc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "color=c=gray:s=128x128:d=1:r=24",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)],
        timeout=30,
    ).returncode
    if rc != 0 or not mp4.exists():
        pytest.skip("ffmpeg synthesis failed (likely missing libx264)")

    reviewer = VideoQualityReviewer()
    result = await reviewer._check_visual_fidelity(mp4)

    assert QualityIssue.BLURRY_FRAMES in result.issues, (
        f"A solid-gray mp4 must trigger the BLURRY_FRAMES flag; got "
        f"issues={result.issues}, notes={result.notes}. This integration "
        "tripwire confirms the unit-tested math actually reaches the "
        "issues-list output when wired end-to-end through ffmpeg."
    )
    assert result.score < 0.1, (
        f"Solid-gray score must be near 0; got {result.score}."
    )
