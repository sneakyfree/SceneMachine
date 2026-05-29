"""
Pure-logic tests for Auction + AuctionBid status/reserve/timing properties.
Transient instances, no DB.
"""

import datetime

from scenemachine.models.auction import (
    Auction,
    AuctionBid,
    AuctionStatus,
    BidStatus,
)

UTC = datetime.UTC


def _auction(**kw):
    a = Auction(title="T", min_bid_usd=10.0)
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def test_auction_is_open():
    assert _auction(status=AuctionStatus.OPEN).is_open is True
    assert _auction(status=AuctionStatus.CLOSED).is_open is False


def test_auction_time_remaining():
    future = datetime.datetime.now(UTC) + datetime.timedelta(hours=1)
    past = datetime.datetime.now(UTC) - datetime.timedelta(hours=1)
    assert _auction(closes_at=future).time_remaining_seconds > 0
    assert _auction(closes_at=past).time_remaining_seconds is None
    assert _auction(closes_at=None).time_remaining_seconds is None


def test_auction_reserve_met():
    # No reserve → always met.
    assert _auction(reserve_price_usd=None).reserve_met is True
    # Reserve set, highest bid meets it.
    assert _auction(reserve_price_usd=100.0, highest_bid_usd=120.0).reserve_met is True
    # Reserve set, highest below.
    assert _auction(reserve_price_usd=100.0, highest_bid_usd=50.0).reserve_met is False
    # Reserve set, no bids.
    assert _auction(reserve_price_usd=100.0, highest_bid_usd=None).reserve_met is False


def _bid(**kw):
    b = AuctionBid(bid_amount_usd=50.0)
    for k, v in kw.items():
        setattr(b, k, v)
    return b


def test_bid_status_flags():
    assert _bid(status=BidStatus.ACTIVE).is_active is True
    assert _bid(status=BidStatus.ACCEPTED).is_active is False
    assert _bid(status=BidStatus.ACCEPTED).is_winning is True
    assert _bid(status=BidStatus.ACTIVE).is_winning is False
