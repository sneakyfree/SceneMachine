"""V-version scorecard — synthesize SCF JSON + montages into one markdown page.

Consumes the JSON from ``scripts/analyze_scene_context_fidelity.py`` plus the
PNG montages from ``scripts/make_rigidity_montage.py`` and emits a single
markdown report that pulls the headline numbers, per-character deltas, and
visual evidence together. Designed so that after every benchmark run (V6a,
V6b, V7-proper, …) Grant gets a one-page Grant-readable artifact instead
of staring at raw JSON.

What the markdown contains
--------------------------

1. **Headline table** — one row per tag (V0, V1, V5, V6a, …) with
   inter_shot_diversity, ref_sim_best_mean, ref_sim_best_max, and the
   number of character clusters that reached the metric's
   ``--min-cluster-size``.

2. **Per-character delta table** — for each character that has ≥3
   shots in at least one tag, the within-cluster pairwise CLIP cosine
   per tag and the **delta vs V0**. Rigidity (1.51× for V5/V0 Ellie)
   becomes a single column.

3. **Visual evidence** — embedded markdown image references to the
   montages. Renders nicely on GitHub.

4. **Auto recommendation** — looks at the latest tag's numbers vs V0
   and V5 baselines and prints what experiment to run next:
   * "rigidity not addressed" → harder strength sweep (V6b)
   * "rigidity addressed, identity lost" → only reduce one knob
   * "rigidity addressed, identity preserved" → ship V7-proper
   * "ambiguous" → flag for human review

Usage
-----

    python scripts/v_scorecard.py \\
      --scf-json .../scene_context_fidelity_with_V6a.json \\
      --montage-dir .../rigidity_montage_with_V6a \\
      --baseline-tag V0 \\
      --target-tag V6a \\
      --out .../scorecard_V6a.md

The baseline-tag is the slop reference; target-tag is the latest run.
Other tags in the SCF JSON are included in tables but not in the
recommendation logic.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Thresholds the recommendation logic applies to the target tag.
RIGIDITY_THRESHOLD_ACCEPTABLE = 0.75  # per-char self-sim above this = "still rigid"
REF_SIM_IDENTITY_FLOOR = 0.65  # below this = identity probably collapsed
DIVERSITY_FLOOR = 0.65  # inter-shot diversity below this = healthy variety


def fmt(value: Any, places: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{places}f}"
    return str(value)


def headline_table(results: list[dict]) -> str:
    """Markdown table: one row per tag, headline numbers + cluster count."""
    lines = [
        "| tag | inter_shot_diversity | ref_sim_mean | ref_sim_max | clusters≥3 |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in results:
        if "error" in r:
            lines.append(
                f"| {r.get('tag','?')} | ERROR: {r['error'][:80]} | — | — | — |"
            )
            continue
        per_char = r.get("per_character_self_sim") or {}
        lines.append(
            f"| {r['tag']} | "
            f"{fmt(r.get('inter_shot_diversity_mean_cos'))} | "
            f"{fmt(r.get('ref_sim_best_mean'))} | "
            f"{fmt(r.get('ref_sim_best_max'))} | "
            f"{len(per_char)} |"
        )
    return "\n".join(lines)


def per_character_table(results: list[dict]) -> str:
    """Markdown table: per-character within-cluster self-sim across all tags
    + the delta vs the first tag (typically V0)."""
    tags = [r["tag"] for r in results if "error" not in r]
    if not tags:
        return "_(no successful runs to compare)_"
    baseline = tags[0]
    # Collect all characters that appear in any tag's per_character_self_sim.
    chars: set[str] = set()
    for r in results:
        chars.update((r.get("per_character_self_sim") or {}).keys())
    if not chars:
        return "_(no characters reached the min-cluster-size threshold)_"

    header_tags = " | ".join(f"{t} self-sim" for t in tags)
    delta_tags = " | ".join(
        f"Δ vs {baseline} ({t})" for t in tags if t != baseline
    )
    sep_tags = " | ".join(["---:"] * len(tags))
    sep_deltas = " | ".join(["---:"] * (len(tags) - 1)) if len(tags) > 1 else ""

    header = f"| character | {header_tags}"
    sep = f"|---| {sep_tags}"
    if len(tags) > 1:
        header += f" | {delta_tags} |"
        sep += f" | {sep_deltas} |"
    else:
        header += " |"
        sep += " |"
    lines = [header, sep]

    # Sort characters by their target-tag's self-sim (descending), so the
    # most rigid characters surface first.
    target_tag = tags[-1]
    target_map = next(
        (r["per_character_self_sim"] or {})
        for r in results if r["tag"] == target_tag
    )

    def sort_key(c: str) -> float:
        v = (target_map.get(c) or {}).get("mean_pairwise_cos")
        return -v if v is not None else 0.0

    for char in sorted(chars, key=sort_key):
        row = [char]
        base_val: float | None = None
        for r in results:
            if "error" in r:
                row.append("—")
                continue
            stats = (r.get("per_character_self_sim") or {}).get(char)
            v = (stats or {}).get("mean_pairwise_cos")
            n = (stats or {}).get("count")
            if v is None:
                row.append("—")
            else:
                row.append(f"{v:.3f} (n={n})")
            if r["tag"] == baseline:
                base_val = v
        # Deltas
        if len(tags) > 1:
            for r in results:
                if r["tag"] == baseline or "error" in r:
                    continue
                stats = (r.get("per_character_self_sim") or {}).get(char)
                v = (stats or {}).get("mean_pairwise_cos")
                if v is None or base_val is None:
                    row.append("—")
                else:
                    delta = v - base_val
                    ratio = (v / base_val) if base_val > 0 else 0.0
                    row.append(f"{delta:+.3f} ({ratio:.2f}×)")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def visual_evidence(
    montage_dir: Path | None, results: list[dict]
) -> str:
    """Embed montage PNGs as markdown image refs, ordered by target-tag
    rigidity (most rigid first so the strongest visual evidence is first)."""
    if not montage_dir:
        return "_(no montage-dir provided)_"
    if not montage_dir.exists():
        return f"_(montage-dir {montage_dir} does not exist)_"

    # Target-tag rigidity ranking
    tags = [r["tag"] for r in results if "error" not in r]
    target_tag = tags[-1] if tags else None
    target_map: dict[str, dict] = {}
    if target_tag is not None:
        target_map = next(
            (r.get("per_character_self_sim") or {})
            for r in results if r["tag"] == target_tag
        )

    lines = []
    montages = sorted(montage_dir.glob("montage_*.png"))
    if not montages:
        return f"_(no montage_*.png found in {montage_dir})_"

    def rigidity(p: Path) -> float:
        char = p.stem.removeprefix("montage_")
        stats = target_map.get(char) or {}
        return -float(stats.get("mean_pairwise_cos") or 0.0)

    for png in sorted(montages, key=rigidity):
        char = png.stem.removeprefix("montage_")
        stats = target_map.get(char) or {}
        v = stats.get("mean_pairwise_cos")
        n = stats.get("count")
        cap = (
            f"{char} — {target_tag} self-sim "
            f"{v:.3f} (n={n})" if v is not None else f"{char}"
        )
        lines.append(f"### {cap}")
        lines.append(f"![{cap}]({png.as_posix()})")
        lines.append("")
    return "\n".join(lines)


def recommend_next(
    results: list[dict],
    baseline_tag: str,
    target_tag: str,
) -> str:
    """One-paragraph recommendation based on the target tag's numbers."""
    target = next((r for r in results if r.get("tag") == target_tag), None)
    base = next((r for r in results if r.get("tag") == baseline_tag), None)
    if not target or "error" in target:
        return f"_(target tag {target_tag} not measurable)_"
    if not base or "error" in base:
        return f"_(baseline tag {baseline_tag} not measurable)_"

    diversity = target.get("inter_shot_diversity_mean_cos") or 0.0
    ref_sim = target.get("ref_sim_best_mean") or 0.0
    per_char = target.get("per_character_self_sim") or {}
    worst_rigidity = max(
        ((stats or {}).get("mean_pairwise_cos") or 0.0)
        for stats in per_char.values()
    ) if per_char else 0.0

    notes = []
    notes.append(
        f"Target {target_tag} worst-cluster rigidity: **{worst_rigidity:.3f}** "
        f"(threshold acceptable < {RIGIDITY_THRESHOLD_ACCEPTABLE:.2f})."
    )
    notes.append(
        f"Target ref_sim_best_mean: **{ref_sim:.3f}** "
        f"(identity floor: > {REF_SIM_IDENTITY_FLOOR:.2f})."
    )
    # inter_shot_diversity is mean pairwise cosine: lower = more diverse.
    # "Floor" here is the ceiling we'd like to stay under.
    notes.append(
        f"Target inter-shot diversity: **{diversity:.3f}** "
        f"(lower = more diverse; prefer ≤ {DIVERSITY_FLOOR + 0.05:.2f})."
    )

    # Recommendation
    if worst_rigidity > RIGIDITY_THRESHOLD_ACCEPTABLE and ref_sim > REF_SIM_IDENTITY_FLOOR:
        rec = (
            "**Rigidity not yet addressed but identity preserved.** "
            "Sweep strength harder: try `face_strength=0.3, "
            "clip_vision_strength=0.3` as V6b. Identity has headroom."
        )
    elif ref_sim < REF_SIM_IDENTITY_FLOOR:
        rec = (
            "**Identity collapsed** — the strength values were too aggressive. "
            "Try `face_strength=1.0` (keep identity tight) + "
            "`clip_vision_strength=0.5` (only the global CLIP-Vision knob) "
            "as V6c. Hypothesis: face attention preserves identity while "
            "CLIP-Vision was the rigidity driver."
        )
    elif worst_rigidity <= RIGIDITY_THRESHOLD_ACCEPTABLE and ref_sim >= REF_SIM_IDENTITY_FLOOR:
        rec = (
            "**Rigidity addressed without losing identity.** Ship a properly-"
            "combined V7: V5 animate + V6a strengths + V3 LLM prompts (PR #68) "
            "+ V2 720p resolution. This is the candidate v1 product config."
        )
    else:
        rec = (
            "**Ambiguous** — numbers don't cleanly match a strategy bucket. "
            "Human review: open the montages, compare to V5, and decide whether "
            "the perceptual quality matches what the numbers suggest."
        )

    return "\n\n".join(["**Recommendation:**", "\n".join(f"- {n}" for n in notes), rec])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scf-json", type=Path, required=True)
    parser.add_argument("--montage-dir", type=Path, default=None,
                        help="Optional. Embeds montage_*.png refs.")
    parser.add_argument("--baseline-tag", default="V0",
                        help="Tag treated as the slop reference.")
    parser.add_argument("--target-tag", default=None,
                        help="Tag treated as 'the new run'. Defaults to the "
                             "last tag in the SCF JSON.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    scf = json.loads(args.scf_json.read_text())
    results = scf.get("results", [])
    if not results:
        print("scf-json has no results — nothing to score", file=sys.stderr)
        return 2

    tags = [r["tag"] for r in results if "tag" in r]
    target_tag = args.target_tag or (tags[-1] if tags else None)

    md_lines: list[str] = []
    md_lines.append(f"# Scorecard — target {target_tag} vs baseline {args.baseline_tag}")
    md_lines.append("")
    md_lines.append(
        f"_Generated {datetime.now(UTC).isoformat()} from "
        f"`{args.scf_json}`._"
    )
    md_lines.append("")
    md_lines.append("## Headline numbers")
    md_lines.append("")
    md_lines.append(headline_table(results))
    md_lines.append("")
    md_lines.append("## Per-character within-cluster self-similarity")
    md_lines.append("")
    md_lines.append(per_character_table(results))
    md_lines.append("")
    md_lines.append("## Visual evidence")
    md_lines.append("")
    md_lines.append(visual_evidence(args.montage_dir, results))
    md_lines.append("")
    md_lines.append("## What to do next")
    md_lines.append("")
    md_lines.append(recommend_next(results, args.baseline_tag, target_tag))
    md_lines.append("")
    md_lines.append("---")
    md_lines.append(
        "_Generated by `scripts/v_scorecard.py`. Companion tools: "
        "`scripts/analyze_scene_context_fidelity.py` (#65), "
        "`scripts/make_rigidity_montage.py` (#66)._"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(md_lines))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
