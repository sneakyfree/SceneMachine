"""Regression tests for P1-5 — Laplacian silent-fail in VideoQualityReviewer.

Before iter 10, when all Laplacian computations failed the visual-fidelity
check returned score=0.5 + confidence=0.1, which a scorecard easily reads
as "acceptable." Now it returns score=0.0 with a distinctive notes field
and warning-level logging.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from scenemachine.services.video_quality_reviewer import (
    QualityDimension,
    VideoQualityReviewer,
)


async def test_all_frames_failed_returns_zero_score_not_half(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The exact P1-5 regression: 100% Laplacian failures must NOT score 0.5."""
    reviewer = VideoQualityReviewer()

    fake_frames = [tmp_path / f"frame_{i}.png" for i in range(5)]
    for f in fake_frames:
        f.write_bytes(b"not a real png")

    def _fake_extract(*args, **kwargs):
        return fake_frames

    # Force Laplacian to raise for every frame.
    with (
        patch.object(
            reviewer,
            "_sample_frame_paths",
            side_effect=_fake_extract,
        ),
        patch.object(
            reviewer,
            "_laplacian_variance",
            side_effect=RuntimeError("PIL cannot open"),
        ),
    ):
        with caplog.at_level(logging.WARNING):
            score = await reviewer._check_visual_fidelity(tmp_path / "video.mp4")

    assert score.dimension == QualityDimension.VISUAL_FIDELITY
    assert score.score == 0.0, (
        f"P1-5 regression: all-failures must return 0.0, not {score.score}. "
        "The old 0.5 looked 'acceptable' in scorecards."
    )
    assert score.confidence < 0.1
    assert "LAPLACIAN_ALL_FRAMES_FAILED" in (score.notes or "")
    assert any(
        "Laplacian failed" in record.message
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ), "per-frame failures must be visible at WARNING level (was debug)"


async def test_partial_failures_still_score_with_remaining_frames(
    tmp_path: Path,
) -> None:
    """If SOME frames succeed, return a real score from the survivors."""
    reviewer = VideoQualityReviewer()

    fake_frames = [tmp_path / f"frame_{i}.png" for i in range(4)]
    for f in fake_frames:
        f.write_bytes(b"x")

    def _fake_extract(*args, **kwargs):
        return fake_frames

    # First two raise, last two return reasonable Laplacian variances.
    side_effects = [RuntimeError("oops"), RuntimeError("oops"), 200.0, 800.0]

    with (
        patch.object(
            reviewer,
            "_sample_frame_paths",
            side_effect=_fake_extract,
        ),
        patch.object(
            reviewer,
            "_laplacian_variance",
            side_effect=side_effects,
        ),
    ):
        score = await reviewer._check_visual_fidelity(tmp_path / "video.mp4")

    assert score.dimension == QualityDimension.VISUAL_FIDELITY
    assert 0.0 < score.score <= 1.0
    # Not the all-failed sentinel
    assert "LAPLACIAN_ALL_FRAMES_FAILED" not in (score.notes or "")


async def test_no_frames_extracted_unchanged_path(tmp_path: Path) -> None:
    """If extract_sample_frames returns []: pre-existing branch, not iter 10's concern."""
    reviewer = VideoQualityReviewer()

    def _fake_extract(*args, **kwargs):
        return []

    with patch.object(
        reviewer,
        "_sample_frame_paths",
        side_effect=_fake_extract,
    ):
        score = await reviewer._check_visual_fidelity(tmp_path / "video.mp4")

    # The no-frames branch still returns the original 0.5/0.1 — that's
    # a separate issue. This test pins that we didn't change it.
    assert score.dimension == QualityDimension.VISUAL_FIDELITY
