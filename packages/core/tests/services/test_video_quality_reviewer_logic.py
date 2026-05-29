"""
Pure-logic tests for VideoQualityReviewer — weighted scoring, recommendations,
result serialization, and the numpy frame helpers (fed real temp PIL images,
no cv2 / ffmpeg / video files).
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scenemachine.services.video_quality_reviewer import (
    QualityDimension,
    QualityIssue,
    QualityScore,
    VideoQualityReviewer,
    VideoReviewResult,
)


def _save(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array.astype("uint8"), mode="L").save(path)


def test_calculate_overall_score_weighted():
    r = VideoQualityReviewer()
    scores = [
        QualityScore(QualityDimension.VISUAL_FIDELITY, score=0.8, confidence=1.0),
        QualityScore(QualityDimension.CHARACTER_CONSISTENCY, score=0.6, confidence=1.0),
    ]
    # Equal weights (0.20 each) + full confidence → mean of 0.8 and 0.6.
    assert r._calculate_overall_score(scores) == pytest.approx(0.7, abs=1e-6)


def test_calculate_overall_score_zero_weight_returns_zero():
    r = VideoQualityReviewer()
    scores = [QualityScore(QualityDimension.VISUAL_FIDELITY, score=0.9, confidence=0.0)]
    assert r._calculate_overall_score(scores) == 0.0
    assert r._calculate_overall_score([]) == 0.0


def test_generate_recommendations_for_low_dimensions_and_issues():
    r = VideoQualityReviewer(pass_threshold=0.7)
    scores = [
        QualityScore(QualityDimension.VISUAL_FIDELITY, score=0.3, confidence=1.0),
        QualityScore(QualityDimension.CHARACTER_CONSISTENCY, score=0.4, confidence=1.0),
    ]
    issues = [{"issue": QualityIssue.HAND_ARTIFACT.value}]
    recs = r._generate_recommendations(scores, issues)
    assert any("higher quality" in x for x in recs)
    assert any("IP-Adapter" in x or "LoRA" in x for x in recs)
    assert any("hand" in x.lower() for x in recs)
    assert len(recs) <= 5


def test_generate_recommendations_empty_when_all_pass():
    r = VideoQualityReviewer(pass_threshold=0.7)
    scores = [QualityScore(QualityDimension.VISUAL_FIDELITY, score=0.95, confidence=1.0)]
    assert r._generate_recommendations(scores, []) == []


def test_review_result_to_dict_roundtrips_nested():
    result = VideoReviewResult(
        video_path="/tmp/v.mp4",
        shot_id="s1",
        overall_score=0.82,
        dimension_scores=[
            QualityScore(
                QualityDimension.VISUAL_FIDELITY,
                score=0.8,
                confidence=0.9,
                issues=[QualityIssue.FACE_DISTORTION],
                notes="ok",
            )
        ],
        passed=True,
    )
    d = result.to_dict()
    assert d["overall_score"] == 0.82
    assert d["dimension_scores"][0]["dimension"] == QualityDimension.VISUAL_FIDELITY.value
    assert d["dimension_scores"][0]["issues"] == [QualityIssue.FACE_DISTORTION.value]
    assert d["escalation_reason"] is None


def test_laplacian_variance_flat_vs_textured():
    with tempfile.TemporaryDirectory() as td:
        flat = Path(td) / "flat.png"
        textured = Path(td) / "tex.png"
        _save(flat, np.full((32, 32), 128))
        # High-frequency checkerboard → large Laplacian variance.
        checker = np.indices((32, 32)).sum(axis=0) % 2 * 255
        _save(textured, checker)
        flat_var = VideoQualityReviewer._laplacian_variance(flat)
        tex_var = VideoQualityReviewer._laplacian_variance(textured)
        assert flat_var == pytest.approx(0.0, abs=1e-6)
        assert tex_var > flat_var


def test_laplacian_variance_tiny_image_returns_zero():
    with tempfile.TemporaryDirectory() as td:
        tiny = Path(td) / "tiny.png"
        _save(tiny, np.full((2, 2), 50))
        assert VideoQualityReviewer._laplacian_variance(tiny) == 0.0


def test_temporal_frame_deltas():
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.png"
        b = Path(td) / "b.png"
        c = Path(td) / "c.png"
        _save(a, np.full((16, 16), 100))
        _save(b, np.full((16, 16), 100))  # identical to a → delta ~0
        _save(c, np.full((16, 16), 200))  # differs from b → delta ~100
        deltas = VideoQualityReviewer._temporal_frame_deltas([a, b, c])
        assert len(deltas) == 2
        assert deltas[0] == pytest.approx(0.0, abs=1e-6)
        assert deltas[1] == pytest.approx(100.0, abs=1.0)
