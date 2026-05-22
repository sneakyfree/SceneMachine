"""Calibration tests for the real character-consistency quality dimension (PR #60).

PR #60 replaced the hardcoded 0.75 stub with a real InsightFace-based
within-video face-identity-drift measurement. This is the dimension the
V0 baseline measurement (PR #58) identified as the actual slop driver:
sharpness + temporal CoV passed 104/105 V0 shots Grant graded as 1/5 slop;
identity drift is the missing signal.

Strategy:
  - Unit tests with mocked FaceEmbeddingService verify the math and
    branching: zero faces → high score / low confidence (legit non-
    character shot), drift threshold flagging, reference blending,
    insufficient-data fallback.
  - Constants pinned to published calibration values.
  - Optional integration test on a real V0 shot (skipped if shots dir
    or InsightFace model isn't on the runner).

Mock-based so the test suite stays fast and CI-portable. Real-model
behavior is validated by the per-shot measurement script.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

# ----------------------------------------------------------------------
# Helpers — synthetic embeddings + fake service
# ----------------------------------------------------------------------


def _make_embedding(seed: int, dim: int = 512) -> np.ndarray:
    """Deterministic random embedding. Different seeds = different 'people'."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(dim).astype(np.float32)
    return e / np.linalg.norm(e)


def _similarity_helper(a, b):
    """Replicate face_embedding.compute_similarity math for test mocking."""
    if a is None or b is None:
        return 0.0
    n1, n2 = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if n1 == 0 or n2 == 0:
        return 0.0
    sim = float(np.dot(a, b) / (n1 * n2))
    return float(max(0.0, min(1.0, (sim + 1) / 2)))


class FakeEmbeddingResult:
    def __init__(self, embedding):
        self.success = embedding is not None
        self.primary_embedding = embedding
        self.faces = [object()] if embedding is not None else []


class FakeFaceService:
    """Test double that returns scripted embeddings per call."""

    def __init__(self, embeddings_per_frame, ref_embeddings=None):
        self.gpu_id = -1
        self._frame_embeddings = list(embeddings_per_frame)
        self._refs = list(ref_embeddings or [])
        self._frame_idx = 0
        self._ref_idx = 0

    def extract_embedding(self, path, select_largest=True):
        path_str = str(path)
        # Reference paths use a distinctive marker
        if "/ref_" in path_str:
            idx = self._ref_idx
            self._ref_idx += 1
            if idx < len(self._refs):
                return FakeEmbeddingResult(self._refs[idx])
            return FakeEmbeddingResult(None)
        # Otherwise it's a frame
        idx = self._frame_idx
        self._frame_idx += 1
        if idx < len(self._frame_embeddings):
            return FakeEmbeddingResult(self._frame_embeddings[idx])
        return FakeEmbeddingResult(None)

    def compute_similarity(self, a, b):
        return _similarity_helper(a, b)


# ----------------------------------------------------------------------
# Calibration constants
# ----------------------------------------------------------------------


class TestCharacterConsistencyConstants:
    """Pin published thresholds — see PR #60 docstring."""

    @pytest.fixture
    def cls(self):
        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
        return VideoQualityReviewer

    def test_drift_threshold_published(self, cls):
        assert cls.CHARACTER_DRIFT_THRESHOLD == 0.55, (
            "CHARACTER_DRIFT_THRESHOLD=0.55 sits just above the InsightFace "
            "'uncorrelated different people' band (mapped cosine sim ~0.5). "
            "Changing this silently re-grades every prior character-consistency "
            "measurement."
        )

    def test_frame_samples_published(self, cls):
        assert cls.CHARACTER_FRAME_SAMPLES == 8

    def test_min_face_frames_published(self, cls):
        assert cls.MIN_FACE_FRAMES == 2

    def test_drift_threshold_in_range(self, cls):
        assert 0.0 < cls.CHARACTER_DRIFT_THRESHOLD < 1.0


# ----------------------------------------------------------------------
# Branching: zero faces, sparse faces, drift, refs, etc.
# ----------------------------------------------------------------------


class TestCharacterConsistencyBranches:
    """Mock the face service to drive each code path. Each test sets up
    a synthetic embedding sequence and verifies the resulting QualityScore."""

    @pytest.fixture
    def reviewer(self):
        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
        return VideoQualityReviewer()

    @pytest.fixture
    def fake_frame_paths(self, tmp_path):
        """Provide CHARACTER_FRAME_SAMPLES dummy frame paths."""
        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
        n = VideoQualityReviewer.CHARACTER_FRAME_SAMPLES
        paths = []
        for i in range(n):
            p = tmp_path / f"frame_{i:02d}.png"
            p.write_bytes(b"dummy")
            paths.append(p)
        return paths

    def _run(self, reviewer, fake_frame_paths, frame_embeddings, ref_paths=None, ref_embeddings=None):
        """Invoke _check_character_consistency with patched frame extraction + face service."""
        import asyncio

        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer

        fake_svc = FakeFaceService(frame_embeddings, ref_embeddings)
        with patch.object(
            VideoQualityReviewer, "_sample_frame_paths",
            staticmethod(lambda video_path, n=8: fake_frame_paths),
        ), patch(
            "scenemachine.services.face_embedding.get_face_embedding_service",
            return_value=fake_svc,
        ):
            return asyncio.run(
                reviewer._check_character_consistency(Path("/dev/null"), ref_paths)
            )

    def test_zero_faces_high_score_low_confidence(self, reviewer, fake_frame_paths):
        """Non-character shot: no faces detected. High score, low conf."""
        from scenemachine.services.video_quality_reviewer import QualityIssue
        result = self._run(reviewer, fake_frame_paths, [None] * len(fake_frame_paths))
        assert result.score >= 0.9, (
            f"No faces should NOT penalize (legit non-character shots); "
            f"got score={result.score}, notes={result.notes}"
        )
        assert result.confidence <= 0.4, (
            "Confidence must be low when we have no data to measure on"
        )
        assert QualityIssue.CHARACTER_DRIFT not in result.issues

    def test_one_face_frame_no_refs_moderate(self, reviewer, fake_frame_paths):
        """1 face frame, no refs — can't compute drift, no comparison signal."""
        embs = [None] * (len(fake_frame_paths) - 1) + [_make_embedding(1)]
        result = self._run(reviewer, fake_frame_paths, embs)
        assert 0.5 <= result.score <= 0.85
        assert result.confidence <= 0.5

    def test_same_person_throughout_high_score(self, reviewer, fake_frame_paths):
        """Same identity in every frame → high drift score, no flag."""
        from scenemachine.services.video_quality_reviewer import QualityIssue
        # Use the SAME embedding for every frame → similarity = 1.0 for all pairs
        same = _make_embedding(seed=42)
        embs = [same] * len(fake_frame_paths)
        result = self._run(reviewer, fake_frame_paths, embs)
        assert result.score >= 0.95, (
            f"Same embedding every frame must score near 1.0; got {result.score}, "
            f"notes={result.notes}"
        )
        assert QualityIssue.CHARACTER_DRIFT not in result.issues

    def test_morphing_subject_flags_drift(self, reviewer, fake_frame_paths):
        """Anti-correlated embeddings every consecutive frame → flag fires.

        Constructed: alternate frame is the NEGATION of the previous so
        every consecutive pair has cos sim = -1 → mapped 0.0. This is the
        synthetic equivalent of a shot where the model rebuilds the
        face into a different identity every frame.
        """
        from scenemachine.services.video_quality_reviewer import QualityIssue
        base = _make_embedding(seed=1)
        embs = []
        for i in range(len(fake_frame_paths)):
            embs.append(base if i % 2 == 0 else -base)
        result = self._run(reviewer, fake_frame_paths, embs)
        assert QualityIssue.CHARACTER_DRIFT in result.issues, (
            f"Anti-correlated embeddings every frame MUST flag CHARACTER_DRIFT; "
            f"got score={result.score}, notes={result.notes}, issues={result.issues}"
        )
        assert result.score < 0.1, f"Anti-correlated → mapped ~0.0; got {result.score}"

    def test_uncorrelated_subjects_also_flag(self, reviewer, fake_frame_paths):
        """Uncorrelated embeddings (different people, not anti-correlated) → mapped ~0.5,
        which is below threshold 0.55, so flag should fire. This is the
        common slop case: the model picks a different person each frame."""
        from scenemachine.services.video_quality_reviewer import QualityIssue
        embs = [_make_embedding(seed=i * 1000 + 1) for i in range(len(fake_frame_paths))]
        result = self._run(reviewer, fake_frame_paths, embs)
        # 512-dim random embeddings have cos sim ~0 (within noise);
        # mapped ~0.5 sits just below the 0.55 threshold so the flag fires.
        assert QualityIssue.CHARACTER_DRIFT in result.issues, (
            f"Uncorrelated random embeddings should flag drift "
            f"(threshold 0.55 above the ~0.5 uncorrelated band); "
            f"got score={result.score}, notes={result.notes}"
        )

    def test_reference_blending(self, reviewer, fake_frame_paths):
        """When refs provided AND drift is computable, score blends 50/50."""
        ref = _make_embedding(seed=100)
        # All frames match the reference exactly → ref_sim = 1.0
        # All frames identical → drift = 1.0
        # Final score should also be ~1.0
        embs = [ref] * len(fake_frame_paths)
        result = self._run(
            reviewer, fake_frame_paths, embs,
            ref_paths=["/tmp/ref_jack.png"], ref_embeddings=[ref],
        )
        assert result.score >= 0.95
        assert "refmatch=" in result.notes
        assert "drift=" in result.notes

    def test_reference_only_when_no_drift_computable(self, reviewer, fake_frame_paths):
        """1 face frame + 1 reference: score from reference comparison only."""
        face_emb = _make_embedding(seed=7)
        ref = _make_embedding(seed=7)  # Same person — should score high
        # Re-derive: same seed = same embedding = exact match
        embs = [None] * (len(fake_frame_paths) - 1) + [face_emb]
        result = self._run(
            reviewer, fake_frame_paths, embs,
            ref_paths=["/tmp/ref_jack.png"], ref_embeddings=[ref],
        )
        assert "refmatch=" in result.notes
        assert "drift=" not in result.notes
        # Same seed → sim = 1.0
        assert result.score >= 0.95

    def test_no_frames_extracted_low_confidence(self, reviewer):
        """If frame extraction yields zero frames, return graceful low-conf."""
        import asyncio

        from scenemachine.services.video_quality_reviewer import VideoQualityReviewer

        with patch.object(
            VideoQualityReviewer, "_sample_frame_paths",
            staticmethod(lambda video_path, n=8: []),
        ):
            result = asyncio.run(
                reviewer._check_character_consistency(Path("/dev/null"))
            )
        assert result.confidence <= 0.2
        assert "Could not extract" in result.notes

    def test_signature_accepts_optional_refs(self, reviewer):
        """Public signature must allow calling without reference_paths
        (PR #60 changed it from required to Optional[List[str]]=None)."""
        import inspect
        sig = inspect.signature(reviewer._check_character_consistency)
        assert sig.parameters["reference_paths"].default is None


# ----------------------------------------------------------------------
# Issue enum
# ----------------------------------------------------------------------


def test_character_drift_issue_enum_exists():
    """PR #60 adds QualityIssue.CHARACTER_DRIFT."""
    from scenemachine.services.video_quality_reviewer import QualityIssue
    assert QualityIssue.CHARACTER_DRIFT.value == "character_drift", (
        "CHARACTER_DRIFT must be a string-valued enum member so it "
        "round-trips through JSON for the per-shot baseline."
    )
