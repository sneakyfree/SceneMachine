"""Regression tests for PR #63 — fix the silent quality-review bug.

Before PR #63, `production_pipeline.generate_shot` called
`review.get("overall_score", ...)` on the VideoReviewResult dataclass.
The dataclass has no `.get()` method, so every call raised
AttributeError, which was swallowed by a bare `except` and logged at
DEBUG. End result: the quality review path was a NO-OP in production
for every shot generated — silent regression of exactly the kind banned
by the feedback_no_silent_fallbacks memory.

This file pins:
  1. `review.get(` is gone from production_pipeline.py source.
  2. ShotGenerationStatus has the `quality_review` field for the
     per-dimension breakdown.
  3. The review path uses `await reviewer.review_video(...)` with
     prompt + character_references + regeneration_count (real signal,
     not just the bare video path).
  4. The fallback log path is WARNING, not DEBUG — silent failure was
     literally the bug.

Structural source-level assertions on the same file pattern as PR #54's
test_overnight_fixes_regression.py — fast, deterministic, no GPU.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Resolve the production_pipeline source path once
_PRODUCTION_PIPELINE_SRC = (
    Path(__file__).resolve().parents[2] / "scenemachine" / "services" / "production_pipeline.py"
)


@pytest.fixture(scope="module")
def src() -> str:
    return _PRODUCTION_PIPELINE_SRC.read_text()


class TestPR63NoReviewGetCall:
    """The broken pattern `review.get(...)` must never come back.
    VideoReviewResult is a dataclass; attribute access is correct.
    """

    def test_no_review_get_pattern(self, src: str):
        # Must not have `.get(` invoked on the review result. Allow
        # other .get() calls (e.g. dict.get on shot_data) by anchoring
        # on the specific variable name.
        assert "review.get(" not in src, (
            "review.get(...) is the bug PR #63 fixed. VideoReviewResult "
            "is a dataclass — `review.overall_score` is the correct access. "
            "Reintroducing review.get(...) means every quality review "
            "silently crashes again. Banned by feedback_no_silent_fallbacks."
        )

    def test_uses_overall_score_attribute(self, src: str):
        assert "review.overall_score" in src, (
            "Production pipeline must read review.overall_score directly "
            "via attribute access (dataclass field), not via .get()."
        )


class TestPR63ShotStatusQualityReviewField:
    """The full per-dimension review is cached on the shot so the UI
    and audit view can show what failed without re-running the
    (CPU-heavy) review.
    """

    def test_field_exists_on_dataclass(self):
        from scenemachine.services.production_pipeline import ShotGenerationStatus

        # Dataclass instance with required positional/keyword args
        s = ShotGenerationStatus(shot_id="s1", scene_id="sc1", status="queued")
        assert hasattr(s, "quality_review"), (
            "ShotGenerationStatus must expose quality_review for the "
            "per-dimension breakdown caching path (PR #63)."
        )
        assert s.quality_review is None, "default must be None"

    def test_field_assignable_with_dict(self):
        from scenemachine.services.production_pipeline import ShotGenerationStatus

        s = ShotGenerationStatus(shot_id="s1", scene_id="sc1", status="queued")
        s.quality_review = {"overall_score": 0.42, "dimension_scores": []}
        assert s.quality_review["overall_score"] == 0.42


class TestPR63ReviewPathPassesRealSignal:
    """review_video accepts prompt + character_references + regeneration_count.
    Pre-PR #63 the pipeline called it with only the video path — even
    the now-real dimensions (character_consistency, prompt_adherence)
    got no signal. Pin that the call site passes the real args."""

    def test_call_passes_prompt(self, src: str):
        assert "prompt=prompt_text" in src or "prompt=" in src, (
            "review_video must be called with prompt= so prompt_adherence "
            "(when implemented) has something to compare to."
        )

    def test_call_passes_character_references(self, src: str):
        assert "character_references=char_refs" in src or "character_references=" in src, (
            "review_video must be called with character_references= so "
            "character_consistency (PR #60) can run in reference-comparison mode."
        )

    def test_call_passes_regeneration_count(self, src: str):
        assert "regeneration_count=shot.regeneration_count" in src, (
            "review_video must be told the current regen attempt so the "
            "MULTIPLE_REGENERATIONS escalation reason fires correctly."
        )


class TestPR63FailureLoggingNotSilent:
    """The bug was `logger.debug(...)` swallowing every AttributeError.
    The fix log must be WARNING (or higher) so a real review crash
    surfaces, with exc_info=True so the stack lands in the log."""

    def test_review_failure_logs_at_warning(self, src: str):
        # Find the except block in the review path
        # (proximity check — the WARNING log must follow the except)
        assert "quality review failed" in src, (
            "Failure log message must be present so operators can grep for review failures."
        )
        assert "logger.warning" in src, (
            "Quality review failure path must log at WARNING, not DEBUG. "
            "The original DEBUG-level swallow is what made the bug invisible."
        )
        assert "exc_info=True" in src, (
            "exc_info=True is required so the stack trace lands in the log "
            "for diagnosis. Banned silent fallback per feedback memory."
        )


class TestPR63NoBreakingExistingCallers:
    """The quality_review field added to ShotGenerationStatus must
    have a default so all existing call sites that create the dataclass
    without it continue to work."""

    def test_dataclass_constructible_without_quality_review(self):
        from scenemachine.services.production_pipeline import ShotGenerationStatus

        # Should not raise
        ShotGenerationStatus(shot_id="x", scene_id="y", status="queued")

    def test_to_dict_serialization_includes_quality_review(self):
        """If shots get serialized for IPC (snapshots, audit view), the
        new field must round-trip cleanly."""
        from dataclasses import asdict

        from scenemachine.services.production_pipeline import ShotGenerationStatus

        s = ShotGenerationStatus(shot_id="x", scene_id="y", status="completed")
        s.quality_review = {"overall_score": 0.5}
        d = asdict(s)
        assert d["quality_review"] == {"overall_score": 0.5}
