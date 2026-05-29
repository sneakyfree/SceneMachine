"""
Pure-logic tests for marketplace model methods (Performer, PerformanceTake).
Model logic only — the marketplace *surface* stays deferred. Transient
instances, no DB.
"""

from scenemachine.models.performance_take import PerformanceTake, TakeStatus
from scenemachine.models.performer import Performer, PerformerAvailability


def _performer(**kw):
    p = Performer(stage_name="Star")
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_performer_placement_rate():
    assert _performer(total_bookings=0).placement_rate == 50.0
    assert _performer(total_bookings=10, completed_bookings=8).placement_rate == 80.0


def test_performer_is_available():
    assert (
        _performer(is_active=True, availability_status=PerformerAvailability.AVAILABLE).is_available
        is True
    )
    assert (
        _performer(is_active=True, availability_status=PerformerAvailability.BUSY).is_available
        is False
    )


def test_performer_average_rating_none_when_no_ratings():
    p = _performer()
    p.ratings = []
    assert p.average_rating is None


def test_performer_get_price_for_mode():
    assert _performer(pricing={"blink": 9.99}).get_price_for_mode("BLINK") == 9.99
    assert _performer(pricing={"blink": 9.99}).get_price_for_mode("epic") is None
    assert _performer(pricing=None).get_price_for_mode("blink") is None


def test_performer_update_revenue_tier():
    cases = [
        (500, 50.0),
        (5_000, 60.0),
        (50_000, 70.0),
        (500_000, 80.0),
        (5_000_000, 90.0),
        (50_000_000, 99.0),
    ]
    for earnings, expected in cases:
        p = _performer(lifetime_earnings_usd=earnings)
        p.update_revenue_tier()
        assert p.revenue_split_percent == expected


def _take(**kw):
    t = PerformanceTake(take_name="T", duration_seconds=3.0)
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def test_take_motion_score():
    assert _take(quality_metrics={"motion_score": 88.0}).motion_score == 88.0
    assert _take(quality_metrics=None).motion_score == 50.0


def test_take_is_available():
    assert _take(status=TakeStatus.AVAILABLE).is_available is True


def test_take_has_motion_data():
    full = {"liveportrait_vectors_path": "/a", "roop_gs_anim_path": "/b"}
    assert _take(motion_profile=full).has_motion_data is True
    assert _take(motion_profile={"liveportrait_vectors_path": "/a"}).has_motion_data is False
    assert _take(motion_profile=None).has_motion_data is False


def test_take_increment_usage():
    t = _take(usage_count=2)
    t.increment_usage()
    assert t.usage_count == 3
    assert t.last_used_at is not None
