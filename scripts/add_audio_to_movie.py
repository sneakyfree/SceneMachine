"""Phase 2 audio MVP — narrate each scene + mux onto an existing final.mp4.

The benchmark harness's V0..V8 outputs are silent. Grandma-watchable wants
voice over the visuals. This is the smallest possible Phase 2 step: take
one already-assembled final.mp4 and lay a per-scene narration track on
top of it. No lipsync (the visuals are wide shots; mouths aren't the
focus); no character voices (one narrator); no music. Just a voice
describing what we're seeing, like a documentary VO or a storyboard
walkthrough.

Two narration sources, in priority order:

  1. ``--prompts-json`` (an llm_prompts JSON from
     scripts/generate_llm_prompts.py) — uses ``scenes[N].enhanced_prompt``
     as the narration text. This is the cleanest version: the Qwen
     LLM-enhanced cinematic descriptions become the voice-over, so the
     audio matches what the model was told to generate. Works only for
     scene_numbers that the JSON covers; failure is loud.

  2. ``--screenplay`` — reads the same scenes the harness reads from the
     SceneMachine DB and uses ``location + raw_content[:300]`` as the
     narration text. Fallback when no LLM prompts JSON exists yet.

Per-scene timing: the input mp4 is split into ``--shots`` equal segments
(duration / shots). For each scene the gTTS-generated audio is paded to
that segment length (silence after) or truncated if it exceeds (rare;
gTTS reads ~5 chars/sec, scene-segments are 2.875s ≈ 14 chars max
which is small — typical Qwen prompts are 40+ words ≈ 200 chars ≈ 40
seconds, way over). The expected use case is therefore: stretch the
video to match the audio length, not the other way around. Two modes
controlled by ``--time-mode``:

  - ``pad``      audio is padded with silence to the video's segment
                 length. Audio that's longer than the segment is
                 truncated (loses content; loud warning).
  - ``stretch``  the video is stretched per-segment to match the audio
                 duration. Final movie ends up longer than the source
                 (47 scenes × ~7s narration ≈ 5.5 min, vs original
                 ~2.5 min). Looks like slow-mo on some shots; ideal
                 for the narration use case.

Output: a new mp4 at ``--out``. The original mp4 is not touched.

Usage::

    /home/user1-gpu/chatterbox-test/venv/bin/python \\
      scripts/add_audio_to_movie.py \\
      --mp4 .../V8_hybrid_routing/RADAR_LOVE_2/final.mp4 \\
      --prompts-json .../llm_prompts/RADAR_LOVE_2/qwen2.5-72b.json \\
      --shots 47 \\
      --time-mode stretch \\
      --out .../V8_hybrid_routing/RADAR_LOVE_2/with_audio.mp4

Hard rule: no silent fallback to "no audio" — if any scene's TTS fails,
the script raises and writes nothing (per the no-silent-fallbacks rule
that's already burned us twice in this codebase).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# gTTS lives in the chatterbox-test venv; system python doesn't have it.
# Caller should invoke via that interpreter (see usage above).
from gtts import gTTS

# Pin CWD so SceneMachine's SQLite path resolves consistently when
# --screenplay falls back to DB reads.
os.chdir("/home/user1-gpu")
sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/SceneMachine/packages/core")


def gtts_one(text: str, out_path: Path, lang: str = "en",
             slow: bool = False, max_retries: int = 5) -> None:
    """Generate one mp3 via gTTS, with backoff on transient network
    failures (gTTS uses Google Translate's TTS endpoint which
    occasionally rate-limits / 5xxs for a few seconds). Raises only
    after exhausting retries — loud failure per no-silent-fallbacks.
    """
    import time
    text = text.strip()
    if not text:
        raise RuntimeError(f"empty narration for {out_path}")
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(str(out_path))
            if out_path.exists() and out_path.stat().st_size >= 1024:
                return
            raise RuntimeError(
                f"gTTS produced empty/tiny mp3 at {out_path} "
                f"({out_path.stat().st_size if out_path.exists() else 'missing'} bytes)"
            )
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_retries - 1:
                backoff = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                print(f"  gTTS attempt {attempt + 1}/{max_retries} failed "
                      f"({e!s}); retry in {backoff}s")
                time.sleep(backoff)
    raise RuntimeError(
        f"gTTS exhausted {max_retries} retries for {out_path}: {last_err!r}"
    )


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ]).decode().strip()
    return float(out)


def pad_audio(in_path: Path, target_seconds: float, out_path: Path) -> None:
    """Pad mp3 with silence to target_seconds (or truncate if longer)."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(in_path),
        "-af", f"apad=whole_dur={target_seconds:.3f}",
        "-t", f"{target_seconds:.3f}",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg apad failed: {res.stderr[-1000:]}")


def stretch_video_segment(
    in_mp4: Path, start_s: float, segment_s: float,
    audio_s: float, out_path: Path,
) -> None:
    """Cut a segment of in_mp4 from start_s for segment_s seconds and
    stretch it to audio_s seconds using the setpts filter. Audio is
    silent; will be muxed later.

    Caution learned 2026-05-18: ``-t`` and ``-ss`` MUST appear before
    ``-i`` so they are interpreted as INPUT-side seek + duration.
    Putting them after ``-i`` makes them OUTPUT clamps, which silently
    truncated the stretched output back to the original segment length
    (47 × 2.875s segments stayed at 135s instead of expanding to
    ~12min). The mux then ``-shortest``-truncated the 12-min audio to
    match the too-short video, lost ~10 min of narration. The bug was
    loud only at ffprobe-the-output time.
    """
    speed = segment_s / audio_s  # < 1 = slower (longer)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start_s:.3f}",
        "-t", f"{segment_s:.3f}",
        "-i", str(in_mp4),
        "-an",
        "-vf", f"setpts=PTS/{speed:.6f}",
        "-c:v", "libx264", "-preset", "fast",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg setpts failed: {res.stderr[-1000:]}")


def concat_segments(segment_paths: list[Path], out_path: Path) -> None:
    """ffmpeg concat-filter re-encode to merge segments (handles
    heterogeneous setpts outputs cleanly)."""
    if not segment_paths:
        raise RuntimeError("no segments to concat")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in segment_paths:
            f.write(f"file '{p.resolve()}'\n")
        list_path = f.name
    try:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            str(out_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # -c copy may fail on heterogeneous segments. Retry with re-encode.
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", list_path,
                "-c:v", "libx264", "-preset", "fast",
                str(out_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"ffmpeg concat fallback failed: "
                                   f"{res.stderr[-1500:]}")
    finally:
        Path(list_path).unlink()


def mux_video_audio(video: Path, audio: Path, out: Path) -> None:
    """Combine a silent-video mp4 + an audio mp3/aac into one mp4."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg mux failed: {res.stderr[-1500:]}")


def load_narration_from_prompts(prompts_json: Path, shots: int) -> list[str]:
    """Return a list of `shots` narration strings keyed by scene_number.

    Scenes are sorted by sequence_number; if any of the first `shots`
    sequence positions is missing from the JSON, fail loud.
    """
    doc = json.loads(prompts_json.read_text())
    scenes = doc.get("scenes") or {}
    if not scenes:
        raise RuntimeError(f"{prompts_json} has no 'scenes' map")
    # Sort by sequence_number so the order matches the harness output.
    items = sorted(
        scenes.values(),
        key=lambda s: int(s.get("sequence_number", 0)),
    )
    if len(items) < shots:
        raise RuntimeError(
            f"{prompts_json} covers {len(items)} scenes but mp4 has "
            f"{shots} shots. Need a complete prompts run."
        )
    narrations = []
    for s in items[:shots]:
        text = s.get("enhanced_prompt", "").strip()
        if not text:
            raise RuntimeError(
                f"scene {s.get('scene_number')} has empty enhanced_prompt"
            )
        narrations.append(text)
    return narrations


async def load_narration_from_db(screenplay: str, shots: int) -> list[str]:
    """Fallback: pull location + raw_content from the SceneMachine DB
    just like run_benchmark.py does, and use that as narration."""
    from uuid import UUID

    from scenemachine.database import get_db_manager
    from scenemachine.services.scene_planning import ScenePlanningService

    corpus = {
        "RADAR_LOVE_2": "f48c808b-9ed9-497e-a0b3-ae46a2b53bf2",
        "IMPOSSIBLE_FULL": "4d2ebed3-25d0-4bf4-80a1-eb9c09242743",
    }
    pid = corpus.get(screenplay)
    if not pid:
        raise RuntimeError(f"unknown screenplay {screenplay}")

    db = get_db_manager()
    await db.initialize()
    async with db.session() as session:
        svc = ScenePlanningService(session)
        scenes = await svc.get_project_scenes(UUID(pid), include_shots=False)
    scenes = sorted(scenes, key=lambda sc: int(sc.sequence_number))
    if len(scenes) < shots:
        raise RuntimeError(
            f"DB has {len(scenes)} scenes for {screenplay} but mp4 has "
            f"{shots} shots."
        )
    narrations = []
    for sc in scenes[:shots]:
        loc = sc.location or ""
        raw = (sc.raw_content or "").replace("\n", " ").strip()
        text = (f"{loc}. {raw[:280]}" if loc else raw[:300]).strip()
        if not text:
            text = f"Scene {sc.scene_number}"
        narrations.append(text)
    return narrations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mp4", type=Path, required=True,
                        help="Silent input movie")
    parser.add_argument("--shots", type=int, required=True,
                        help="Number of shot-segments in the input mp4")
    parser.add_argument("--prompts-json", type=Path, default=None,
                        help="LLM prompts JSON (preferred narration source)")
    parser.add_argument("--screenplay", type=str, default=None,
                        help="Fallback narration source via DB read "
                             "(RADAR_LOVE_2 or IMPOSSIBLE_FULL)")
    parser.add_argument("--time-mode", choices=("pad", "stretch"),
                        default="stretch",
                        help="pad = pad audio to video duration. "
                             "stretch = stretch video to audio duration "
                             "(default; better for narration).")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--keep-workdir", action="store_true")
    args = parser.parse_args()

    if not args.mp4.exists():
        print(f"input mp4 missing: {args.mp4}", file=sys.stderr)
        return 2
    if not args.prompts_json and not args.screenplay:
        print("need either --prompts-json or --screenplay", file=sys.stderr)
        return 2

    # Load narrations
    if args.prompts_json and args.prompts_json.exists():
        narrations = load_narration_from_prompts(args.prompts_json, args.shots)
        print(f"loaded {len(narrations)} narrations from {args.prompts_json}")
    elif args.screenplay:
        import asyncio
        narrations = asyncio.run(
            load_narration_from_db(args.screenplay, args.shots)
        )
        print(f"loaded {len(narrations)} narrations from DB "
              f"({args.screenplay})")
    else:
        print(f"prompts-json {args.prompts_json} not found and no "
              f"--screenplay fallback supplied", file=sys.stderr)
        return 2

    workdir = Path(tempfile.mkdtemp(prefix="audio_mvp_"))
    print(f"workdir={workdir}")

    duration = ffprobe_duration(args.mp4)
    segment_seconds = duration / args.shots
    print(f"input duration={duration:.3f}s  shots={args.shots}  "
          f"per-shot={segment_seconds:.3f}s")

    # Stage 1: TTS each narration
    raw_audios: list[Path] = []
    for i, text in enumerate(narrations):
        out_mp3 = workdir / f"narration_{i:03d}.mp3"
        try:
            gtts_one(text, out_mp3, lang=args.lang)
        except Exception as e:
            print(f"TTS failed at scene {i}: {e}", file=sys.stderr)
            return 4
        raw_audios.append(out_mp3)
    print(f"generated {len(raw_audios)} TTS clips")

    # Stage 2: build the soundtrack
    if args.time_mode == "pad":
        # Pad each clip to segment_seconds; concat all → one audio track
        padded: list[Path] = []
        for i, mp3 in enumerate(raw_audios):
            out_aac = workdir / f"padded_{i:03d}.m4a"
            pad_audio(mp3, segment_seconds, out_aac)
            padded.append(out_aac)
        full_audio = workdir / "soundtrack.m4a"
        concat_segments(padded, full_audio)
        # Mux onto the original (silent) video
        mux_video_audio(args.mp4, full_audio, args.out)
    else:
        # stretch: stretch each video segment to match its audio length
        stretched_segs: list[Path] = []
        for i, mp3 in enumerate(raw_audios):
            audio_s = ffprobe_duration(mp3)
            start_s = i * segment_seconds
            out_seg = workdir / f"stretched_{i:03d}.mp4"
            stretch_video_segment(
                args.mp4, start_s, segment_seconds, audio_s, out_seg,
            )
            stretched_segs.append(out_seg)
        stretched_video = workdir / "stretched_video.mp4"
        concat_segments(stretched_segs, stretched_video)
        # Concat the raw audio clips (each clip already matches its
        # stretched segment).
        audio_concat = workdir / "soundtrack.m4a"
        # Re-encode the mp3s to aac for clean mux
        aac_paths: list[Path] = []
        for i, mp3 in enumerate(raw_audios):
            aac = workdir / f"audio_aac_{i:03d}.m4a"
            res = subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                "-c:a", "aac", "-b:a", "128k", str(aac),
            ], capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"ffmpeg mp3→aac failed: {res.stderr[-800:]}")
            aac_paths.append(aac)
        concat_segments(aac_paths, audio_concat)
        mux_video_audio(stretched_video, audio_concat, args.out)

    print(f"wrote {args.out} ({args.out.stat().st_size} bytes)")

    if not args.keep_workdir:
        import shutil
        shutil.rmtree(workdir)
        print(f"removed workdir {workdir}")
    else:
        print(f"kept workdir {workdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
