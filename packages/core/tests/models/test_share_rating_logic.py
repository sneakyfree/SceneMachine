"""
Pure-logic tests for ProjectShare permission gating and PerformerRating
score aggregation. Transient instances, no DB.
"""

import uuid

from scenemachine.models.performer_rating import PerformerRating
from scenemachine.models.share import ProjectShare, SharePermission, ShareStatus


def _share(permission, status=ShareStatus.ACCEPTED, **kw):
    s = ProjectShare(project_id=uuid.uuid4(), permission=permission, status=status)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def test_share_is_valid():
    assert _share(SharePermission.VIEW, status=ShareStatus.ACCEPTED).is_valid() is True
    assert _share(SharePermission.VIEW, status=ShareStatus.PENDING).is_valid() is True
    assert _share(SharePermission.VIEW, status=ShareStatus.REVOKED).is_valid() is False


def test_share_permission_tiers():
    viewer = _share(SharePermission.VIEW)
    assert viewer.can_view() is True
    assert viewer.can_comment() is False
    assert viewer.can_edit() is False
    assert viewer.can_admin() is False

    editor = _share(SharePermission.EDIT)
    assert editor.can_view() is True
    assert editor.can_comment() is True
    assert editor.can_edit() is True
    assert editor.can_admin() is False

    admin = _share(SharePermission.ADMIN)
    assert admin.can_admin() is True


def test_share_invalid_denies_all():
    revoked = _share(SharePermission.ADMIN, status=ShareStatus.REVOKED)
    assert revoked.can_view() is False
    assert revoked.can_admin() is False


def _rating(**kw):
    r = PerformerRating(performer_id=uuid.uuid4(), overall_score=4.0)
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def test_rating_average_detailed_score():
    r = _rating(
        motion_quality_score=80,
        emotion_accuracy_score=60,
        professionalism_score=None,
        timeliness_score=None,
    )
    assert r.average_detailed_score == 70.0


def test_rating_average_detailed_none_when_all_missing():
    r = _rating(
        motion_quality_score=None,
        emotion_accuracy_score=None,
        professionalism_score=None,
        timeliness_score=None,
    )
    assert r.average_detailed_score is None
    assert r.has_detailed_scores is False


def test_rating_has_detailed_scores_true():
    assert _rating(motion_quality_score=90).has_detailed_scores is True


def test_rating_engagement_score():
    assert _rating(audience_buzz_votes=10, helpful_votes=4).engagement_score == 12.0
