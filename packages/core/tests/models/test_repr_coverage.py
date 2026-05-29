"""__repr__ coverage for marketplace models."""

from scenemachine.models.auction import Auction, AuctionStatus
from scenemachine.models.performer import Performer, PerformerType


def test_auction_repr():
    a = Auction(title="Lot 1", min_bid_usd=10.0)
    a.status = AuctionStatus.OPEN
    a.total_bids = 3
    assert "Auction" in repr(a) and "Lot 1" in repr(a)


def test_performer_repr():
    p = Performer(stage_name="Nova")
    p.performer_type = PerformerType.SYNTHETIC
    p.aci_score = 7.5
    assert "Performer" in repr(p) and "Nova" in repr(p)
