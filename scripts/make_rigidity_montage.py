"""Rigidity-montage tool — render V0/V1/V5(/V6a/...) side-by-side per character.

Consumes the JSON produced by ``scripts/analyze_scene_context_fidelity.py``
plus a tag → mp4 mapping, and emits one PNG per character cluster showing
that character's best-matching shots across versions. Designed so Grant
can SEE the within-character rigidity (V5's "every shot of Ellie is the
same portrait") that the SCF numbers describe.

Per-character output layout::

  [V0]  [shot a][shot b][shot c]…
  [V1]  [shot d][shot e][shot f]…
  [V5]  [shot g][shot h][shot i]…
  [V6a] [shot j][shot k][shot l]…   (when available)

Within-row order is by sequence (low shot_idx first); cells are middle
frames re-extracted via ffmpeg from each tag's assembled final.mp4. The
tool tolerates clusters of different sizes — short rows are left-aligned
and the longest one sets the grid width.

Usage::

    python scripts/make_rigidity_montage.py \\
      --scf-json .../scene_context_fidelity_RADAR_LOVE_2.json \\
      --mp4 V0=.../RADAR_LOVE_2/final.mp4 \\
      --mp4 V1=.../benchmarks/V1_30steps/RADAR_LOVE_2/final.mp4 \\
      --mp4 V5=.../benchmarks/V5_animate/RADAR_LOVE_2/final.mp4 \\
      --out-dir .../benchmarks/rigidity_montage_RADAR_LOVE_2 \\
      --max-per-row 8 \\
      --min-cluster-size 3
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

THUMB_W = 320
THUMB_H = 180  # 16:9
LABEL_W = 110
ROW_PADDING = 8
HEADER_H = 36


def extract_middle_frame(mp4: Path, shot_idx: int, shots: int, out_path: Path) -> None:
    """Extract the middle frame of shot N from an N-shots concatenated mp4."""
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(mp4),
    ]).strip())
    shot_dur = duration / shots
    t = (shot_idx + 0.5) * shot_dur
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{t:.3f}",
        "-i", str(mp4),
        "-frames:v", "1",
        "-q:v", "2",
        "-loglevel", "error",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 1024:
        raise RuntimeError(
            f"ffmpeg failed (rc={res.returncode}) extracting shot {shot_idx} "
            f"from {mp4} at t={t:.3f}s\nstderr: {res.stderr}"
        )


def _load_font(size: int) -> ImageFont.ImageFont:
    """Best-effort font load. Falls back to PIL default if no TTF found."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def render_character_montage(
    character: str,
    tag_order: list[str],
    tag_to_idxs: dict[str, list[int]],
    tag_to_mp4: dict[str, Path],
    shots: int,
    max_per_row: int,
    workdir: Path,
    out_path: Path,
) -> None:
    """Render one character's montage. Skips a tag if its cluster is empty."""
    # Truncate to max_per_row per tag; preserve original sequence order.
    rendered_tags: list[tuple[str, list[int]]] = []
    for tag in tag_order:
        idxs = sorted(tag_to_idxs.get(tag, []))[:max_per_row]
        if idxs:
            rendered_tags.append((tag, idxs))

    if not rendered_tags:
        print(f"[{character}] no shots in any tag — skipping")
        return

    grid_cols = max(len(idxs) for _, idxs in rendered_tags)
    grid_rows = len(rendered_tags)

    img_w = LABEL_W + grid_cols * (THUMB_W + ROW_PADDING) + ROW_PADDING
    img_h = HEADER_H + grid_rows * (THUMB_H + ROW_PADDING) + ROW_PADDING
    canvas = Image.new("RGB", (img_w, img_h), color=(20, 20, 24))
    draw = ImageDraw.Draw(canvas)

    title_font = _load_font(22)
    label_font = _load_font(18)
    idx_font = _load_font(12)

    # Header
    title = (
        f"{character} — within-cluster shots (best-matching ref)  "
        f"·  {grid_cols}/row max  ·  V0/V1/V5 baseline"
    )
    draw.text((ROW_PADDING, 8), title, fill=(220, 220, 220), font=title_font)

    # Render each row
    for r, (tag, idxs) in enumerate(rendered_tags):
        y = HEADER_H + r * (THUMB_H + ROW_PADDING) + ROW_PADDING
        # Row label (tag name)
        draw.text(
            (ROW_PADDING, y + THUMB_H // 2 - 12),
            tag,
            fill=(180, 220, 255),
            font=label_font,
        )
        for c, shot_idx in enumerate(idxs):
            cell_path = workdir / f"{tag}_shot_{shot_idx:03d}.png"
            if not cell_path.exists():
                extract_middle_frame(
                    tag_to_mp4[tag], shot_idx, shots, cell_path,
                )
            thumb = Image.open(cell_path).convert("RGB")
            thumb = thumb.resize((THUMB_W, THUMB_H), Image.LANCZOS)
            x = LABEL_W + c * (THUMB_W + ROW_PADDING)
            canvas.paste(thumb, (x, y))
            # Per-cell shot index for traceability
            draw.text(
                (x + 4, y + 4),
                f"#{shot_idx}",
                fill=(255, 255, 255),
                font=idx_font,
                stroke_width=1,
                stroke_fill=(0, 0, 0),
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    cluster_summary = ", ".join(f"{tag}={len(idxs)}" for tag, idxs in rendered_tags)
    print(f"[{character}] saved {out_path}  ({cluster_summary})")


def parse_mp4_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"--mp4 expects TAG=PATH, got {value!r}"
        )
    tag, _, path = value.partition("=")
    return tag.strip(), Path(path.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scf-json", type=Path, required=True,
                        help="JSON from analyze_scene_context_fidelity.py")
    parser.add_argument("--mp4", action="append", required=True,
                        type=parse_mp4_arg,
                        help="TAG=PATH; one per version (e.g. V0=.../final.mp4)")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-per-row", type=int, default=8,
                        help="Cap shots-per-row to keep image width sane.")
    parser.add_argument("--min-cluster-size", type=int, default=3,
                        help="Skip characters whose largest tag cluster is "
                             "smaller than this.")
    parser.add_argument("--characters", nargs="*", default=None,
                        help="Restrict to these character IDs.")
    parser.add_argument("--keep-frames", action="store_true",
                        help="Don't delete extracted middle-frame PNGs.")
    args = parser.parse_args()

    scf = json.loads(args.scf_json.read_text())
    tag_to_mp4: dict[str, Path] = dict(args.mp4)
    tag_order = list(tag_to_mp4.keys())

    # Build {character → {tag → [shot_idxs]}} from SCF per_shot entries.
    by_char: dict[str, dict[str, list[int]]] = {}
    shots_per_tag: dict[str, int] = {}
    for tag_data in scf["results"]:
        tag = tag_data.get("tag")
        if tag is None or tag not in tag_to_mp4:
            continue
        shots_per_tag[tag] = int(tag_data.get("shots", 0))
        for m in tag_data.get("per_shot", []):
            label = m.get("ref_sim_best_label")
            if not label:
                continue
            by_char.setdefault(label, {}).setdefault(tag, []).append(
                int(m["shot_idx"])
            )

    if args.characters:
        by_char = {c: by_char.get(c, {}) for c in args.characters}

    # Drop characters with no cluster reaching the min size.
    filtered: dict[str, dict[str, list[int]]] = {}
    for char, tag_map in by_char.items():
        max_cluster = max((len(v) for v in tag_map.values()), default=0)
        if max_cluster >= args.min_cluster_size:
            filtered[char] = tag_map
        else:
            print(f"[{char}] skip (max cluster {max_cluster} < "
                  f"{args.min_cluster_size})")

    if not filtered:
        print("No characters cleared the min-cluster-size filter; nothing to do.")
        return 1

    workdir = Path(tempfile.mkdtemp(prefix="rigidity_montage_"))
    print(f"workdir={workdir}")

    # All tag mp4s should agree on shot count (the metric runs on each
    # version with the same --shots), but use the per-tag value defensively.
    if len(set(shots_per_tag.values())) > 1:
        print(f"WARN per-tag shot counts disagree: {shots_per_tag} "
              f"— using majority for ffprobe.")
    shots = max(shots_per_tag.values()) if shots_per_tag else 47

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for char, tag_map in sorted(filtered.items()):
        out_path = args.out_dir / f"montage_{char}.png"
        try:
            render_character_montage(
                character=char,
                tag_order=tag_order,
                tag_to_idxs=tag_map,
                tag_to_mp4=tag_to_mp4,
                shots=shots,
                max_per_row=args.max_per_row,
                workdir=workdir,
                out_path=out_path,
            )
        except Exception as e:
            print(f"[{char}] ERROR rendering: {e}")

    if not args.keep_frames:
        shutil.rmtree(workdir)
        print(f"removed workdir {workdir}")
    else:
        print(f"kept frames at {workdir}")

    print(f"\nMontages → {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
