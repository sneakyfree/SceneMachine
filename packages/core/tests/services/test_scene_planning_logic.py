"""
Pure-logic tests for ScenePlanningService's heuristic helpers — scene
analysis, mood/pacing/key-moments, shot generation, and coverage styling.
These methods don't touch the DB (the service is built with session=None).
"""

import uuid

from scenemachine.models.scene import Scene, SceneType, TimeOfDay
from scenemachine.models.shot import CameraMovement, ShotType
from scenemachine.services.scene_planning import ScenePlanningService

SVC = ScenePlanningService(None)


def _scene(**kw):
    s = Scene(
        project_id=uuid.uuid4(),
        scene_number="1",
        sequence_number=1,
        scene_type=kw.pop("scene_type", SceneType.INTERIOR),
        location=kw.pop("location", "Office"),
        time_of_day=kw.pop("time_of_day", TimeOfDay.NIGHT),
        raw_content=kw.pop("raw_content", "Action here."),
    )
    for k, v in kw.items():
        setattr(s, k, v)
    return s


# ---- _determine_mood -----------------------------------------------------

def test_determine_mood_keywords_and_default():
    assert SVC._determine_mood("he pulls a gun, danger and fear") == "tense"
    assert SVC._determine_mood("they kiss with love and tender embrace") == "romantic"
    assert SVC._determine_mood("") == "neutral"


# ---- _determine_pacing ---------------------------------------------------

def test_determine_pacing_branches():
    assert SVC._determine_pacing("x", action_heavy=True, dialogue_heavy=False).startswith("fast")
    assert "measured" in SVC._determine_pacing("x", False, True)
    assert "slow" in SVC._determine_pacing("they move slowly", False, False)
    assert "moderate" in SVC._determine_pacing("ordinary", False, False)


# ---- _extract_key_moments ------------------------------------------------

def test_extract_key_moments_importance_and_limit():
    lines = ["She reveals the truth", "He looks around", "nothing notable here"]
    moments = SVC._extract_key_moments(lines)
    importances = {m["importance"] for m in moments}
    assert "high" in importances  # "reveals"
    assert "medium" in importances  # "looks"
    assert all(m["importance"] != "low" for m in moments)
    # 30 high-importance lines → capped at 10
    assert len(SVC._extract_key_moments(["suddenly!"] * 30)) == 10


# ---- _generate_emotional_arc ---------------------------------------------

def test_generate_emotional_arc():
    arc = SVC._generate_emotional_arc(
        "they argue then discover a secret then exit",
        [{"description": "He enters the room"}],
    )
    assert arc[0] == "anticipation"
    assert len(arc) >= 2
    # No moments + bland content → starts neutral, ends with a closing emotion.
    bland = SVC._generate_emotional_arc("plain", [])
    assert bland[0] == "neutral" and len(bland) >= 2


# ---- _suggest_visual_style -----------------------------------------------

def test_suggest_visual_style():
    s = _scene(scene_type=SceneType.INTERIOR, time_of_day=TimeOfDay.NIGHT)
    styles = SVC._suggest_visual_style(s, "tense")
    assert any("low-key" in x for x in styles)
    assert any("interior" in x for x in styles)
    assert any("contrast" in x for x in styles)


# ---- _estimate_importance / _suggest_shot_count --------------------------

def test_estimate_importance_clamped():
    s = _scene(character_ids=[uuid.uuid4() for _ in range(4)])
    assert 1 <= SVC._estimate_importance(s, dialogue_count=20, action_count=10) <= 10
    s0 = _scene(character_ids=[])
    assert SVC._estimate_importance(s0, 0, 0) >= 1


def test_suggest_shot_count_clamped():
    assert SVC._suggest_shot_count(0, 0, 1) >= 3
    assert SVC._suggest_shot_count(100, 100, 10) <= 20


# ---- _generate_scene_summary ---------------------------------------------

def test_generate_scene_summary():
    s = _scene(location="Rooftop")
    with_moments = SVC._generate_scene_summary(s, [{"description": "A fight"}])
    assert "Rooftop" in with_moments and "fight" in with_moments
    assert "Rooftop" in SVC._generate_scene_summary(s, [])


# ---- analysis chain + shot generation ------------------------------------

def test_analyze_scene_content_full_chain():
    s = _scene(
        raw_content="He pulls a gun. Danger. slowly.",
        action_lines=["She reveals the secret", "He looks around"],
        character_ids=[uuid.uuid4(), uuid.uuid4()],
    )
    a = SVC._analyze_scene_content(s)
    assert a.mood == "tense"
    assert a.suggested_shot_count >= 3
    assert isinstance(a.key_moments, list)


def test_generate_shots_produces_specs():
    s = _scene(
        scene_type=SceneType.EXTERIOR,
        character_ids=[uuid.uuid4(), uuid.uuid4()],
        action_lines=["He reveals it"],
    )
    a = SVC._analyze_scene_content(s)
    shots = SVC._generate_shots(s, a)
    assert len(shots) >= 3
    # Exterior → first shot is an establishing shot
    assert shots[0].shot_type == ShotType.ESTABLISHING


def test_suggest_shot_for_moment():
    assert SVC._suggest_shot_for_moment({"description": "she reveals", "importance": "high"}) == (
        ShotType.CLOSE_UP,
        CameraMovement.DOLLY,
    )
    assert SVC._suggest_shot_for_moment({"description": "he enters", "importance": "high"}) == (
        ShotType.MEDIUM,
        CameraMovement.TRACKING,
    )
    assert SVC._suggest_shot_for_moment({"description": "he looks", "importance": "medium"})[0] == (
        ShotType.MEDIUM_CLOSE_UP
    )


# ---- coverage style + approach -------------------------------------------

def test_coverage_style_and_approach():
    s = _scene(raw_content="fight chase run", action_lines=["a", "b", "c", "d", "e", "f"])
    a = SVC._analyze_scene_content(s)
    assert isinstance(SVC._determine_coverage_style(a), str)
    assert SVC._generate_approach_description(a).startswith("Coverage approach")
