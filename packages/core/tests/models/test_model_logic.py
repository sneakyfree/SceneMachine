"""
Pure-logic unit tests for Project model computed properties / state methods.

Exercises in-memory logic on transient instances (no DB, no mocking). First
installment of the coverage ratchet toward the 80% gate — legitimate coverage,
no omits, no gaming. Relationship-member branches (non-empty characters/scenes)
need real mapped instances and are covered by the DB-backed model tests; here
we cover the state-machine + percentage + empty-collection paths.
"""

from scenemachine.models.project import Project, ProjectState


def _proj(state):
    p = Project(name="P", state=state)
    p.characters = []
    p.scenes = []
    p.screenplay = None
    return p


# ---- can_advance (builds the full state→validator map on every call) -----

def test_can_advance_empty_without_screenplay_is_false():
    assert _proj(ProjectState.EMPTY).can_advance is False


def test_can_advance_terminal_states():
    # SCENES_APPROVED / COMPLETE always advance; EXPORTED is final.
    assert _proj(ProjectState.SCENES_APPROVED).can_advance is True
    assert _proj(ProjectState.COMPLETE).can_advance is True
    assert _proj(ProjectState.GENERATION_COMPLETE).can_advance is True
    assert _proj(ProjectState.ASSEMBLY_IN_PROGRESS).can_advance is True
    assert _proj(ProjectState.EXPORTED).can_advance is False


def test_can_advance_empty_collection_gates_are_false():
    # PLAN_APPROVED needs characters; CHARACTERS_LOCKED needs scenes — both empty here.
    assert _proj(ProjectState.PLAN_APPROVED).can_advance is False
    assert _proj(ProjectState.CHARACTERS_LOCKED).can_advance is False
    # all() over empty collections is vacuously True.
    assert _proj(ProjectState.CHARACTERS_IN_PROGRESS).can_advance is True
    assert _proj(ProjectState.SCENES_PLANNING).can_advance is True
    assert _proj(ProjectState.GENERATING).can_advance is True


def test_can_advance_unknown_state_default_false():
    p = _proj(ProjectState.EMPTY)
    p.state = None  # not in the validator map
    assert p.can_advance is False


# ---- next_state ----------------------------------------------------------

def test_next_state_advances_one_step():
    assert _proj(ProjectState.EMPTY).next_state == list(ProjectState)[1]


def test_next_state_final_is_none():
    assert _proj(list(ProjectState)[-1]).next_state is None


def test_next_state_unknown_is_none():
    p = _proj(ProjectState.EMPTY)
    p.state = "not-a-state"
    assert p.next_state is None


# ---- progress_percentage -------------------------------------------------

def test_progress_percentage_endpoints_and_midpoint():
    assert _proj(ProjectState.EMPTY).progress_percentage == 0
    assert _proj(ProjectState.COMPLETE).progress_percentage == 100
    assert _proj(ProjectState.EXPORTED).progress_percentage == 100
    assert 0 < _proj(ProjectState.GENERATING).progress_percentage < 100


def test_progress_percentage_unknown_state_zero():
    p = _proj(ProjectState.EMPTY)
    p.state = None
    assert p.progress_percentage == 0


# ---- counts (empty-collection paths) -------------------------------------

def test_counts_zero_when_empty():
    p = _proj(ProjectState.EMPTY)
    assert p.character_count == 0
    assert p.scene_count == 0
    assert p.locked_character_count == 0
    assert p.approved_scene_count == 0


# ---- repr ----------------------------------------------------------------

def test_repr_contains_name_and_state():
    r = repr(_proj(ProjectState.EMPTY))
    assert "Project" in r and "state=" in r
