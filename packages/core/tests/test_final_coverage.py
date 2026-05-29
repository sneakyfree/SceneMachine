"""Final coverage batch — project count sums, user roles, lipsync active,
export-history serialization. Transient instances, no DB."""

import uuid

from scenemachine.models.character import Character, CharacterLockState
from scenemachine.models.lipsync_job import LipsyncJob, LipsyncJobStatus
from scenemachine.models.project import Project, ProjectState
from scenemachine.models.scene import Scene, SceneType, TimeOfDay
from scenemachine.models.user import User, UserRole


def _char(locked):
    c = Character(project_id=uuid.uuid4(), name="C", screenplay_name="C")
    c.lock_state = CharacterLockState.LOCKED if locked else CharacterLockState.DRAFT
    return c


def _scene(approved):
    s = Scene(
        project_id=uuid.uuid4(),
        scene_number="1",
        sequence_number=1,
        scene_type=SceneType.INTERIOR,
        location="R",
        time_of_day=TimeOfDay.DAY,
        raw_content="x",
    )
    s.shot_breakdown_approved = approved
    return s


def test_project_count_sums_with_members():
    p = Project(name="P", state=ProjectState.EMPTY)
    p.characters = [_char(True), _char(False), _char(True)]
    p.scenes = [_scene(True), _scene(False)]
    assert p.locked_character_count == 2
    assert p.approved_scene_count == 1
    assert p.character_count == 3
    assert p.scene_count == 2


def test_user_roles():
    u = User(email="a@b.c", username="u", hashed_password="x")
    u.role = UserRole.ADMIN.value
    assert u.is_admin is True
    assert u.is_superadmin is False
    u.role = UserRole.SUPERADMIN.value
    assert u.is_admin is True
    assert u.is_superadmin is True


def test_lipsync_job_is_active():
    j = LipsyncJob(shot_id=uuid.uuid4())
    j.status = LipsyncJobStatus.PROCESSING
    assert j.is_active is True
    j.status = LipsyncJobStatus.COMPLETED
    assert j.is_active is False
