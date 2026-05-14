"""Across-shot face-identity analysis for the V0 baseline.

Within-shot character_consistency (PR #60) showed V0 is fine WITHIN a
shot — median drift similarity 0.729 across the 76/105 face-bearing
shots, only 1 shot flagged. So if V0 is slop and within-shot identity
is stable, the identity issue must live ACROSS shots: Jack looking
different in scene 1 vs scene 5 vs scene 12.

This script:
  1. Extracts ONE representative face embedding per shot (largest
     face from the middle frame).
  2. Computes the 76x76 pairwise cosine similarity matrix.
  3. Runs DBSCAN clustering to count distinct face-identity clusters.
  4. Reports mean pairwise similarity + cluster summary.

Interpretation:
  - Many tiny clusters / low mean similarity → severe inter-shot drift
    (each shot's "person" is a different person). V5_animate would
    address this directly by using ONE reference image across all
    shots — the metric to beat after V5 runs.
  - Few large clusters / high mean similarity → V0 actually produces
    consistent identities across shots, so the slop is elsewhere
    (composition, motion, or CLIP-level prompt mismatch).
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

os.chdir("/home/user1-gpu")
sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/SceneMachine/packages/core")

logging.basicConfig(level=logging.WARNING)

import numpy as np


def main() -> int:
    import subprocess
    import tempfile
    from scenemachine.services.face_embedding import FaceEmbeddingService

    v2_path = Path("/tmp/scenemachine_loop/V0_per_shot_quality_baseline_v2.json")
    if not v2_path.exists():
        print(f"need v2 baseline at {v2_path}")
        return 1

    v2 = json.loads(v2_path.read_text())
    shots_with_faces = [
        r for r in v2["per_shot"]
        if ((r.get("character_consistency") or {}).get("face_frames") or 0) >= 1
    ]
    print(f"V0 shots with ≥1 face: {len(shots_with_faces)}")

    svc = FaceEmbeddingService(gpu_id=-1)
    if not svc._lazy_init():
        print("InsightFace failed to init")
        return 1

    # For each shot, extract the middle frame and run face detection
    # on it ONLY (much faster than re-extracting 8 frames per shot).
    embeddings = []
    shot_ids = []
    t0 = time.monotonic()

    for i, row in enumerate(shots_with_faces):
        mp4 = Path(row["mp4_path"])
        if not mp4.exists():
            continue

        try:
            dur = float(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", str(mp4)],
                text=True,
            ).strip())
        except Exception:
            continue

        tmpdir = Path(tempfile.mkdtemp(prefix="inter_shot_"))
        mid_frame = tmpdir / "mid.png"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-ss", f"{dur/2:.3f}", "-i", str(mp4),
                 "-update", "1", "-frames:v", "1", str(mid_frame)],
                check=True, timeout=15,
            )
            if not mid_frame.exists():
                continue
            result = svc.extract_embedding(mid_frame, select_largest=True)
            if result.success and result.primary_embedding is not None:
                embeddings.append(result.primary_embedding)
                shot_ids.append(row["shot_id"])
        except Exception as e:
            print(f"  skip {row['shot_id'][:8]}: {e}")
        finally:
            try:
                import shutil as _shutil
                _shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

        if (i + 1) % 10 == 0:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed
            remaining = (len(shots_with_faces) - i - 1) / rate
            print(f"  {i+1}/{len(shots_with_faces)} rate={rate:.2f}/s ETA={remaining:.0f}s")

    n = len(embeddings)
    print(f"extracted {n} representative embeddings in {time.monotonic()-t0:.1f}s")
    if n < 2:
        print("not enough embeddings for pairwise analysis")
        return 1

    # Stack into matrix, normalize, compute pairwise similarity (cosine).
    E = np.stack(embeddings).astype(np.float32)
    norms = np.linalg.norm(E, axis=1, keepdims=True)
    En = E / np.maximum(norms, 1e-9)
    # Raw cosine sim matrix (range [-1, 1])
    sim = En @ En.T
    # Mapped to [0, 1] using (sim + 1) / 2 to match face_embedding.compute_similarity
    sim_mapped = (sim + 1) / 2.0

    # Mean off-diagonal (pairwise)
    iu = np.triu_indices(n, k=1)
    pair_raw = sim[iu]
    pair_mapped = sim_mapped[iu]

    print()
    print("=== V0 INTER-SHOT face-identity similarity ===")
    print(f"  shots analyzed: {n}")
    print(f"  pairwise cosine sim (raw):     min={pair_raw.min():.3f}  mean={pair_raw.mean():.3f}  median={float(np.median(pair_raw)):.3f}  max={pair_raw.max():.3f}")
    print(f"  pairwise cosine sim (mapped):  min={pair_mapped.min():.3f}  mean={pair_mapped.mean():.3f}  median={float(np.median(pair_mapped)):.3f}  max={pair_mapped.max():.3f}")

    # Cluster: a pair is "same identity" if raw cos sim > 0.4 (InsightFace standard)
    same_id_threshold_raw = 0.4
    same_id_pairs = int((pair_raw > same_id_threshold_raw).sum())
    total_pairs = len(pair_raw)
    print()
    print(f"  pairs that look like 'same person' (raw cos > {same_id_threshold_raw}): {same_id_pairs}/{total_pairs}  ({100*same_id_pairs/total_pairs:.1f}%)")

    # Simple greedy clustering on raw cos sim threshold
    # (avoid scikit-learn import overhead)
    cluster_id = [-1] * n
    next_cluster = 0
    for i in range(n):
        if cluster_id[i] >= 0:
            continue
        cluster_id[i] = next_cluster
        for j in range(i + 1, n):
            if cluster_id[j] < 0 and sim[i, j] > same_id_threshold_raw:
                cluster_id[j] = next_cluster
        next_cluster += 1
    from collections import Counter
    sizes = Counter(cluster_id)
    n_clusters = len(sizes)
    biggest = sizes.most_common(5)
    print()
    print(f"  greedy clusters (threshold raw cos > {same_id_threshold_raw}): {n_clusters} total")
    print(f"  top-5 cluster sizes: {biggest}")
    n_singletons = sum(1 for s in sizes.values() if s == 1)
    print(f"  singleton clusters (faces with no match elsewhere): {n_singletons}/{n_clusters}")

    out = {
        "n_shots_analyzed": n,
        "pairwise_cosine_raw": {
            "min": float(pair_raw.min()),
            "mean": float(pair_raw.mean()),
            "median": float(np.median(pair_raw)),
            "max": float(pair_raw.max()),
        },
        "pairwise_cosine_mapped": {
            "min": float(pair_mapped.min()),
            "mean": float(pair_mapped.mean()),
            "median": float(np.median(pair_mapped)),
            "max": float(pair_mapped.max()),
        },
        "same_id_pairs_at_raw_0p4": int(same_id_pairs),
        "total_pairs": int(total_pairs),
        "same_id_pair_fraction": float(same_id_pairs / total_pairs),
        "n_clusters_greedy_raw_0p4": int(n_clusters),
        "top_5_cluster_sizes": [(int(k), int(v)) for k, v in biggest],
        "n_singletons": int(n_singletons),
        "interpretation": (
            f"V0 produces {n_clusters} distinct face-identity clusters across {n} "
            f"face-bearing shots, with {n_singletons} singletons. "
            f"{100*same_id_pairs/total_pairs:.1f}% of all shot pairs look like the "
            f"same person at the InsightFace standard threshold. "
            f"Low % + many singletons ⇒ severe inter-shot identity drift "
            f"(every shot is a different person)."
        ),
    }

    out_path = Path("/tmp/scenemachine_loop/V0_inter_shot_analysis.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")

    try:
        from huggingface_hub import HfApi
        api = HfApi()
        url = api.upload_file(
            path_or_fileobj=str(out_path),
            path_in_repo="benchmarks/V0_2026-05-14/inter_shot_identity_analysis.json",
            repo_id="SceneMachine/operations-log",
            repo_type="model",
            commit_message="V0 inter-shot face-identity analysis: drift across shots",
        )
        print(f"uploaded: {url}")
    except Exception as e:
        print(f"HF upload failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
