"""Tests for scenemachine.services.stack_router.

Routing must be deterministic and side-effect-free — these tests don't
touch any ComfyUI, model file, or filesystem state.
"""
from uuid import uuid4


class TestStackRouter:
    """Per-shot model_id selection for the three Wan stacks."""

    def test_t2v_for_shot_with_no_context(self):
        """A shot with no prior frame and no character references uses T2V —
        the cheapest, fastest path. Establishing shots fall here by default.
        """
        from scenemachine.services.stack_router import MODEL_T2V, route_shot

        decision = route_shot(
            {"character_ids": [], "shot_type": "establishing"},
            prev_shot_last_frame=None,
            character_ref_paths=None,
        )
        assert decision.model_id == MODEL_T2V
        assert decision.input_image_path is None
        assert decision.character_references == []
        assert "t2v" in decision.reason.lower()

    def test_i2v_for_continuity_shot(self):
        """When a previous shot's last frame is provided AND no character
        references are available, the router picks I2V for shot-to-shot
        continuity. This is the typical mid-scene shot.
        """
        from scenemachine.services.stack_router import MODEL_I2V, route_shot

        decision = route_shot(
            {"character_ids": [], "shot_type": "medium"},
            prev_shot_last_frame="prev_shot_last.png",
            character_ref_paths=None,
        )
        assert decision.model_id == MODEL_I2V
        assert decision.input_image_path == "prev_shot_last.png"
        assert decision.character_references == []
        assert "i2v" in decision.reason.lower()

    def test_animate_wins_when_character_reference_exists(self):
        """Animate takes priority over I2V when the shot has at least one
        character with a known reference image. Identity preservation is
        more valuable than frame-to-frame continuity for character shots.
        """
        from scenemachine.services.stack_router import MODEL_ANIMATE, route_shot

        hero_id = str(uuid4())
        decision = route_shot(
            {"character_ids": [hero_id], "shot_type": "close_up"},
            prev_shot_last_frame="prev_last.png",  # would otherwise trigger I2V
            character_ref_paths={hero_id: "hero_ref.png"},
        )
        assert decision.model_id == MODEL_ANIMATE
        assert decision.character_references == [
            {"character_id": hero_id, "reference_image_path": "hero_ref.png"}
        ]
        # I2V's frame is intentionally NOT consumed here — Animate uses its own
        # ref_images chain. The caller can still see prev_last.png was offered
        # via context but the decision didn't pick it.
        assert decision.input_image_path is None
        assert "animate" in decision.reason.lower()

    def test_animate_skipped_when_reference_image_missing(self):
        """Having character_ids on the shot is NOT enough — we need an
        actual reference image. If the character is in the shot but we
        haven't generated/uploaded a reference, fall back to the next
        available stack (I2V if there's continuity, else T2V).
        """
        from scenemachine.services.stack_router import MODEL_I2V, MODEL_T2V, route_shot

        hero_id = str(uuid4())

        # Has continuity → I2V
        d1 = route_shot(
            {"character_ids": [hero_id]},
            prev_shot_last_frame="prev.png",
            character_ref_paths={},  # no ref images
        )
        assert d1.model_id == MODEL_I2V

        # No continuity, no ref → T2V
        d2 = route_shot(
            {"character_ids": [hero_id]},
            prev_shot_last_frame=None,
            character_ref_paths={},
        )
        assert d2.model_id == MODEL_T2V

    def test_animate_with_multiple_characters_only_includes_those_with_refs(self):
        """If 3 characters are in the shot but only 2 have reference images,
        Animate runs with the 2 we can resolve. The character_references
        list reflects only the refs we actually have.
        """
        from scenemachine.services.stack_router import MODEL_ANIMATE, route_shot

        a, b, c = str(uuid4()), str(uuid4()), str(uuid4())
        decision = route_shot(
            {"character_ids": [a, b, c]},
            character_ref_paths={a: "a.png", c: "c.png"},  # b has no ref
        )
        assert decision.model_id == MODEL_ANIMATE
        ids_in_refs = [r["character_id"] for r in decision.character_references]
        assert a in ids_in_refs
        assert c in ids_in_refs
        assert b not in ids_in_refs
        assert len(decision.character_references) == 2

    def test_force_model_id_overrides_all_routing(self):
        """Caller can pass force_model_id to bypass the heuristic — useful
        for "render this shot with T2V even though we have a character
        reference" workflows (quality A/B, debug, user choice in UI).
        """
        from scenemachine.services.stack_router import MODEL_T2V, route_shot

        hero_id = str(uuid4())
        decision = route_shot(
            {"character_ids": [hero_id]},
            prev_shot_last_frame="prev.png",
            character_ref_paths={hero_id: "hero.png"},
            force_model_id=MODEL_T2V,  # explicit override
        )
        assert decision.model_id == MODEL_T2V
        # The router still preserves what context WAS available, so the
        # caller can plumb it through to the provider if their forced model
        # supports it (e.g. force I2V but expose the prev frame).
        assert decision.input_image_path == "prev.png"
        assert len(decision.character_references) == 1

    def test_uuid_objects_in_character_ids_are_normalized(self):
        """character_ids from the DB are UUID objects, not strings. The
        router must handle both — the keying into character_ref_paths
        should work either way.
        """
        from scenemachine.services.stack_router import MODEL_ANIMATE, route_shot

        hero_uuid = uuid4()  # UUID object, not str
        decision = route_shot(
            {"character_ids": [hero_uuid]},  # list contains UUID object
            character_ref_paths={str(hero_uuid): "hero.png"},
        )
        assert decision.model_id == MODEL_ANIMATE
        assert decision.character_references[0]["character_id"] == str(hero_uuid)

    def test_reason_string_is_populated_for_every_decision(self):
        """Every StackDecision must have a non-empty reason — for logging,
        UI display, and debugging. Future regressions that drop the reason
        would make pipeline logs unhelpful.
        """
        from scenemachine.services.stack_router import route_shot

        for shot_data, prev, refs in [
            ({"character_ids": []}, None, None),
            ({"character_ids": []}, "prev.png", None),
            ({"character_ids": ["x"]}, None, {"x": "x.png"}),
        ]:
            d = route_shot(shot_data, prev_shot_last_frame=prev,
                           character_ref_paths=refs)
            assert d.reason, f"empty reason for inputs {shot_data}, {prev}, {refs}"
