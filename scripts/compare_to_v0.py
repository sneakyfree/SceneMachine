"""Compare a benchmark version's quality scores against the locked V0 baseline.

Designed to run the moment a V_N benchmark finishes. Loads the V0
per-shot baseline from disk (or HF), measures the V_N shots with the
same metrics, and emits:

  1. A per-shot table: shot_id | V0_sharp | V_N_sharp | Δ | V0_cov | V_N_cov | Δ
  2. Distribution summary (median/mean/max for both versions)
  3. Win/loss/tie counts per metric
  4. A JSON dump for downstream consumption + HF upload

V0 baseline source priority:
  1. /tmp/scenemachine_loop/V0_per_shot_quality_baseline.json (local)
  2. HF: SceneMachine/operations-log/benchmarks/V0_2026-05-14/per_shot_quality_baseline.json
  3. Error out — we will not compare to a phantom baseline.

Usage:
    python scripts/compare_to_v0.py V1_30steps
    python scripts/compare_to_v0.py V1_30steps --screenplay RADAR_LOVE_2

Per Grant's directive (2026-05-14): "we will just keep using the same
two screenplays so we can track... they will be our benchmark base
control group screenplays."
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

os.chdir("/home/user1-gpu")
sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/SceneMachine/packages/core")

logging.basicConfig(level=logging.WARNING)


V0_LOCAL_PATH = Path("/tmp/scenemachine_loop/V0_per_shot_quality_baseline.json")
V0_HF_REPO = "SceneMachine/operations-log"
V0_HF_PATH = "benchmarks/V0_2026-05-14/per_shot_quality_baseline.json"


def load_v0_baseline() -> Dict[str, Any]:
    """Return the V0 baseline JSON. Tries local then HF."""
    if V0_LOCAL_PATH.exists():
        print(f"loaded V0 baseline from {V0_LOCAL_PATH}")
        return json.loads(V0_LOCAL_PATH.read_text())

    try:
        from huggingface_hub import hf_hub_download
        local = hf_hub_download(
            repo_id=V0_HF_REPO,
            filename=V0_HF_PATH,
            repo_type="model",
        )
        print(f"downloaded V0 baseline from HF: {local}")
        return json.loads(Path(local).read_text())
    except Exception as e:
        raise RuntimeError(
            f"V0 baseline not at {V0_LOCAL_PATH} and HF fetch failed: {e}. "
            "Cannot compare to a phantom V0 — refusing."
        )


def find_vn_shot_mp4s(version_tag: str, screenplay: Optional[str]) -> List[Path]:
    """Locate V_N shot mp4s. Two layouts supported, in this order:

      1. /home/user1-gpu/scenemachine_movies/benchmarks/<TAG>/<SCREENPLAY>/shots/*/output.mp4
         — the layout run_benchmark.py uses for V_N runs.

      2. /home/user1-gpu/data/outputs/shots/*/output.mp4 with mtime after a
         per-version cutoff (V0 fallback layout — only honored if --screenplay
         is unset).
    """
    bench_root = Path("/home/user1-gpu/scenemachine_movies/benchmarks") / version_tag
    if bench_root.exists():
        if screenplay:
            shots_dir = bench_root / screenplay / "shots"
            if not shots_dir.exists():
                raise FileNotFoundError(f"no shots dir at {shots_dir}")
            return sorted(shots_dir.glob("*/output.mp4"))
        # all screenplays under that V_N
        return sorted(bench_root.glob("*/shots/*/output.mp4"))

    raise FileNotFoundError(
        f"No benchmark output found at {bench_root}. "
        f"Run `python scripts/run_benchmark.py {version_tag}` first."
    )


async def measure_shots(mp4_paths: List[Path]) -> List[Dict[str, Any]]:
    """Run the same two metrics that produced the V0 baseline."""
    from scenemachine.services.video_quality_reviewer import VideoQualityReviewer

    rev = VideoQualityReviewer()
    out: List[Dict[str, Any]] = []
    t0 = time.monotonic()

    for i, mp4 in enumerate(mp4_paths):
        shot_id = mp4.parent.name
        vis = await rev._check_visual_fidelity(mp4)
        tmp = await rev._check_temporal_stability(mp4)

        sharp_var = None
        try:
            sharp_var = float(vis.notes.split("mean_laplacian_variance=")[1].split(" ")[0])
        except Exception:
            pass
        cov_val = None
        try:
            cov_val = float(tmp.notes.split("frame_delta_CoV=")[1].split(" ")[0])
        except Exception:
            pass

        out.append({
            "shot_id": shot_id,
            "mp4_path": str(mp4),
            "mp4_bytes": mp4.stat().st_size,
            "sharpness": {
                "score": vis.score,
                "confidence": vis.confidence,
                "laplacian_variance": sharp_var,
                "issues": [issue.value for issue in vis.issues],
            },
            "temporal_stability": {
                "score": tmp.score,
                "confidence": tmp.confidence,
                "frame_delta_cov": cov_val,
                "issues": [issue.value for issue in tmp.issues],
            },
        })

        if (i + 1) % 10 == 0:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(mp4_paths) - i - 1) / rate if rate > 0 else 0
            print(f"  {i+1}/{len(mp4_paths)} rate={rate:.2f}/s ETA={remaining:.0f}s")

    return out


def _stats(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "median": None, "mean": None, "max": None, "n": 0}
    return {
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "max": max(values),
        "n": len(values),
    }


def build_comparison(
    v0: Dict[str, Any],
    vn_rows: List[Dict[str, Any]],
    version_tag: str,
) -> Dict[str, Any]:
    """Pair V_N shots to V0 shots by shot_id (exact match). Shots that
    don't match are reported under unmatched_*; this is informational —
    a different version may pick different shot_ids."""
    v0_by_id = {r["shot_id"]: r for r in v0["per_shot"]}

    paired: List[Dict[str, Any]] = []
    unmatched_vn: List[str] = []
    sharp_deltas: List[float] = []
    cov_deltas: List[float] = []
    sharp_wins = sharp_losses = sharp_ties = 0
    cov_wins = cov_losses = cov_ties = 0

    for vn in vn_rows:
        v0_row = v0_by_id.get(vn["shot_id"])
        if not v0_row:
            unmatched_vn.append(vn["shot_id"])
            continue

        v0_sharp = v0_row["sharpness"]["laplacian_variance"]
        vn_sharp = vn["sharpness"]["laplacian_variance"]
        sd = (vn_sharp - v0_sharp) if (v0_sharp is not None and vn_sharp is not None) else None
        if sd is not None:
            sharp_deltas.append(sd)
            if sd > 5: sharp_wins += 1
            elif sd < -5: sharp_losses += 1
            else: sharp_ties += 1

        v0_cov = v0_row["temporal_stability"]["frame_delta_cov"]
        vn_cov = vn["temporal_stability"]["frame_delta_cov"]
        cd = (vn_cov - v0_cov) if (v0_cov is not None and vn_cov is not None) else None
        if cd is not None:
            cov_deltas.append(cd)
            # For CoV, LOWER is better
            if cd < -0.02: cov_wins += 1
            elif cd > 0.02: cov_losses += 1
            else: cov_ties += 1

        paired.append({
            "shot_id": vn["shot_id"],
            "sharpness": {"v0": v0_sharp, "vn": vn_sharp, "delta": sd},
            "temporal_cov": {"v0": v0_cov, "vn": vn_cov, "delta": cd},
        })

    unmatched_v0 = sorted(set(v0_by_id) - {r["shot_id"] for r in vn_rows})

    vn_sharp_values = [r["sharpness"]["laplacian_variance"] for r in vn_rows if r["sharpness"]["laplacian_variance"] is not None]
    vn_cov_values = [r["temporal_stability"]["frame_delta_cov"] for r in vn_rows if r["temporal_stability"]["frame_delta_cov"] is not None]

    return {
        "version_tag": version_tag,
        "compared_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "v0_baseline_n": v0.get("n_shots"),
        "vn_n": len(vn_rows),
        "n_paired": len(paired),
        "n_vn_unmatched": len(unmatched_vn),
        "n_v0_unmatched": len(unmatched_v0),
        "vn_distribution": {
            "sharpness": _stats(vn_sharp_values),
            "temporal_cov": _stats(vn_cov_values),
        },
        "v0_distribution": {
            "sharpness": v0.get("sharpness_laplacian_variance"),
            "temporal_cov": v0.get("temporal_stability_frame_delta_cov"),
        },
        "paired_delta_distribution": {
            "sharpness": _stats(sharp_deltas),
            "temporal_cov": _stats(cov_deltas),
        },
        "win_loss": {
            "sharpness": {"vn_wins": sharp_wins, "vn_losses": sharp_losses, "ties": sharp_ties},
            "temporal_cov_lower_better": {"vn_wins": cov_wins, "vn_losses": cov_losses, "ties": cov_ties},
        },
        "paired_shots": paired,
        "unmatched_vn_shot_ids": unmatched_vn,
        "unmatched_v0_shot_ids": unmatched_v0,
    }


def print_summary(report: Dict[str, Any]) -> None:
    vt = report["version_tag"]
    print()
    print("=" * 72)
    print(f"  Comparison: {vt}  vs  V0_2026-05-14")
    print("=" * 72)
    print(f"  V0 shots: {report['v0_baseline_n']}   {vt} shots: {report['vn_n']}   paired: {report['n_paired']}")
    if report["n_vn_unmatched"]:
        print(f"  {vt} shots not in V0: {report['n_vn_unmatched']}")
    if report["n_v0_unmatched"]:
        print(f"  V0 shots not in {vt}: {report['n_v0_unmatched']}")
    print()

    print("  Sharpness (Laplacian variance, HIGHER better):")
    vs0 = report["v0_distribution"]["sharpness"] or {}
    vsn = report["vn_distribution"]["sharpness"]
    print(f"    V0      median={vs0.get('median', 0):>7.1f}  mean={vs0.get('mean', 0):>7.1f}  max={vs0.get('max', 0):>7.1f}")
    if vsn["median"] is not None:
        print(f"    {vt:<7} median={vsn['median']:>7.1f}  mean={vsn['mean']:>7.1f}  max={vsn['max']:>7.1f}")
    wl = report["win_loss"]["sharpness"]
    print(f"    paired Δ: {vt} wins={wl['vn_wins']}  losses={wl['vn_losses']}  ties={wl['ties']}")
    print()

    print("  Temporal CoV (LOWER better):")
    vt0 = report["v0_distribution"]["temporal_cov"] or {}
    vtn = report["vn_distribution"]["temporal_cov"]
    print(f"    V0      median={vt0.get('median', 0):>7.3f}  mean={vt0.get('mean', 0):>7.3f}  max={vt0.get('max', 0):>7.3f}")
    if vtn["median"] is not None:
        print(f"    {vt:<7} median={vtn['median']:>7.3f}  mean={vtn['mean']:>7.3f}  max={vtn['max']:>7.3f}")
    wl = report["win_loss"]["temporal_cov_lower_better"]
    print(f"    paired Δ: {vt} wins={wl['vn_wins']}  losses={wl['vn_losses']}  ties={wl['ties']}")
    print()

    print("  Honesty reminder:")
    print("    These two metrics did NOT distinguish V0 (graded 1/5 slop)")
    print("    from a hypothetical 5/5 version on the 2026-05-14 baseline.")
    print("    Treat the verdict as 'no regression on spatial/temporal pixel stats'")
    print("    until character_consistency + prompt_adherence land.")
    print("=" * 72)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_tag", help="Benchmark tag (e.g. V1_30steps)")
    parser.add_argument("--screenplay", default=None, help="Limit to one screenplay (e.g. RADAR_LOVE_2)")
    parser.add_argument("--no-upload", action="store_true", help="Skip HF upload")
    args = parser.parse_args()

    v0 = load_v0_baseline()

    mp4_paths = find_vn_shot_mp4s(args.version_tag, args.screenplay)
    print(f"{args.version_tag}: {len(mp4_paths)} shot mp4s found")
    if not mp4_paths:
        print("nothing to measure; exiting")
        return 1

    vn_rows = await measure_shots(mp4_paths)
    report = build_comparison(v0, vn_rows, args.version_tag)
    print_summary(report)

    out_path = Path(f"/tmp/scenemachine_loop/{args.version_tag}_vs_V0_comparison.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"wrote {out_path}  ({out_path.stat().st_size} bytes)")

    if not args.no_upload:
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            url = api.upload_file(
                path_or_fileobj=str(out_path),
                path_in_repo=f"benchmarks/{args.version_tag}/comparison_to_V0.json",
                repo_id="SceneMachine/operations-log",
                repo_type="model",
                commit_message=f"{args.version_tag} comparison to V0 baseline",
            )
            print(f"uploaded to HF: {url}")
        except Exception as e:
            print(f"HF upload failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
