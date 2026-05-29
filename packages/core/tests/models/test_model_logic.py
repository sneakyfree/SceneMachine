"""
Pure-logic unit tests for Project model computed properties / state methods.

Exercises in-memory logic on transient instances (no DB, no mocking). First
installment of the coverage ratchet toward the 80% gate — legitimate coverage,
no omits, no gaming. Relationship-member branches (non-empty characters/scenes)
need real mapped instances and are covered by the DB-backed model tests; here
we cover the state-machine + percentage + empty-collection paths.
"""

import datetime
import uuid

from scenemachine.models.audio_asset import AudioAsset, AudioAssetType
from scenemachine.models.character import Character, CharacterLockState
from scenemachine.models.generation_job import GenerationJob, JobStatus, JobType
from scenemachine.models.project import Project, ProjectState
from scenemachine.models.scene import Scene, SceneState, SceneType, TimeOfDay
from scenemachine.models.screenplay import Screenplay
from scenemachine.models.settings import UserSettings
from scenemachine.models.shot import CameraMovement, Shot, ShotState, ShotType


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


# ==========================================================================
# Scene model logic
# ==========================================================================

def _scene(**kw):
    s = Scene(
        project_id=uuid.uuid4(),
        scene_number="1",
        sequence_number=1,
        scene_type=SceneType.INTERIOR,
        location="A Room",
        time_of_day=TimeOfDay.DAY,
        raw_content="INT. A ROOM - DAY",
    )
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def test_scene_heading_basic():
    assert _scene().heading == "INT. A ROOM - DAY"


def test_scene_heading_exterior_with_sublocation():
    s = _scene(scene_type=SceneType.EXTERIOR, sub_location="Front porch", time_of_day=TimeOfDay.NIGHT)
    assert s.heading == "EXT. A ROOM - FRONT PORCH - NIGHT"


def test_scene_heading_interior_exterior():
    assert _scene(scene_type=SceneType.INTERIOR_EXTERIOR).heading.startswith("INT./EXT.")


def test_scene_shot_count_from_breakdown():
    assert _scene(shot_breakdown={"total_shots": 7}).shot_count == 7


def test_scene_is_ready_for_generation():
    ready = _scene(
        state=SceneState.PLAN_APPROVED,
        shot_breakdown={"total_shots": 1},
        shot_breakdown_approved=True,
    )
    assert ready.is_ready_for_generation is True
    assert _scene(state=SceneState.PARSED).is_ready_for_generation is False


def test_scene_can_transition_to():
    s = _scene(state=SceneState.PARSED)
    assert s.can_transition_to(SceneState.PLANNED) is True
    assert s.can_transition_to(SceneState.GENERATING) is False


# ==========================================================================
# Shot model logic
# ==========================================================================

def _shot(**kw):
    sh = Shot(
        scene_id=uuid.uuid4(),
        shot_number="1A",
        sequence_number=1,
        shot_type=ShotType.WIDE,
        description="A wide view of the room.",
    )
    for k, v in kw.items():
        setattr(sh, k, v)
    return sh


def test_shot_state_flags():
    assert _shot(state=ShotState.GENERATED).is_generated is True
    assert _shot(state=ShotState.PLANNED).is_generated is False
    assert _shot(state=ShotState.APPROVED).is_approved is True
    assert _shot(state=ShotState.REJECTED).needs_regeneration is True
    assert _shot(state=ShotState.FAILED).needs_regeneration is True


def test_shot_has_output():
    assert _shot(output_video_path=None).has_output is False
    assert _shot(output_video_path="/tmp/x.mp4").has_output is True


def test_shot_display_label():
    assert _shot().display_label == "Shot 1A - Wide"


def test_shot_generation_cost():
    assert _shot(generation_metadata=None).generation_cost is None
    assert _shot(generation_metadata={"cost_estimate_usd": 1.25}).generation_cost == 1.25


def test_shot_can_transition_to():
    s = _shot(state=ShotState.PLANNED)
    assert s.can_transition_to(ShotState.QUEUED) is True
    assert s.can_transition_to(ShotState.APPROVED) is False


def test_shot_get_full_prompt_combines_fields():
    sh = _shot(
        camera_movement=CameraMovement.PAN,
        action="She turns.",
        composition_notes="Rule of thirds",
        lighting_notes="Soft key",
        color_notes="Warm",
    )
    prompt = sh.get_full_prompt()
    assert "wide shot" in prompt
    assert "movement" in prompt
    assert "Action: She turns." in prompt
    assert "Composition: Rule of thirds" in prompt
    assert "Lighting: Soft key" in prompt
    assert "Color: Warm" in prompt


def test_shot_repr():
    assert "Shot" in repr(_shot(state=ShotState.PLANNED))


# ==========================================================================
# Character model logic
# ==========================================================================

def _char_model(**kw):
    c = Character(project_id=uuid.uuid4(), name="Bob", screenplay_name="BOB")
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def test_character_is_locked():
    assert _char_model(lock_state=CharacterLockState.LOCKED).is_locked is True
    assert _char_model(lock_state=CharacterLockState.DRAFT).is_locked is False


def test_character_display_name():
    assert _char_model(name="Bob", screenplay_name="BOB").display_name == "Bob"
    assert _char_model(name="SAME", screenplay_name="SAME").display_name == "SAME"


def test_character_age_display_variants():
    assert _char_model(age_range_min=30, age_range_max=30).age_display == "30"
    assert _char_model(age_range_min=30, age_range_max=40).age_display == "30-40"
    assert _char_model(age_range_min=30, age_range_max=None).age_display == "30+"
    assert _char_model(age_range_min=None, age_range_max=18).age_display == "Under 18"
    assert _char_model(age_range_min=None, age_range_max=None).age_display is None


def test_character_importance_score_caps():
    # protagonist (50) + scene cap (30) + dialogue cap (20) = 100
    c = _char_model(is_protagonist=True, scene_count=100, dialogue_count=100)
    assert c.importance_score == 100.0
    # non-protagonist, modest presence
    c2 = _char_model(is_protagonist=False, scene_count=3, dialogue_count=4)
    assert c2.importance_score == 3 * 2 + 4 * 0.5


def test_character_lock_progress_percentage():
    assert _char_model(lock_state=CharacterLockState.UNDEFINED).lock_progress_percentage == 0
    assert _char_model(lock_state=CharacterLockState.LOCKED).lock_progress_percentage == 100
    assert _char_model(lock_state=CharacterLockState.REVIEW).lock_progress_percentage == 80


def test_character_can_transition_to():
    c = _char_model(lock_state=CharacterLockState.UNDEFINED)
    assert c.can_transition_to(CharacterLockState.DRAFT) is True
    assert c.can_transition_to(CharacterLockState.LOCKED) is False


# ==========================================================================
# GenerationJob model logic
# ==========================================================================

def _job(**kw):
    j = GenerationJob(shot_id=uuid.uuid4(), status=JobStatus.PENDING)
    for k, v in kw.items():
        setattr(j, k, v)
    return j


def test_job_status_flags():
    assert _job(status=JobStatus.RUNNING).is_active is True
    assert _job(status=JobStatus.COMPLETED).is_active is False
    assert _job(status=JobStatus.COMPLETED).is_complete is True
    assert _job(status=JobStatus.RUNNING).is_complete is False
    assert _job(status=JobStatus.COMPLETED).is_successful is True
    assert _job(status=JobStatus.FAILED).is_successful is False


def test_job_can_retry():
    assert _job(status=JobStatus.FAILED, retry_count=1, max_retries=3).can_retry is True
    assert _job(status=JobStatus.FAILED, retry_count=3, max_retries=3).can_retry is False
    assert _job(status=JobStatus.RUNNING, retry_count=0, max_retries=3).can_retry is False


def test_job_duration_and_wait():
    t0 = datetime.datetime(2026, 1, 1, 10, 0, 0)
    t1 = datetime.datetime(2026, 1, 1, 10, 0, 30)
    t2 = datetime.datetime(2026, 1, 1, 10, 1, 0)
    j = _job(queued_at=t0, started_at=t1, completed_at=t2)
    assert j.wait_time_seconds == 30.0
    assert j.duration_seconds == 30.0
    assert _job(started_at=None, completed_at=None).duration_seconds is None
    assert _job(queued_at=None, started_at=None).wait_time_seconds is None


def test_job_costs():
    j = _job(cost_info={"estimated_cost_usd": 1.0, "actual_cost_usd": 1.5})
    assert j.estimated_cost == 1.0
    assert j.actual_cost == 1.5
    assert j.cost_usd == 1.5  # prefers actual
    assert _job(cost_info=None).cost_usd == 0.0


def test_job_can_transition_to():
    assert _job(status=JobStatus.PENDING).can_transition_to(JobStatus.QUEUED) is True
    assert _job(status=JobStatus.COMPLETED).can_transition_to(JobStatus.RUNNING) is False


def test_job_repr():
    assert "GenerationJob" in repr(
        _job(status=JobStatus.PENDING, job_type=list(JobType)[0], progress=0.0)
    )


# ==========================================================================
# UserSettings model logic (API-key crypto, masking, to_dict)
# ==========================================================================

def test_settings_mask_api_key():
    s = UserSettings()
    assert s.mask_api_key("abc") == "****"          # too short
    assert s.mask_api_key("") == "****"             # empty
    assert s.mask_api_key("sk-1234567890") == "sk-1...7890"


def test_settings_api_key_roundtrip_all_providers():
    s = UserSettings()
    s.anthropic_api_key = "sk-ant-0000000000"
    s.openai_api_key = "sk-oai-1111111111"
    s.replicate_api_key = "r8-2222222222"
    s.fal_api_key = "fal-3333333333"
    s.runwayml_api_key = "rw-4444444444"
    assert s.anthropic_api_key == "sk-ant-0000000000"
    assert s.openai_api_key == "sk-oai-1111111111"
    assert s.replicate_api_key == "r8-2222222222"
    assert s.fal_api_key == "fal-3333333333"
    assert s.runwayml_api_key == "rw-4444444444"


def test_settings_has_api_key():
    s = UserSettings()
    assert s.has_api_key("anthropic") is False
    s.anthropic_api_key = "sk-ant-0000000000"
    assert s.has_api_key("anthropic") is True
    assert s.has_api_key("ANTHROPIC") is True  # case-insensitive
    assert s.has_api_key("openai") is False


def test_settings_to_dict_without_keys():
    d = UserSettings().to_dict(include_keys=False)
    assert "apiKeys" not in d
    assert "llmProvider" in d and "themeMode" in d


def test_settings_to_dict_with_keys_masks_configured():
    s = UserSettings()
    s.anthropic_api_key = "sk-ant-0000000000"
    d = s.to_dict(include_keys=True)
    assert d["apiKeys"]["anthropic"]["configured"] is True
    assert d["apiKeys"]["anthropic"]["masked"] is not None
    assert d["apiKeys"]["openai"]["configured"] is False
    assert d["apiKeys"]["openai"]["masked"] is None


# ==========================================================================
# Screenplay model logic (parsed_content accessors)
# ==========================================================================

def _screenplay(parsed=None):
    sp = Screenplay(
        project_id=uuid.uuid4(),
        original_filename="s.fountain",
        original_format="fountain",
        file_hash="0" * 64,
        original_file_path="/tmp/s.fountain",
    )
    sp.parsed_content = parsed
    return sp


def test_screenplay_accessors_empty_when_unparsed():
    sp = _screenplay(None)
    assert sp.title is None
    assert sp.author is None
    assert sp.character_names == []
    assert sp.scene_count == 0
    assert sp.page_count is None


def test_screenplay_accessors_from_parsed_content():
    sp = _screenplay(
        {
            "title_page": {"title": "My Movie", "author": "Me"},
            "elements": [
                {"type": "character", "name": "bob"},
                {"type": "scene_heading"},
                {"type": "character", "name": "BOB"},  # dedups with 'bob' (upper)
                {"type": "character", "name": "alice"},
            ],
            "metadata": {"page_count": 12},
        }
    )
    assert sp.title == "My Movie"
    assert sp.author == "Me"
    assert sp.character_names == ["ALICE", "BOB"]  # deduped, uppercased, sorted
    assert sp.scene_count == 1
    assert sp.page_count == 12


# ==========================================================================
# AudioAsset model logic (type flags + human-readable formatting)
# ==========================================================================

def _audio(**kw):
    a = AudioAsset(
        asset_type=kw.pop("asset_type", AudioAssetType.MUSIC),
        name="track",
        file_path="/tmp/a.wav",
    )
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def test_audio_type_flags():
    assert _audio(asset_type=AudioAssetType.SOUND_EFFECT).is_sound_effect is True
    assert _audio(asset_type=AudioAssetType.SOUND_EFFECT).is_music is False
    assert _audio(asset_type=AudioAssetType.MUSIC).is_music is True


def test_audio_duration_display():
    assert _audio(duration_seconds=0.25).duration_display == "250ms"
    assert _audio(duration_seconds=45).duration_display == "45s"
    assert _audio(duration_seconds=90).duration_display == "1:30"


def test_audio_file_size_display():
    assert _audio(file_size_bytes=None).file_size_display is None
    assert _audio(file_size_bytes=512).file_size_display == "512.0 B"
    assert _audio(file_size_bytes=2048).file_size_display == "2.0 KB"
    assert _audio(file_size_bytes=5 * 1024 * 1024).file_size_display == "5.0 MB"
