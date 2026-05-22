"""Generate Wan 2.2 cinematic prompts from screenplay scenes via Ollama.

The benchmark harness has long had a ``use_llm_prompts`` flag (BenchmarkPreset
field) and a stub line in ``run_one_screenplay`` that promises: "V3 will swap
this loop for an LLM-driven breakdown when ``preset.use_llm_prompts`` is True."
That branch was never wired. This script — together with the small
``scripts/run_benchmark.py`` consumer patch — wires it.

The script reads scenes from the SceneMachine DB (same source the harness uses),
asks an Ollama model to convert each scene description into a single sentence
optimized for Wan 2.2 text-to-video, and writes a JSON dictionary keyed by
scene_number that the harness loads when a preset opts in.

JSON layout::

    {
      "meta": {
        "screenplay": "RADAR_LOVE_2",
        "ollama_model": "qwen2.5:72b-instruct-q6_K",
        "generated_at_utc": "2026-05-17T20:00:00+00:00",
        "scenes_count": 47,
        "system_prompt_sha256": "...",
        "elapsed_seconds": 1234.5
      },
      "scenes": {
        "1": {
          "scene_number": "1",
          "sequence_number": 1,
          "location": "INT. RAIL CAR",
          "time_of_day": "DAY",
          "raw_excerpt": "Jack stares out the window...",
          "enhanced_prompt": "Cinematic wide shot of a young man..."
        },
        ...
      }
    }

Usage::

    python scripts/generate_llm_prompts.py \\
      --screenplay RADAR_LOVE_2 \\
      --model qwen2.5:72b-instruct-q6_K \\
      --out /home/user1-gpu/scenemachine_movies/llm_prompts/RADAR_LOVE_2/qwen2.5-72b.json

Idempotent: if --out exists and --force is not passed, exits early without
calling Ollama. The harness consumer (run_benchmark.py) FAILS LOUD when
``use_llm_prompts=True`` but the expected JSON is missing — there is no silent
fallback to templates, per the no-silent-fallbacks rule.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

os.chdir("/home/user1-gpu")
sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/SceneMachine/packages/core")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("generate_llm_prompts")


# Mirror the corpus from run_benchmark.py so both share project_ids.
CORPUS = {
    "RADAR_LOVE_2": {
        "project_id": "f48c808b-9ed9-497e-a0b3-ae46a2b53bf2",
        "expected_scenes": 47,
    },
    "IMPOSSIBLE_FULL": {
        "project_id": "4d2ebed3-25d0-4bf4-80a1-eb9c09242743",
        "expected_scenes": 106,
    },
}


SYSTEM_PROMPT = (
    "You are a cinematic prompt engineer for the Wan 2.2 text-to-video "
    "diffusion model.\n"
    "\n"
    "Convert each screenplay scene into a SINGLE English sentence "
    "optimized for Wan 2.2. Cover these elements when the scene supports "
    "them:\n"
    "\n"
    "- Subject — who or what is in the shot\n"
    "- Action — what they are doing, in present tense\n"
    "- Setting — location, time of day, weather\n"
    "- Camera — wide / medium / close-up + angle (high / low / eye-level)\n"
    "- Lighting — source and mood (golden hour, harsh fluorescent, soft "
    "daylight, neon, candlelight…)\n"
    "- Style — cinematic / gritty / vintage / dreamy — choose what fits "
    "the scene's tone\n"
    "\n"
    "Hard constraints:\n"
    "- One sentence. ≤ 60 words.\n"
    "- Use concrete visual details, not abstract feelings.\n"
    "- Do not invent character names not in the source.\n"
    "- Do not include dialogue or sound.\n"
    "- Output ONLY the enhanced prompt. No headings, no markdown, no "
    "preamble, no closing punctuation other than a single period.\n"
)


def build_user_prompt(scene_number: str, location: str,
                      time_of_day: str, raw: str) -> str:
    return (
        f"SCENE NUMBER: {scene_number}\n"
        f"LOCATION: {location or '(unspecified)'}\n"
        f"TIME OF DAY: {time_of_day or '(unspecified)'}\n\n"
        f"RAW SCENE TEXT:\n{raw.strip() or '(empty)'}\n\n"
        "ENHANCED PROMPT (one sentence, ≤60 words):"
    )


def system_prompt_hash() -> str:
    return hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()


async def call_ollama(
    client: httpx.AsyncClient,
    model: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    ollama_url: str,
    timeout_seconds: float = 1800.0,
) -> str:
    """One Ollama /api/chat call. Raises on HTTP error or empty response.

    Default timeout is 1800s (30 min) — earlier 600s default got tripped
    by Qwen 72B Q6_K on CPU while V6a was contending for cycles (scene 12
    took 584s and scene 14 ReadTimeout'd at >600s). On a freed GPU the
    same calls take ~30s, so this generous timeout has zero downside in
    the GPU-warm case and prevents avoidable failures in the CPU case.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    resp = await client.post(
        f"{ollama_url.rstrip('/')}/api/chat",
        json=payload,
        timeout=timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    content = (data.get("message") or {}).get("content", "").strip()
    if not content:
        raise RuntimeError(
            f"Ollama returned empty content for model={model}; full body: {data!r}"
        )
    # Collapse to a single line — even with the system prompt, models
    # occasionally hard-wrap. One sentence per scene, not a paragraph.
    return " ".join(content.split())


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenplay", required=True,
                        choices=list(CORPUS.keys()))
    parser.add_argument("--model", default="qwen2.5:72b-instruct-q6_K",
                        help="Ollama model tag")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output JSON path")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--temperature", type=float, default=0.2,
                        help="Sampling temperature (0.2 = mostly deterministic)")
    parser.add_argument("--max-tokens", type=int, default=200)
    parser.add_argument("--force", action="store_true",
                        help="Overwrite --out if it already exists")
    parser.add_argument("--resume", action="store_true",
                        help="When --out already exists, keep the scenes "
                             "it has and generate only the missing ones. "
                             "Cannot be combined with --force.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only generate prompts for the first N scenes "
                             "(smoke test)")
    parser.add_argument("--timeout-seconds", type=float, default=1800.0,
                        help="Per-call Ollama timeout (default 1800s; bump "
                             "higher when running Qwen 72B Q6_K on CPU "
                             "under contention)")
    args = parser.parse_args()

    if args.force and args.resume:
        log.error("--force and --resume are mutually exclusive")
        return 2

    if args.out.exists() and not args.force and not args.resume:
        log.info("%s already exists — pass --force to regenerate or "
                 "--resume to fill missing scenes. Exiting.", args.out)
        return 0

    from scenemachine.database import get_db_manager
    from scenemachine.services.scene_planning import ScenePlanningService

    entry = CORPUS[args.screenplay]

    db = get_db_manager()
    await db.initialize()

    async with db.session() as session:
        svc = ScenePlanningService(session)
        scenes = await svc.get_project_scenes(
            UUID(entry["project_id"]), include_shots=False
        )
        log.info("loaded %d scenes from DB", len(scenes))
        if args.limit is not None and args.limit > 0:
            scenes = scenes[:args.limit]
            log.info("--limit applied: keeping first %d scenes", len(scenes))

        scene_inputs: list[dict[str, Any]] = []
        for sc in scenes:
            tod = (sc.time_of_day.value if hasattr(sc.time_of_day, "value")
                   else str(sc.time_of_day))
            scene_inputs.append({
                "scene_number": str(sc.scene_number),
                "sequence_number": int(sc.sequence_number),
                "location": sc.location or "",
                "time_of_day": tod,
                "raw_content": (sc.raw_content or "")[:1500],
            })

    log.info("calling Ollama model=%s on %d scenes (this can take minutes; "
             "Qwen 72B Q6_K on CPU is ~1-2 min/scene)",
             args.model, len(scene_inputs))

    # --resume: load whatever we already have, skip scenes whose prompts
    # are present, redo any that are missing. The system_prompt_sha256
    # check protects against resuming with a different system prompt
    # (which would mix prompt styles across scenes).
    out: dict[str, Any]
    if args.resume and args.out.exists():
        out = json.loads(args.out.read_text())
        if (out.get("meta") or {}).get("system_prompt_sha256") != system_prompt_hash():
            log.error(
                "--resume: existing %s was generated with a different "
                "SYSTEM_PROMPT (sha mismatch). Refusing to mix prompts. "
                "Use --force to regenerate from scratch.", args.out,
            )
            return 2
        if (out.get("meta") or {}).get("ollama_model") != args.model:
            log.error(
                "--resume: existing %s was generated with model %r, "
                "now requested %r. Refusing to mix. Use --force.",
                args.out, out["meta"].get("ollama_model"), args.model,
            )
            return 2
        out["meta"]["scenes_count"] = len(scene_inputs)
        out["meta"].pop("error", None)
        out["scenes"] = out.get("scenes") or {}
        already_done = len(out["scenes"])
        log.info("--resume: %d scenes already in %s; %d still to do",
                 already_done, args.out, len(scene_inputs) - already_done)
    else:
        out = {
            "meta": {
                "screenplay": args.screenplay,
                "ollama_model": args.model,
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "scenes_count": len(scene_inputs),
                "system_prompt_sha256": system_prompt_hash(),
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
            },
            "scenes": {},
        }

    t0 = time.monotonic()
    async with httpx.AsyncClient() as client:
        for i, sc in enumerate(scene_inputs):
            if sc["scene_number"] in out["scenes"] and \
                    out["scenes"][sc["scene_number"]].get("enhanced_prompt"):
                log.info("[%d/%d] scene %s already done — skipping",
                         i + 1, len(scene_inputs), sc["scene_number"])
                continue
            t_sc = time.monotonic()
            user = build_user_prompt(
                sc["scene_number"], sc["location"],
                sc["time_of_day"], sc["raw_content"],
            )
            try:
                prompt = await call_ollama(
                    client=client,
                    model=args.model,
                    user_prompt=user,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    ollama_url=args.ollama_url,
                    timeout_seconds=args.timeout_seconds,
                )
            except Exception as e:
                # Loud failure per no-silent-fallbacks: write progress so far
                # and exit non-zero. Future runs with --force will retry.
                out["meta"]["elapsed_seconds"] = round(time.monotonic() - t0, 1)
                out["meta"]["error"] = (
                    f"failed at scene #{i + 1} ({sc['scene_number']}): {e!r}"
                )
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(out, indent=2))
                log.error("Ollama call failed at scene #%d: %s", i + 1, e)
                return 2

            sc_elapsed = time.monotonic() - t_sc
            log.info("[%d/%d] scene %s -> %s … (%.1fs)",
                     i + 1, len(scene_inputs), sc["scene_number"],
                     prompt[:80], sc_elapsed)
            out["scenes"][sc["scene_number"]] = {
                **sc,
                "enhanced_prompt": prompt,
                "elapsed_seconds": round(sc_elapsed, 1),
            }
            # Write incrementally so an unexpected death (OOM, host kill,
            # network blip) preserves every scene completed before the
            # crash. Cost is negligible (<1 ms per write).
            out["meta"]["elapsed_seconds"] = round(time.monotonic() - t0, 1)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(out, indent=2))

    out["meta"]["elapsed_seconds"] = round(time.monotonic() - t0, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    log.info("wrote %d prompts -> %s (total %.1fs)",
             len(out["scenes"]), args.out, out["meta"]["elapsed_seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
