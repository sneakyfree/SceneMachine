"""Stack router — picks the right model_id per shot.

SceneMachine has three actively-validated Wan stacks:

  * wan22-t2v-14b-fp8   — text-only seed; for establishing shots and any
                          shot without a prior frame or character reference
  * wan22-i2v-14b-fp8   — image-to-video; for shot-to-shot continuity
                          (last frame of prior shot seeds the next)
  * wan22-animate-14b   — character-ID-preserving; for shots with a
                          character reference image, faces, dialogue

The router is intentionally a small pure function rather than a class.
It takes the shot metadata + optional context (prior shot output, available
character reference images) and returns a routing decision.

The caller (the production pipeline) is responsible for actually:
  * extracting the last frame of a prior shot if I2V is chosen
  * uploading character reference images to ComfyUI's input dir
  * passing the decision into a GenerationRequest before calling the provider
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Canonical model_ids — must match scenemachine/generators/comfyui.py MODELS
MODEL_T2V = "wan22-t2v-14b-fp8"
MODEL_I2V = "wan22-i2v-14b-fp8"
MODEL_ANIMATE = "wan22-animate-14b"


@dataclass
class StackDecision:
    """The router's verdict for one shot.

    Attributes:
        model_id: Which provider model to use (matches comfyui.py registry keys).
        input_image_path: For I2V, the previous shot's last frame (filename
            already uploaded to ComfyUI's input dir). None for T2V/Animate.
        character_references: For Animate, list of {character_id,
            reference_image_path} dicts. Empty for T2V/I2V.
        extra_params: Provider-level overrides (e.g. force speed_lora off
            for a quality-comparison run). Caller can merge their own.
        reason: Human-readable explanation of why this stack was chosen —
            useful for debug logs and for the UI to surface to the user.
    """

    model_id: str
    input_image_path: str | None = None
    character_references: list[dict[str, Any]] = field(default_factory=list)
    extra_params: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


def route_shot(
    shot_data: dict[str, Any],
    *,
    prev_shot_last_frame: str | None = None,
    character_ref_paths: dict[str, str] | None = None,
    force_model_id: str | None = None,
) -> StackDecision:
    """Pick the right stack for a shot.

    Routing rules (in priority order):

      1. ``force_model_id`` — explicit override (caller-supplied; respects
         user choice in the UI). No further routing happens.
      2. Animate — if the shot has character_ids AND we have at least one
         reference image path keyed by one of those character UUIDs.
      3. I2V — if a previous shot's last frame is available (continuity).
      4. T2V — fallback for establishing shots / shots with no prior context.

    Args:
        shot_data: Dict with at least ``character_ids: list[str]``. Other
            fields tolerated: ``shot_type``, ``description`` (used for the
            reason string), ``generation_params``.
        prev_shot_last_frame: ComfyUI-input-relative filename of the last
            frame of the previous shot, if continuity is wanted.
        character_ref_paths: Map of character_id -> reference image
            filename (already uploaded to ComfyUI's input dir).
        force_model_id: Override the routing decision entirely.

    Returns:
        StackDecision with model_id and any required side-channel inputs.
    """
    if force_model_id:
        return StackDecision(
            model_id=force_model_id,
            input_image_path=prev_shot_last_frame,
            character_references=_build_character_refs(
                shot_data.get("character_ids", []),
                character_ref_paths or {},
            ),
            reason=f"forced by caller: {force_model_id}",
        )

    character_ids = list(shot_data.get("character_ids", []) or [])
    refs = _build_character_refs(character_ids, character_ref_paths or {})

    # Animate wins when we have characters AND can reference them
    if refs:
        return StackDecision(
            model_id=MODEL_ANIMATE,
            character_references=refs,
            reason=(
                f"animate: {len(refs)} character reference"
                f"{'s' if len(refs) != 1 else ''} available"
            ),
        )

    # I2V for shot-to-shot continuity
    if prev_shot_last_frame:
        return StackDecision(
            model_id=MODEL_I2V,
            input_image_path=prev_shot_last_frame,
            reason="i2v: continuity from previous shot's last frame",
        )

    # T2V fallback
    return StackDecision(
        model_id=MODEL_T2V,
        reason="t2v: no prior frame, no character references",
    )


def _build_character_refs(
    character_ids: list[Any],
    character_ref_paths: dict[str, str],
) -> list[dict[str, Any]]:
    """Build the character_references list a provider expects.

    Only includes characters for which we actually have a reference image
    on disk. Skips silently rather than crashing — the caller can decide
    whether a partial set is acceptable.
    """
    refs: list[dict[str, Any]] = []
    for cid in character_ids:
        # Normalise to str — character_ids may be UUID objects
        key = str(cid)
        path = character_ref_paths.get(key)
        if not path:
            continue
        refs.append({
            "character_id": key,
            "reference_image_path": path,
        })
    return refs
