"""Tests for the deterministic screenplay auto-fix transformation (P0-5 core)."""

import copy

from scenemachine.services.screenplay_autofix import apply_auto_fixes


def test_fixes_missing_slugline():
    content = {
        "elements": [
            {"type": "scene_heading", "text": "the kitchen"},  # no INT/EXT
            {"type": "action", "text": "She enters."},
        ]
    }
    fixed, n = apply_auto_fixes(content)
    assert n == 1
    assert fixed["elements"][0]["text"] == "INT. the kitchen"


def test_leaves_valid_slugline_untouched():
    for heading in ("INT. OFFICE - DAY", "EXT. STREET - NIGHT", "I/E CAR - DAY", "est. city"):
        content = {"elements": [{"type": "scene_heading", "text": heading}]}
        fixed, n = apply_auto_fixes(content)
        assert n == 0
        assert fixed["elements"][0]["text"] == heading


def test_names_unnamed_characters_sequentially():
    content = {
        "elements": [
            {"type": "character", "character_name": "", "text": ""},
            {"type": "dialogue", "text": "Hi."},
            {"type": "character", "character_name": "UNNAMED", "text": "UNNAMED"},
            {"type": "character", "character_name": "BOB", "text": "BOB"},  # real → untouched
        ]
    }
    fixed, n = apply_auto_fixes(content)
    assert n == 2
    chars = [e for e in fixed["elements"] if e["type"] == "character"]
    assert chars[0]["character_name"] == "CHARACTER 1"
    assert chars[1]["character_name"] == "CHARACTER 2"
    assert chars[2]["character_name"] == "BOB"
    # roster rebuilt + sorted + deduped
    assert fixed["characters"] == ["BOB", "CHARACTER 1", "CHARACTER 2"]


def test_combined_fixes_count():
    content = {
        "elements": [
            {"type": "scene_heading", "text": "a room"},
            {"type": "character", "character_name": "?", "text": "?"},
        ]
    }
    _, n = apply_auto_fixes(content)
    assert n == 2


def test_noop_on_clean_content_returns_zero():
    content = {
        "elements": [
            {"type": "scene_heading", "text": "INT. OFFICE - DAY"},
            {"type": "character", "character_name": "ALICE", "text": "ALICE"},
        ]
    }
    _, n = apply_auto_fixes(content)
    assert n == 0


def test_does_not_mutate_input():
    content = {"elements": [{"type": "scene_heading", "text": "kitchen"}]}
    original = copy.deepcopy(content)
    apply_auto_fixes(content)
    assert content == original  # input untouched


def test_handles_empty_and_malformed():
    assert apply_auto_fixes({}) == ({}, 0)
    assert apply_auto_fixes({"elements": "not-a-list"})[1] == 0
    assert apply_auto_fixes(None) == (None, 0)
