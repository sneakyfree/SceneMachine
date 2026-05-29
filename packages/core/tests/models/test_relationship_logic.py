"""
Logic tests that need real mapped child instances (not SimpleNamespace) on
relationships, plus Base.to_dict's datetime branch. Transient instances, no DB.
"""

import datetime
import uuid

from scenemachine.models.scene import Scene, SceneType, TimeOfDay
from scenemachine.models.shot import Shot, ShotState, ShotType


def _scene():
    return Scene(
        project_id=uuid.uuid4(),
        scene_number="1",
        sequence_number=1,
        scene_type=SceneType.INTERIOR,
        location="Room",
        time_of_day=TimeOfDay.DAY,
        raw_content="INT. ROOM - DAY",
    )


def _shot(state):
    s = Shot(
        scene_id=uuid.uuid4(),
        shot_number="1",
        sequence_number=1,
        shot_type=ShotType.WIDE,
        description="d",
    )
    s.state = state
    return s


def test_scene_generation_progress():
    sc = _scene()
    sc.shots = [_shot(ShotState.GENERATED), _shot(ShotState.PLANNED)]
    assert sc.generation_progress == 50.0
    empty = _scene()
    empty.shots = []
    assert empty.generation_progress == 0.0


def test_scene_all_shots_approved():
    sc = _scene()
    sc.shots = [_shot(ShotState.APPROVED), _shot(ShotState.GENERATED)]
    assert sc.all_shots_approved is False
    sc.shots = [_shot(ShotState.APPROVED), _shot(ShotState.APPROVED)]
    assert sc.all_shots_approved is True
    empty = _scene()
    empty.shots = []
    assert empty.all_shots_approved is False


def test_base_to_dict_datetime_branch():
    # Base.to_dict isoformats datetime column values.
    sc = _scene()
    sc.created_at = datetime.datetime(2026, 1, 2, 3, 4, 5)
    d = sc.to_dict()
    assert d["created_at"] == "2026-01-02T03:04:05"
    assert d["scene_number"] == "1"
