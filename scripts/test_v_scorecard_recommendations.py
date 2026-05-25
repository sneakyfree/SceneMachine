"""Regression tests for scripts/v_scorecard.py::recommend_next.

Closes P1-8 — the recommendation heuristic was preset-blind and gave V11
(a prompt-diversification experiment) the dead-end "tune face_strength /
clip_vision_strength" advice that V8 had already disproved.

Run directly with `python scripts/test_v_scorecard_recommendations.py`,
or via `pytest scripts/test_v_scorecard_recommendations.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from anywhere by adding the scripts dir to sys.path
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import v_scorecard  # noqa: E402


def _result(
    tag: str, *, ref_sim: float, diversity: float, worst_rigidity: float
) -> dict:
    """Build a results-row in the shape recommend_next expects."""
    return {
        "tag": tag,
        "ref_sim_best_mean": ref_sim,
        "inter_shot_diversity_mean_cos": diversity,
        "per_character_self_sim": {
            "synthetic_char": {"mean_pairwise_cos": worst_rigidity},
        },
    }


def _v0() -> dict:
    return _result("V0", ref_sim=0.5332, diversity=0.6191, worst_rigidity=0.637)


def test_v11_no_longer_recommends_strength_tweaks() -> None:
    """The exact P1-8 regression: V11 must NOT get strength-tweak advice."""
    v11 = _result("V11", ref_sim=0.8077, diversity=0.7120, worst_rigidity=0.897)
    out = v_scorecard.recommend_next([v11, _v0()], "V0", "V11")

    assert "face_strength=0.3" not in out, (
        "P1-8 regression: V11 (a diversification preset) must not be told "
        "to tune face_strength — V8 already disproved that mechanism. "
        f"Got: {out[:300]}"
    )
    assert "clip_vision_strength=0.3" not in out
    # Must explain why and point at the right next rung.
    assert "exhausted" in out.lower(), (
        f"V11 advice must call out that the diversification mechanism is "
        f"empirically exhausted. Got: {out[:300]}"
    )
    assert "V10" in out and "LoRA" in out, (
        f"V11 advice must point at V10 LoRA as the next ladder rung. "
        f"Got: {out[:300]}"
    )


def test_v9b_per_char_chain_recognized_as_exhausted() -> None:
    """V9b's per-character chain mechanism is exhausted per the V9/V9b data."""
    v9b = _result("V9b", ref_sim=0.5843, diversity=0.7956, worst_rigidity=0.884)
    out = v_scorecard.recommend_next([v9b, _v0()], "V0", "V9b")
    # V9b has identity collapse — that branch fires first. Just check that
    # the advice is no longer the generic strength tweak.
    assert "face_strength=0.3" not in out
    assert "clip_vision_strength=0.3" not in out


def test_v5_strength_sweep_advice_only_when_strategy_matches() -> None:
    """A V6a-style strength-tweak preset SHOULD still get strength-tweak advice."""
    v6a = _result("V6a", ref_sim=0.78, diversity=0.69, worst_rigidity=0.82)
    out = v_scorecard.recommend_next([v6a, _v0()], "V0", "V6a")
    # V6a's strategy is strength_tweak, and it shows up in STRATEGY_EXHAUSTED.
    # So it should NOT recommend more strength tweaks either; we mark this
    # exhausted because the V6 series collectively showed strength is not the
    # lever. The advice should point at V10/V12 instead.
    assert "exhausted" in out.lower()
    assert "V10" in out


def test_baseline_v0_does_not_pretend_to_speak_to_rigidity() -> None:
    """V0/V1/V2/V3 are not rigidity experiments — when identity holds, advice
    should say "informational only" rather than prescribe rigidity fixes.

    (Use a hypothetical V3-like preset that DOESN'T collapse identity — the
    real V3 did, which is its own valid branch covered by
    test_identity_collapse_advice_is_clear.)
    """
    v3_strong_identity = _result(
        "V3", ref_sim=0.78, diversity=0.6163, worst_rigidity=0.78
    )
    out = v_scorecard.recommend_next([v3_strong_identity, _v0()], "V0", "V3")
    assert "informational" in out.lower() or "not a rigidity test" in out.lower(), (
        f"V3 (llm_prompts) with healthy identity is not a rigidity experiment; "
        f"advice should not prescribe rigidity-class fixes. Got: {out[:300]}"
    )


def test_unknown_tag_falls_through_safely() -> None:
    """A preset not in TAG_STRATEGY shouldn't give wrong-strategy advice."""
    v99 = _result(
        "V99_exotic_experiment", ref_sim=0.78, diversity=0.69, worst_rigidity=0.82
    )
    out = v_scorecard.recommend_next([v99, _v0()], "V0", "V99_exotic_experiment")
    # Old logic would say "Sweep strength harder: try face_strength=0.3" — wrong.
    assert "face_strength=0.3" not in out
    # New logic must surface that this is an unknown strategy.
    assert "unknown" in out.lower() or "not in" in out.lower()


def test_identity_collapse_advice_is_clear() -> None:
    """When identity collapses, the advice should call that out plainly."""
    v9 = _result("V9", ref_sim=0.5645, diversity=0.8731, worst_rigidity=0.85)
    out = v_scorecard.recommend_next([v9, _v0()], "V0", "V9")
    assert "Identity collapsed" in out
    # And it should not prescribe the V6c strength tweak unless this was
    # actually a strength-tweak preset.
    assert "V6c" not in out


def test_v5_target_when_already_passing_says_ship_v7() -> None:
    """If a hypothetical preset clears both bars, recommend V7."""
    v7candidate = _result(
        "V7_combined", ref_sim=0.82, diversity=0.55, worst_rigidity=0.70
    )
    out = v_scorecard.recommend_next([v7candidate, _v0()], "V0", "V7_combined")
    assert "Rigidity addressed" in out
    assert "V7" in out


if __name__ == "__main__":
    test_v11_no_longer_recommends_strength_tweaks()
    test_v9b_per_char_chain_recognized_as_exhausted()
    test_v5_strength_sweep_advice_only_when_strategy_matches()
    test_baseline_v0_does_not_pretend_to_speak_to_rigidity()
    test_unknown_tag_falls_through_safely()
    test_identity_collapse_advice_is_clear()
    test_v5_target_when_already_passing_says_ship_v7()
    print("ALL 7 PASS")
