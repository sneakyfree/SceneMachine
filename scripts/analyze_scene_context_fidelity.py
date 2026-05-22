"""Scene-context fidelity metric: did Animate routing ate the scene?

Hypothesis from V5_animate memory (2026-05-15):
  Wan 2.2 Animate fixed inter-shot character drift (V0's "47 different
  Jacks" failure mode) but may have introduced a NEW failure: shots
  reproducing the character reference too rigidly and losing scene
  context. That claim was based on one viewing — not measured. This
  script measures it.

What it measures (image-only, no text prompts needed):
  1. ref_sim_mean: for shots whose middle frame contains a recognizable
     face matching a known reference, CLIP cosine of (frame, ref).
     High = frame closely resembles the reference photo.
  2. inter_shot_diversity_mean: pairwise CLIP cosine across ALL 47
     middle frames. High mean cosine = shots look similar to each
     other (low diversity); low = shots are visually distinct.

Interpretation matrix:
  ref_sim   diversity     read
  ────────  ──────────    ─────────────────────────────────────────
  low       high          slop — random frames, no shared identity (V0)
  low       low           homogeneous slop — all shots look samey
  high      high          ideal — characters recognizable AND scenes vary
  high      low           the "rigid Animate" failure — every shot is
                          basically the same portrait of the same ref

Usage:
  /opt/ai/comfyui/venv/bin/python scripts/analyze_scene_context_fidelity.py \\
    --tag V0 --mp4 /home/user1-gpu/scenemachine_movies/RADAR_LOVE_2/final.mp4 \\
    --tag V1 --mp4 .../benchmarks/V1_30steps/RADAR_LOVE_2/final.mp4 \\
    --tag V5 --mp4 .../benchmarks/V5_animate/RADAR_LOVE_2/final.mp4 \\
    --refs /home/user1-gpu/scenemachine_movies/character_refs/RADAR_LOVE_2 \\
    --shots 47 \\
    --out scene_context_fidelity_RADAR_LOVE_2.json

Runs on whatever device transformers picks (GPU if available).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"  # 600MB; large-patch14 = 1.7GB if we want fidelity


@dataclass
class ShotMeasurement:
    shot_idx: int
    middle_time_s: float
    frame_path: str
    ref_sim_best: float | None = None  # cosine to the best-matching ref
    ref_sim_best_label: str | None = None
    ref_sims_all: dict[str, float] = field(default_factory=dict)


def extract_middle_frame(mp4: Path, t_seconds: float, out_path: Path) -> None:
    """ffmpeg seek + extract single frame as PNG. Stays loud on failure
    per no-silent-fallbacks rule — caller should not get an empty PNG."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{t_seconds:.3f}",
        "-i", str(mp4),
        "-frames:v", "1",
        "-q:v", "2",
        "-loglevel", "error",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 1024:
        raise RuntimeError(
            f"ffmpeg failed extracting t={t_seconds}s from {mp4}\n"
            f"stderr: {res.stderr}\n"
            f"stdout: {res.stdout}\n"
            f"out_path size: {out_path.stat().st_size if out_path.exists() else 'missing'}"
        )


def load_images(paths: list[Path]) -> list[Image.Image]:
    return [Image.open(p).convert("RGB") for p in paths]


def encode_images(model: CLIPModel, processor: CLIPProcessor, images: list[Image.Image],
                  device: torch.device, batch_size: int = 16) -> torch.Tensor:
    """Return L2-normalized image embeddings as a (N, dim) tensor.

    Implementation note: avoids ``get_image_features`` because some
    transformers versions return a ``BaseModelOutputWithPooling``
    instead of a tensor. We project the pooler output ourselves through
    ``model.visual_projection`` to get the same image-embedding tensor.
    """
    all_emb: list[torch.Tensor] = []
    for i in range(0, len(images), batch_size):
        batch = images[i:i + batch_size]
        inputs = processor(images=batch, return_tensors="pt").to(device)
        with torch.no_grad():
            vision_out = model.vision_model(pixel_values=inputs["pixel_values"])
            pooled = vision_out.pooler_output  # (B, vision_dim)
            emb = model.visual_projection(pooled)  # (B, projection_dim)
        emb = emb / emb.norm(dim=-1, keepdim=True)
        all_emb.append(emb.cpu())
    return torch.cat(all_emb, dim=0)


def pairwise_cos_mean(emb: torch.Tensor) -> float:
    """Mean of pairwise cosine similarity, excluding the diagonal."""
    sim = emb @ emb.T
    n = sim.shape[0]
    mask = ~torch.eye(n, dtype=torch.bool)
    return float(sim[mask].mean().item())


def measure_one(
    tag: str,
    mp4: Path,
    refs_dir: Path | None,
    shots: int,
    tmpdir: Path,
    model: CLIPModel,
    processor: CLIPProcessor,
    device: torch.device,
) -> dict:
    """Extract middle frames, encode, compute ref_sim and diversity."""
    # ffprobe duration for per-shot time
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(mp4),
    ]).strip())
    shot_dur = duration / shots
    print(f"[{tag}] mp4={mp4.name} duration={duration:.3f}s shots={shots} "
          f"shot_dur={shot_dur:.3f}s")

    # Extract every middle frame
    tag_dir = tmpdir / tag
    tag_dir.mkdir(parents=True, exist_ok=True)
    measurements: list[ShotMeasurement] = []
    for i in range(shots):
        t = (i + 0.5) * shot_dur
        fp = tag_dir / f"shot_{i:03d}.png"
        extract_middle_frame(mp4, t, fp)
        measurements.append(ShotMeasurement(
            shot_idx=i, middle_time_s=round(t, 3), frame_path=str(fp),
        ))
    print(f"[{tag}] extracted {len(measurements)} middle frames")

    # CLIP-encode all middle frames
    frame_paths = [Path(m.frame_path) for m in measurements]
    frame_images = load_images(frame_paths)
    frame_emb = encode_images(model, processor, frame_images, device)
    print(f"[{tag}] encoded shape={tuple(frame_emb.shape)}")

    # Inter-shot diversity (pairwise mean cosine across all 47 middle frames)
    inter_shot_mean = pairwise_cos_mean(frame_emb)

    # Reference matching: for every ref image, CLIP-encode and compute cosine
    # to every middle frame. Best-matching ref per shot wins.
    ref_emb_by_label: dict[str, torch.Tensor] = {}
    if refs_dir and refs_dir.is_dir():
        ref_paths = sorted(refs_dir.glob("*.png"))
        if ref_paths:
            ref_images = load_images(ref_paths)
            ref_emb = encode_images(model, processor, ref_images, device)
            for j, p in enumerate(ref_paths):
                ref_emb_by_label[p.stem] = ref_emb[j]
            print(f"[{tag}] encoded {len(ref_paths)} refs: "
                  f"{[p.stem for p in ref_paths]}")

            # For each middle frame: cosine to every ref
            for i, m in enumerate(measurements):
                f_emb = frame_emb[i]
                sims = {label: float((f_emb @ e).item())
                        for label, e in ref_emb_by_label.items()}
                m.ref_sims_all = sims
                best_label = max(sims, key=sims.get)
                m.ref_sim_best = sims[best_label]
                m.ref_sim_best_label = best_label
        else:
            print(f"[{tag}] WARN refs_dir {refs_dir} has no PNGs")
    else:
        print(f"[{tag}] no refs_dir given — skipping ref_sim")

    # Aggregate
    ref_sims_best = [m.ref_sim_best for m in measurements
                     if m.ref_sim_best is not None]
    ref_sim_mean = (sum(ref_sims_best) / len(ref_sims_best)
                    if ref_sims_best else None)
    ref_sim_max = max(ref_sims_best) if ref_sims_best else None
    ref_sim_min = min(ref_sims_best) if ref_sims_best else None

    # Per-character coverage: how many shots best-match each ref?
    coverage: dict[str, int] = {}
    for m in measurements:
        if m.ref_sim_best_label:
            coverage[m.ref_sim_best_label] = coverage.get(
                m.ref_sim_best_label, 0) + 1

    # Within-character self-similarity: for each character with >=3 shots
    # best-matching it, compute the mean pairwise cosine across those
    # shots' middle frames. Very high (>~0.85) = Animate reproducing the
    # SAME shot repeatedly (rigid). Normal (~0.6-0.75) = different scenes
    # of the same person.
    per_character_self_sim: dict[str, dict[str, float]] = {}
    for label, count in coverage.items():
        if count < 3:
            continue
        idxs = [i for i, m in enumerate(measurements)
                if m.ref_sim_best_label == label]
        cluster_emb = frame_emb[idxs]
        cluster_self = pairwise_cos_mean(cluster_emb)
        per_character_self_sim[label] = {
            "count": count,
            "mean_pairwise_cos": round(cluster_self, 4),
        }

    summary = {
        "tag": tag,
        "mp4_path": str(mp4),
        "duration_s": round(duration, 3),
        "shots": shots,
        "shot_dur_s": round(shot_dur, 3),
        "clip_model": CLIP_MODEL_ID,
        "inter_shot_diversity_mean_cos": round(inter_shot_mean, 4),
        "ref_sim_best_mean": round(ref_sim_mean, 4) if ref_sim_mean is not None else None,
        "ref_sim_best_max": round(ref_sim_max, 4) if ref_sim_max is not None else None,
        "ref_sim_best_min": round(ref_sim_min, 4) if ref_sim_min is not None else None,
        "best_ref_coverage": coverage,
        "per_character_self_sim": per_character_self_sim,
        "per_shot": [asdict(m) for m in measurements],
    }
    print(f"[{tag}] inter_shot_diversity_mean_cos={inter_shot_mean:.4f}  "
          f"ref_sim_best_mean={ref_sim_mean}  coverage={coverage}")
    for label, stats in per_character_self_sim.items():
        print(f"[{tag}]   within-{label} (n={stats['count']}): "
              f"mean_pairwise_cos={stats['mean_pairwise_cos']:.4f}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", action="append", required=True,
                        help="One per --mp4. Order must match.")
    parser.add_argument("--mp4", action="append", required=True, type=Path)
    parser.add_argument("--refs", type=Path, required=True,
                        help="Dir of <character_id>.png files")
    parser.add_argument("--shots", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--keep-frames", action="store_true",
                        help="Don't delete the extracted middle-frame PNGs")
    args = parser.parse_args()

    if len(args.tag) != len(args.mp4):
        print(f"--tag count {len(args.tag)} != --mp4 count {len(args.mp4)}")
        return 2

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}  model={CLIP_MODEL_ID}")
    model = CLIPModel.from_pretrained(CLIP_MODEL_ID).to(device).eval()
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID)

    workdir = Path(tempfile.mkdtemp(prefix="scf_"))
    print(f"workdir={workdir}")

    results: list[dict] = []
    for tag, mp4 in zip(args.tag, args.mp4, strict=True):
        if not mp4.exists():
            print(f"SKIP {tag}: {mp4} does not exist")
            continue
        try:
            summary = measure_one(
                tag=tag, mp4=mp4, refs_dir=args.refs, shots=args.shots,
                tmpdir=workdir, model=model, processor=processor, device=device,
            )
            results.append(summary)
        except Exception as e:
            print(f"ERROR on {tag}: {e}")
            results.append({"tag": tag, "mp4_path": str(mp4), "error": str(e)})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"results": results}, indent=2))
    print(f"\nResults → {args.out}")

    # Cross-tag comparison
    print("\n" + "=" * 78)
    print(f"{'tag':<6} {'inter_shot_diversity':>22} {'ref_sim_mean':>14} "
          f"{'ref_sim_max':>14}")
    print("=" * 78)
    for r in results:
        if "error" in r:
            print(f"{r['tag']:<6} ERROR: {r['error']}")
            continue
        print(f"{r['tag']:<6} {r['inter_shot_diversity_mean_cos']:>22.4f} "
              f"{r['ref_sim_best_mean'] or 0:>14.4f} "
              f"{r['ref_sim_best_max'] or 0:>14.4f}")

    if not args.keep_frames:
        import shutil
        shutil.rmtree(workdir)
        print(f"removed workdir {workdir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
