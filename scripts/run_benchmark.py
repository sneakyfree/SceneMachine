"""Benchmark harness: run the SceneMachine pipeline against the fixed
2-screenplay control-group corpus and tag the output for quality tracking.

Usage:
    python scripts/run_benchmark.py V1_30steps
    python scripts/run_benchmark.py V3_llm_prompts --screenplay RADAR_LOVE_2
    python scripts/run_benchmark.py --list-presets

The corpus is fixed: RADAR_LOVE_2 (47 scenes) + IMPOSSIBLE_FULL (106 scenes).
These were locked as V0 on 2026-05-14 after Grant watched both outputs and
declared them "video slop." Every future change to the pipeline that touches
video generation must beat V0 on this corpus on Grant's watch-it scale.

V0 corpus + config + outputs are at
``https://huggingface.co/SceneMachine/operations-log/tree/main/benchmarks/V0_2026-05-14``
and locally at ``/tmp/scenemachine_loop/screenplays_converted/`` +
``/home/user1-gpu/scenemachine_movies/{RADAR_LOVE_2,IMPOSSIBLE_FULL}/``.

This harness produces tagged outputs under
``/home/user1-gpu/scenemachine_movies/benchmarks/<version_tag>/<screenplay>/``
so V0 is never overwritten.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional

# Pin CWD so the launcher's SQLite path resolves consistently.
os.chdir("/home/user1-gpu")
sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/SceneMachine/packages/core")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("benchmark")


# ----------------------------------------------------------------------
# Corpus + presets
# ----------------------------------------------------------------------

CORPUS = {
    "RADAR_LOVE_2": {
        "screenplay_path": "/tmp/scenemachine_loop/screenplays_converted/Radar_Love_2.txt",
        "project_id": "f48c808b-9ed9-497e-a0b3-ae46a2b53bf2",
        "expected_scenes": 47,
        "github_source": "github.com/sneakyfree/screenplays/Radar_Love_2.fountain",
    },
    "IMPOSSIBLE_FULL": {
        "screenplay_path": "/tmp/scenemachine_loop/screenplays_converted/Impossible_Full.txt",
        "project_id": "4d2ebed3-25d0-4bf4-80a1-eb9c09242743",
        "expected_scenes": 106,
        "github_source": "github.com/sneakyfree/screenplays/Impossible.fountain",
    },
}


@dataclass
class BenchmarkPreset:
    """One row in the V0..V7 hypothesis matrix."""
    name: str
    description: str
    num_inference_steps: int = 10
    guidance_scale: float = 6.0
    width: int = 768
    height: int = 432
    duration_seconds: float = 3.0
    fps: int = 24
    use_llm_prompts: bool = False
    use_continuity: bool = False
    use_animate_when_chars: bool = False
    use_quality_gate_regen: bool = False
    expected_wallclock_minutes_per_47_shots: int = 110


PRESETS: Dict[str, BenchmarkPreset] = {
    "V0_baseline": BenchmarkPreset(
        name="V0_baseline",
        description="The slop baseline. 10 steps, 768x432, template prompts. Locked; do not re-run.",
        num_inference_steps=10,
    ),
    "V1_30steps": BenchmarkPreset(
        name="V1_30steps",
        description="Step count only: 10 -> 30. Everything else equal to V0.",
        num_inference_steps=30,
        expected_wallclock_minutes_per_47_shots=8 * 60,
    ),
    "V2_720p": BenchmarkPreset(
        name="V2_720p",
        description="V1 + bump resolution 768x432 -> 1280x720.",
        num_inference_steps=30,
        width=1280,
        height=720,
        expected_wallclock_minutes_per_47_shots=12 * 60,
    ),
    "V3_llm_prompts": BenchmarkPreset(
        name="V3_llm_prompts",
        description="V1 + LLM-generated rich prompts (Qwen) instead of templates.",
        num_inference_steps=30,
        use_llm_prompts=True,
        expected_wallclock_minutes_per_47_shots=8 * 60,
    ),
    "V4_continuity": BenchmarkPreset(
        name="V4_continuity",
        description="V1 + I2V continuity within scenes (PR #47 unblocked path).",
        num_inference_steps=30,
        use_continuity=True,
        expected_wallclock_minutes_per_47_shots=8 * 60,
    ),
    "V5_animate": BenchmarkPreset(
        name="V5_animate",
        description="V1 + Animate when named characters in frame (needs character refs first).",
        num_inference_steps=30,
        use_animate_when_chars=True,
        expected_wallclock_minutes_per_47_shots=2 * 60,
    ),
    "V6_quality_regen": BenchmarkPreset(
        name="V6_quality_regen",
        description="V1 + real quality gate + regen on score < 0.6 (needs RIB-3.7 shipped first).",
        num_inference_steps=30,
        use_quality_gate_regen=True,
        expected_wallclock_minutes_per_47_shots=11 * 60,
    ),
    "V7_combined": BenchmarkPreset(
        name="V7_combined",
        description="All improvements merged. The candidate v1 product config.",
        num_inference_steps=30,
        width=1280,
        height=720,
        use_llm_prompts=True,
        use_continuity=True,
        use_animate_when_chars=True,
        use_quality_gate_regen=True,
        expected_wallclock_minutes_per_47_shots=15 * 60,
    ),
}


# ----------------------------------------------------------------------
# Provenance
# ----------------------------------------------------------------------

def git_commit() -> str:
    """Capture the current git commit so every benchmark output is traceable."""
    try:
        return subprocess.check_output(
            ["git", "-C", "/home/user1-gpu/Desktop/grants_folder/SceneMachine",
             "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except Exception as e:
        log.warning("could not capture git commit: %s", e)
        return "unknown"


def sha256_file(path: Path) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

async def run_one_screenplay(
    screenplay_name: str,
    preset: BenchmarkPreset,
    run_dir: Path,
) -> Dict[str, Any]:
    """Run one screenplay through the pipeline with the given preset."""
    from uuid import UUID, uuid4
    from scenemachine.database import get_db_manager
    from scenemachine.generators.registry import setup_providers
    from scenemachine.services.production_pipeline import (
        ProductionPipeline,
        ShotGenerationStatus,
    )
    from scenemachine.services.scene_planning import ScenePlanningService

    entry = CORPUS[screenplay_name]
    output_dir = run_dir / screenplay_name
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 72)
    log.info("BENCHMARK RUN: %s (%s)", preset.name, screenplay_name)
    log.info("  project_id: %s", entry["project_id"])
    log.info("  output_dir: %s", output_dir)
    log.info("  steps=%d  res=%dx%d  llm_prompts=%s  continuity=%s",
             preset.num_inference_steps, preset.width, preset.height,
             preset.use_llm_prompts, preset.use_continuity)
    log.info("=" * 72)

    setup_providers()
    db = get_db_manager()
    await db.initialize()

    async with db.session() as session:
        svc = ScenePlanningService(session)
        scenes = await svc.get_project_scenes(UUID(entry["project_id"]), include_shots=False)
        log.info("loaded %d scenes from DB", len(scenes))
        scene_data = []
        for sc in scenes:
            tod = sc.time_of_day.value if hasattr(sc.time_of_day, "value") else str(sc.time_of_day)
            scene_data.append({
                "scene_number": str(sc.scene_number),
                "sequence_number": int(sc.sequence_number),
                "location": sc.location or "",
                "time_of_day": tod,
                "raw_content": (sc.raw_content or "")[:600],
            })

    # V5_animate wire-up: when use_animate_when_chars=True, load the
    # screenplay's character reference images from disk and tag each
    # shot with the character_ids it features. The downstream pipeline +
    # StackRouter route shots with non-empty character_ids through the
    # Wan 2.2 Animate workflow (per memory comfyui-animate-vram-cache).
    #
    # Character ID convention: lowercase_snake_case (jack_harris). The
    # ref filenames at character_refs/<SCREENPLAY>/<id>.png must match.
    character_refs: List[Dict[str, Any]] = []
    char_id_by_keyword: Dict[str, str] = {}
    if preset.use_animate_when_chars:
        refs_dir = Path(
            f"/home/user1-gpu/scenemachine_movies/character_refs/{screenplay_name}"
        )
        if refs_dir.is_dir():
            for png in sorted(refs_dir.glob("*.png")):
                cid = png.stem  # e.g. "jack_harris"
                character_refs.append({
                    "id": cid,
                    "character_id": cid,
                    "name": cid.replace("_", " ").title(),
                    "reference_image_path": str(png),
                })
                # Build a keyword → character_id map for shot-text
                # matching. Each underscore-separated token becomes a
                # match keyword (e.g. "jack_harris" → ["jack", "harris"]).
                for tok in cid.split("_"):
                    if len(tok) >= 3:  # skip tiny tokens
                        char_id_by_keyword[tok.lower()] = cid
            log.info(
                "V5 mode: loaded %d character refs from %s",
                len(character_refs), refs_dir,
            )
        else:
            log.warning(
                "V5 mode but no character refs at %s — falling back to "
                "T2V routing for all shots (V5 == V1 in effect)",
                refs_dir,
            )

    # Load LLM-enhanced prompts when the preset opts in. Fails LOUD when
    # the expected JSON is missing or doesn't cover every requested scene —
    # no silent fallback to template prompts, per the no-silent-fallbacks
    # rule. To populate the JSON: run scripts/generate_llm_prompts.py.
    llm_prompts_map: Dict[str, str] = {}
    if preset.use_llm_prompts:
        llm_json_path = Path(
            f"/home/user1-gpu/scenemachine_movies/llm_prompts/"
            f"{screenplay_name}/qwen2.5-72b.json"
        )
        if not llm_json_path.exists():
            raise FileNotFoundError(
                f"preset.use_llm_prompts=True but {llm_json_path} not found. "
                f"Run `python scripts/generate_llm_prompts.py --screenplay "
                f"{screenplay_name} --out {llm_json_path}` first."
            )
        llm_doc = json.loads(llm_json_path.read_text())
        for sn, sc in (llm_doc.get("scenes") or {}).items():
            prompt = (sc or {}).get("enhanced_prompt")
            if prompt:
                llm_prompts_map[sn] = prompt
        # Verify coverage of every scene we're about to run. Partial JSONs
        # (failed mid-generation) must be regenerated before benchmarking.
        missing = [sd["scene_number"] for sd in scene_data
                   if sd["scene_number"] not in llm_prompts_map]
        if missing:
            raise RuntimeError(
                f"LLM prompts JSON at {llm_json_path} is missing prompts "
                f"for scenes {missing}. Regenerate with --force after "
                f"diagnosing the gap."
            )
        log.info("V3 mode: loaded %d LLM-enhanced prompts from %s",
                 len(llm_prompts_map), llm_json_path)

    scenes_for_pipeline = []
    shot_statuses = []
    for sd in scene_data:
        if llm_prompts_map:
            description = llm_prompts_map[sd["scene_number"]]
        else:
            snippets = [f"{sd['location']}, {sd['time_of_day']}"] if sd["location"] else []
            raw = sd["raw_content"].replace("\n", " ").strip()
            if raw:
                snippets.append(raw[:280])
            description = (
                "Cinematic wide establishing shot. " + " — ".join(snippets)
                if snippets else "Cinematic wide establishing shot"
            )

        # V5 character detection: scan the raw scene content (longer
        # than the truncated description) for any character keyword.
        # We match against the FULL raw scene text — screenplay format
        # capitalizes character names on dialogue lines so the signal
        # is strong. Order of insertion preserved; dedup later.
        shot_character_ids: List[str] = []
        if char_id_by_keyword:
            haystack = (sd["raw_content"] or "").lower()
            seen = set()
            for kw, cid in char_id_by_keyword.items():
                if kw in haystack and cid not in seen:
                    shot_character_ids.append(cid)
                    seen.add(cid)

        shot_id = str(uuid4())
        scenes_for_pipeline.append({
            "scene_number": sd["scene_number"],
            "shots": [{
                "shot_id": shot_id,
                "description": description,
                "shot_type": "wide",
                "camera_movement": "static",
                "duration_seconds": preset.duration_seconds,
                "width": preset.width,
                "height": preset.height,
                "fps": preset.fps,
                "seed": 42 + sd["sequence_number"],
                "character_ids": shot_character_ids,
                "negative_prompt": "blurry, low quality, watermark, text overlay, distorted",
                "num_inference_steps": preset.num_inference_steps,
                "guidance_scale": preset.guidance_scale,
            }],
        })
        # Chain mode for continuity presets: when preset.use_continuity is
        # True, all shots share a single synthetic scene_id so the I2V
        # routing logic (which groups shots by scene_id, only passing
        # prev_shot_last_frame within a group) treats the whole run as one
        # big chain. RADAR_LOVE_2's per-scene decomposition gives 1 shot
        # per scene; without this, prev_shot_last_frame is always None and
        # I2V routing never fires (V4-as-broken on 2026-05-21 confirmed
        # this null result). Tracked as P1-7 in docs/INVENTORY_DEFECTS.md.
        chain_scene_id = "_continuity_chain" if preset.use_continuity else sd["scene_number"]
        shot_statuses.append(ShotGenerationStatus(
            shot_id=shot_id, scene_id=chain_scene_id, status="queued",
        ))

    if preset.use_animate_when_chars:
        shots_with_chars = sum(
            1 for s in scenes_for_pipeline if s["shots"][0]["character_ids"]
        )
        log.info(
            "V5 mode: %d/%d shots tagged with at least one character",
            shots_with_chars, len(shot_statuses),
        )

    log.info("built %d shots for %s", len(shot_statuses), screenplay_name)

    pipeline = ProductionPipeline(
        project_id=entry["project_id"],
        output_dir=output_dir,
        max_parallel=1,
        quality_threshold=0.0,
    )
    pipeline.shot_list = {"scenes": scenes_for_pipeline}
    pipeline.shot_statuses = {s.shot_id: s for s in shot_statuses}
    pipeline.characters = character_refs

    t0 = time.monotonic()
    await pipeline._generate_videos(shot_statuses)
    gen_elapsed = time.monotonic() - t0

    completed = sum(1 for s in shot_statuses if s.status == "completed")
    failed = sum(1 for s in shot_statuses if s.status == "failed")
    log.info("video gen: %.1fs  completed=%d  failed=%d", gen_elapsed, completed, failed)

    output_path = await pipeline._assemble_movie(shot_statuses)
    final_mp4 = output_dir / "final.mp4"
    if Path(output_path).exists() and output_path != str(final_mp4):
        shutil.copy2(output_path, final_mp4)

    final_sha = sha256_file(final_mp4) if final_mp4.exists() else None
    return {
        "screenplay": screenplay_name,
        "preset": preset.name,
        "shots_total": len(shot_statuses),
        "shots_completed": completed,
        "shots_failed": failed,
        "video_gen_elapsed_s": round(gen_elapsed, 1),
        "final_mp4_path": str(final_mp4),
        "final_mp4_bytes": final_mp4.stat().st_size if final_mp4.exists() else 0,
        "final_mp4_sha256": final_sha,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_tag", nargs="?",
                        help="One of the preset names (V0_baseline, V1_30steps, ...)")
    parser.add_argument("--screenplay",
                        choices=list(CORPUS.keys()) + ["both"], default="both")
    parser.add_argument("--list-presets", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan; do not run.")
    args = parser.parse_args()

    if args.list_presets or not args.version_tag:
        print("Available presets:")
        for name, p in PRESETS.items():
            wallclock_h = p.expected_wallclock_minutes_per_47_shots / 60
            print(f"  {name:<22} {wallclock_h:>5.1f}h/47-shots  — {p.description}")
        return 0

    if args.version_tag not in PRESETS:
        print(f"unknown preset: {args.version_tag}; see --list-presets")
        return 2

    preset = PRESETS[args.version_tag]
    if args.version_tag == "V0_baseline":
        print("ERROR: V0 is locked. Re-running would overwrite the slop reference.")
        print("If you intend a fresh V0, use a different tag (e.g. V0_replay_<date>).")
        return 2

    commit = git_commit()
    run_dir = Path(f"/home/user1-gpu/scenemachine_movies/benchmarks/{args.version_tag}")
    run_dir.mkdir(parents=True, exist_ok=True)

    plan = {
        "version_tag": args.version_tag,
        "preset": asdict(preset),
        "commit": commit,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "screenplay_filter": args.screenplay,
        "run_dir": str(run_dir),
    }
    (run_dir / "PLAN.json").write_text(json.dumps(plan, indent=2))
    log.info("plan saved to %s", run_dir / "PLAN.json")

    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0

    screenplays = list(CORPUS.keys()) if args.screenplay == "both" else [args.screenplay]
    results: List[Dict[str, Any]] = []
    for sn in screenplays:
        try:
            r = await run_one_screenplay(sn, preset, run_dir)
            results.append(r)
        except Exception as e:
            log.exception("run failed for %s: %s", sn, e)
            results.append({"screenplay": sn, "error": str(e), "preset": preset.name})

    summary = {
        **plan,
        "ended_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    (run_dir / "RESULTS.json").write_text(json.dumps(summary, indent=2, default=str))
    log.info("results -> %s", run_dir / "RESULTS.json")
    print(json.dumps(summary, indent=2, default=str))

    # Best-effort HF upload of just the metadata (mp4s stay local — too large).
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        for fname in ("PLAN.json", "RESULTS.json"):
            api.upload_file(
                path_or_fileobj=str(run_dir / fname),
                path_in_repo=f"benchmarks/{args.version_tag}/{fname}",
                repo_id="SceneMachine/operations-log",
                repo_type="model",
                commit_message=f"benchmark {args.version_tag}: {fname}",
            )
        log.info("metadata pushed to HF benchmarks/%s/", args.version_tag)
    except Exception as e:
        log.warning("HF upload failed (non-fatal): %s", e)

    any_failed = any(r.get("shots_failed", 0) > 0 or "error" in r for r in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
