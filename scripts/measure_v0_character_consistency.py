"""Measure character_consistency (PR #60) on every V0 shot from the locked baseline.

Reads the existing V0 per-shot baseline JSON (PR #58) — which has
explicit mp4_path entries — runs the new InsightFace-based
character_consistency check on each shot, and writes an enriched
baseline JSON with all 3 real quality dimensions.

This is the definitive test of whether the new metric actually
discriminates V0 slop. If the V0 distribution shows a substantial
fraction below CHARACTER_DRIFT_THRESHOLD=0.55, the V5 hypothesis
(Animate routing fixes identity drift) becomes empirically testable
— V5 should score substantially higher on this metric.

Uses explicit mp4 paths from the V0 baseline (not mtime filtering)
because V1_30steps is running concurrently and writing to the same
output dir.

Runs on CPU only (V1 occupies all GPU VRAM).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import statistics
import sys
import time
from pathlib import Path

os.chdir("/home/user1-gpu")
sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/SceneMachine/packages/core")

logging.basicConfig(level=logging.WARNING)


V0_BASELINE_LOCAL = Path("/tmp/scenemachine_loop/V0_per_shot_quality_baseline.json")


async def main() -> int:
    if not V0_BASELINE_LOCAL.exists():
        print(f"V0 baseline not found at {V0_BASELINE_LOCAL}; run measure_v0_baseline.py first")
        return 1

    v0 = json.loads(V0_BASELINE_LOCAL.read_text())
    print(f"loaded V0 baseline: {v0['n_shots']} shots")

    from scenemachine.services.video_quality_reviewer import VideoQualityReviewer
    rev = VideoQualityReviewer()

    char_sims = []
    n_flagged = 0
    n_with_faces = 0
    n_no_faces = 0
    n_errors = 0

    t0 = time.monotonic()
    enriched_rows = []
    for i, row in enumerate(v0["per_shot"]):
        mp4 = Path(row["mp4_path"])
        if not mp4.exists():
            row["character_consistency"] = {"error": "mp4 not on disk"}
            n_errors += 1
            enriched_rows.append(row)
            continue

        try:
            result = await rev._check_character_consistency(mp4, None)
        except Exception as e:
            row["character_consistency"] = {"error": str(e)}
            n_errors += 1
            enriched_rows.append(row)
            continue

        # Pull the drift value from the notes if present
        drift_val = None
        try:
            if "drift=" in result.notes:
                drift_val = float(result.notes.split("drift=")[1].split(" ")[0])
        except Exception:
            pass

        face_frames = None
        try:
            if "face_frames=" in result.notes:
                face_frames = result.notes.split("face_frames=")[1].split("/")[0]
                face_frames = int(face_frames)
        except Exception:
            pass

        row["character_consistency"] = {
            "score": result.score,
            "confidence": result.confidence,
            "drift_similarity": drift_val,
            "face_frames": face_frames,
            "issues": [issue.value for issue in result.issues],
        }
        enriched_rows.append(row)

        if face_frames is not None and face_frames >= 2:
            n_with_faces += 1
            if drift_val is not None:
                char_sims.append(drift_val)
        else:
            n_no_faces += 1

        if "character_drift" in row["character_consistency"]["issues"]:
            n_flagged += 1

        if (i + 1) % 10 == 0:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(v0["per_shot"]) - i - 1) / rate if rate > 0 else 0
            print(f"  {i+1}/{len(v0['per_shot'])} rate={rate:.2f}/s ETA={remaining:.0f}s")

    elapsed = time.monotonic() - t0
    print(f"measured {len(enriched_rows)} shots in {elapsed:.1f}s")

    char_stats = {
        "min": min(char_sims) if char_sims else None,
        "median": statistics.median(char_sims) if char_sims else None,
        "mean": statistics.mean(char_sims) if char_sims else None,
        "max": max(char_sims) if char_sims else None,
        "stdev": statistics.stdev(char_sims) if len(char_sims) > 1 else None,
        "n": len(char_sims),
    }

    v0["character_consistency_drift_similarity"] = char_stats
    v0["character_consistency_summary"] = {
        "shots_with_measurable_drift": n_with_faces,
        "shots_without_faces": n_no_faces,
        "shots_errored": n_errors,
        "shots_flagged_character_drift": n_flagged,
        "threshold_used": 0.55,
    }
    v0["per_shot"] = enriched_rows
    v0["enriched_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    out = Path("/tmp/scenemachine_loop/V0_per_shot_quality_baseline_v2.json")
    out.write_text(json.dumps(v0, indent=2))
    print(f"wrote {out} ({out.stat().st_size} bytes)")

    print()
    print("=== V0 character_consistency baseline ===")
    print(f"  shots measured:                {len(enriched_rows)}")
    print(f"  shots with ≥2 face frames:     {n_with_faces}")
    print(f"  shots with NO faces:           {n_no_faces}")
    print(f"  shots errored:                 {n_errors}")
    print(f"  shots flagged CHARACTER_DRIFT: {n_flagged}/{n_with_faces}  (threshold 0.55)")
    if char_sims:
        print(f"  drift sim  min={char_stats['min']:.3f}  median={char_stats['median']:.3f}  mean={char_stats['mean']:.3f}  max={char_stats['max']:.3f}")

    try:
        from huggingface_hub import HfApi
        api = HfApi()
        url = api.upload_file(
            path_or_fileobj=str(out),
            path_in_repo="benchmarks/V0_2026-05-14/per_shot_quality_baseline_v2.json",
            repo_id="SceneMachine/operations-log",
            repo_type="model",
            commit_message="V0 baseline enriched with character_consistency (PR #60)",
        )
        print(f"uploaded to HF: {url}")
    except Exception as e:
        print(f"HF upload failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
