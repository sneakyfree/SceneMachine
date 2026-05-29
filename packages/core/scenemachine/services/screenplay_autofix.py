"""
Deterministic, non-destructive screenplay auto-fixes.

Closes the auto-fix half of P0-5: the renderer's "Auto-Fix" / "Fix All"
affordances now have a real backend that applies safe, mechanical
corrections to parsed screenplay content. Only deterministic normalizations
are performed (no content invented, nothing deleted) — issues needing
creative/AI judgment are left for manual editing.

Fixes applied:
  1. **Missing sluglines** — a scene-heading element whose text lacks an
     INT/EXT prefix gets ``INT. `` prepended so the downstream scene parser
     can classify it.
  2. **Unnamed characters** — character cues with an empty or generic name
     ("UNNAMED", "CHARACTER", "?", …) are given a stable ``CHARACTER N`` name
     so generation can target them.

The function is pure: it deep-copies the input and returns
``(new_content, fixes_applied)`` without mutating the original.
"""

from __future__ import annotations

import copy
from typing import Any

# Recognised scene-heading prefixes (Fountain-style). Compared case-insensitively.
SLUGLINE_PREFIXES = ("INT.", "EXT.", "INT/EXT", "INT./EXT.", "I/E", "EST.")

# Names that mean "no real name was parsed".
GENERIC_CHARACTER_NAMES = {"", "UNNAMED", "CHARACTER", "UNKNOWN", "?", "N/A"}


def _has_slugline_prefix(text: str) -> bool:
    upper = text.strip().upper()
    return any(upper.startswith(prefix) for prefix in SLUGLINE_PREFIXES)


def apply_auto_fixes(parsed_content: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Apply deterministic auto-fixes to parsed screenplay content.

    Args:
        parsed_content: The screenplay's ``parsed_content`` dict (with an
            ``elements`` list of ``{type, text, character_name, ...}``).

    Returns:
        ``(new_content, fixes_applied)`` — a fixed deep copy and the count of
        fixes made. The original is never mutated.
    """
    if not parsed_content:
        return parsed_content, 0

    content = copy.deepcopy(parsed_content)
    elements = content.get("elements")
    if not isinstance(elements, list):
        return content, 0

    fixes = 0
    unnamed_seq = 0

    for el in elements:
        if not isinstance(el, dict):
            continue
        etype = el.get("type")

        if etype == "scene_heading":
            text = (el.get("text") or "").strip()
            if text and not _has_slugline_prefix(text):
                el["text"] = f"INT. {text}"
                fixes += 1

        elif etype == "character":
            name = (el.get("character_name") or el.get("text") or "").strip()
            if name.upper() in GENERIC_CHARACTER_NAMES:
                unnamed_seq += 1
                new_name = f"CHARACTER {unnamed_seq}"
                el["character_name"] = new_name
                el["text"] = new_name
                fixes += 1

    if fixes:
        # Rebuild the de-duplicated, sorted character roster from the
        # (now-fixed) character cues so it stays consistent.
        names = sorted(
            {
                (el.get("character_name") or "").strip()
                for el in elements
                if isinstance(el, dict)
                and el.get("type") == "character"
                and (el.get("character_name") or "").strip()
            }
        )
        if names:
            content["characters"] = names

    return content, fixes
