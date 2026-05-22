"""Tests for performer IPC handlers."""

from datetime import UTC
from uuid import uuid4

import pytest

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer
from scenemachine.models import (
    Performer,
    PerformerAvailability,
    PerformerType,
    PerformerVerification,
)


@pytest.fixture
def ipc_server():
    """Create IPC server with registered handlers."""
    server = IPCServer("/tmp/test_scenemachine.sock")
    register_handlers(server)
    return server


@pytest.fixture
async def sample_performers(db_session):
    """Create sample performers for testing."""
    from datetime import datetime

    performers = []

    # Create diverse performers
    performer_data = [
        {
            "stage_name": "Alex Thunder",
            "bio": "Action star specialist",
            "specialties": ["action", "stunts"],
            "aci_score": 92.5,
            "performer_type": PerformerType.SYNTHETIC,
            "availability_status": PerformerAvailability.AVAILABLE,
            "verification_status": PerformerVerification.VERIFIED,
            "pricing": {"blink": 15.0, "deep": 75.0, "epic_per_minute": 25.0},
            "total_bookings": 150,
            "completed_bookings": 145,
            "lifetime_earnings_usd": 45000.0,
            "joined_at": datetime.now(UTC),
        },
        {
            "stage_name": "Sarah Grace",
            "bio": "Drama and emotional scenes",
            "specialties": ["drama", "emotional"],
            "aci_score": 88.0,
            "performer_type": PerformerType.HUMAN,
            "availability_status": PerformerAvailability.AVAILABLE,
            "verification_status": PerformerVerification.VERIFIED,
            "pricing": {"blink": 20.0, "deep": 100.0, "epic_per_minute": 35.0},
            "total_bookings": 100,
            "completed_bookings": 98,
            "lifetime_earnings_usd": 35000.0,
            "joined_at": datetime.now(UTC),
        },
        {
            "stage_name": "Mike Comedy",
            "bio": "Comedy and improv expert",
            "specialties": ["comedy", "improv"],
            "aci_score": 75.0,
            "performer_type": PerformerType.SYNTHETIC,
            "availability_status": PerformerAvailability.BUSY,
            "verification_status": PerformerVerification.PENDING,
            "pricing": {"blink": 10.0, "deep": 50.0, "epic_per_minute": 15.0},
            "total_bookings": 50,
            "completed_bookings": 48,
            "lifetime_earnings_usd": 10000.0,
            "joined_at": datetime.now(UTC),
        },
    ]

    for data in performer_data:
        performer = Performer(id=uuid4(), **data)
        db_session.add(performer)
        performers.append(performer)

    await db_session.commit()
    for p in performers:
        await db_session.refresh(p)

    return performers


class TestPerformerSearchHandler:
    """Tests for performers.search handler."""

    @pytest.mark.asyncio
    async def test_search_returns_all_performers(self, ipc_server, sample_performers):
        """Test basic search returns all performers."""
        handler = ipc_server.handlers.get("performers.search")
        assert handler is not None

        result = await handler()

        assert "performers" in result
        assert "total" in result
        assert "hasMore" in result
        assert result["total"] >= 3

    @pytest.mark.asyncio
    async def test_search_with_query(self, ipc_server, sample_performers):
        """Test search with text query."""
        handler = ipc_server.handlers.get("performers.search")

        result = await handler(query="Action")

        performers = result["performers"]
        assert len(performers) >= 1
        assert any("Thunder" in p["stage_name"] for p in performers)

    @pytest.mark.asyncio
    async def test_search_with_performer_type_filter(self, ipc_server, sample_performers):
        """Test filtering by performer type."""
        handler = ipc_server.handlers.get("performers.search")

        result = await handler(performer_type="human")

        performers = result["performers"]
        assert all(p["performer_type"] == "HUMAN" for p in performers)

    @pytest.mark.asyncio
    async def test_search_with_min_aci(self, ipc_server, sample_performers):
        """Test filtering by minimum ACI score."""
        handler = ipc_server.handlers.get("performers.search")

        result = await handler(min_aci=85.0)

        performers = result["performers"]
        assert all(p["aci_score"] >= 85.0 for p in performers)

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, ipc_server, sample_performers):
        """Test pagination works correctly."""
        handler = ipc_server.handlers.get("performers.search")

        # Get first page
        result1 = await handler(limit=2, offset=0)
        # Get second page
        result2 = await handler(limit=2, offset=2)

        assert len(result1["performers"]) <= 2
        # Check no overlap between pages
        ids1 = {p["id"] for p in result1["performers"]}
        ids2 = {p["id"] for p in result2["performers"]}
        assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def test_search_with_sort_desc(self, ipc_server, sample_performers):
        """Test sorting by ACI score descending."""
        handler = ipc_server.handlers.get("performers.search")

        result = await handler(sort_by="aci_score", sort_order="desc")

        performers = result["performers"]
        if len(performers) >= 2:
            for i in range(len(performers) - 1):
                assert performers[i]["aci_score"] >= performers[i + 1]["aci_score"]

    @pytest.mark.asyncio
    async def test_search_with_sort_asc(self, ipc_server, sample_performers):
        """Test sorting by ACI score ascending."""
        handler = ipc_server.handlers.get("performers.search")

        result = await handler(sort_by="aci_score", sort_order="asc")

        performers = result["performers"]
        if len(performers) >= 2:
            for i in range(len(performers) - 1):
                assert performers[i]["aci_score"] <= performers[i + 1]["aci_score"]


class TestPerformerFeaturedHandler:
    """Tests for performers.featured handler."""

    @pytest.mark.asyncio
    async def test_featured_returns_available_performers(self, ipc_server, sample_performers):
        """Test featured only returns available performers."""
        handler = ipc_server.handlers.get("performers.featured")
        assert handler is not None

        result = await handler(limit=10)

        assert isinstance(result, list)
        assert all(p["is_available"] is True for p in result)

    @pytest.mark.asyncio
    async def test_featured_sorted_by_aci(self, ipc_server, sample_performers):
        """Test featured performers are sorted by ACI score."""
        handler = ipc_server.handlers.get("performers.featured")

        result = await handler(limit=10)

        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i]["aci_score"] >= result[i + 1]["aci_score"]

    @pytest.mark.asyncio
    async def test_featured_respects_limit(self, ipc_server, sample_performers):
        """Test featured respects limit parameter."""
        handler = ipc_server.handlers.get("performers.featured")

        result = await handler(limit=2)

        assert len(result) <= 2


class TestPerformerLeaderboardHandler:
    """Tests for performers.leaderboard handler."""

    @pytest.mark.asyncio
    async def test_leaderboard_returns_top_performers(self, ipc_server, sample_performers):
        """Test leaderboard returns performers sorted by ACI."""
        handler = ipc_server.handlers.get("performers.leaderboard")
        assert handler is not None

        result = await handler(limit=10)

        assert isinstance(result, list)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i]["aci_score"] >= result[i + 1]["aci_score"]

    @pytest.mark.asyncio
    async def test_leaderboard_includes_required_fields(self, ipc_server, sample_performers):
        """Test leaderboard entries include required fields."""
        handler = ipc_server.handlers.get("performers.leaderboard")

        result = await handler(limit=10)

        for entry in result:
            assert "rank" in entry
            assert "performer_id" in entry
            assert "stage_name" in entry
            assert "aci_score" in entry
            assert "completed_bookings" in entry
            assert "average_rating" in entry


class TestPerformerGetHandler:
    """Tests for performers.get handler."""

    @pytest.mark.asyncio
    async def test_get_returns_performer(self, ipc_server, sample_performers):
        """Test getting a specific performer by ID."""
        handler = ipc_server.handlers.get("performers.get")
        assert handler is not None

        performer_id = str(sample_performers[0].id)
        result = await handler(id=performer_id)

        assert result["id"] == performer_id
        assert result["stage_name"] == sample_performers[0].stage_name

    @pytest.mark.asyncio
    async def test_get_not_found_raises_error(self, ipc_server, db_session):
        """Test getting non-existent performer raises error."""
        handler = ipc_server.handlers.get("performers.get")

        with pytest.raises(ValueError, match="not found"):
            await handler(id=str(uuid4()))

    @pytest.mark.asyncio
    async def test_get_includes_all_fields(self, ipc_server, sample_performers):
        """Test get returns all performer fields."""
        handler = ipc_server.handlers.get("performers.get")

        result = await handler(id=str(sample_performers[0].id))

        required_fields = [
            "id", "stage_name", "bio", "specialties", "aci_score",
            "performer_type", "is_verified", "is_available",
            "motion_capabilities", "total_bookings",
            "completed_bookings", "lifetime_earnings_usd", "average_rating",
            "pricing_blink_usd", "base_price_usd", "completion_rate",
        ]
        for field in required_fields:
            assert field in result


class TestPerformerACIHandler:
    """Tests for performers.getACI handler."""

    @pytest.mark.asyncio
    async def test_get_aci_breakdown(self, ipc_server, sample_performers):
        """Test getting ACI breakdown for a performer."""
        handler = ipc_server.handlers.get("performers.getACI")
        assert handler is not None

        performer_id = str(sample_performers[0].id)
        result = await handler(performerId=performer_id)

        assert "overall" in result
        assert "consistency" in result
        assert "versatility" in result
        assert "delivery_speed" in result
        assert "client_satisfaction" in result

    @pytest.mark.asyncio
    async def test_get_aci_not_found_raises_error(self, ipc_server, db_session):
        """Test getting ACI for non-existent performer raises error."""
        handler = ipc_server.handlers.get("performers.getACI")

        with pytest.raises(ValueError, match="not found"):
            await handler(performerId=str(uuid4()))


class TestPerformerSeedHandler:
    """Tests for performers.seed handler."""

    @pytest.mark.asyncio
    async def test_seed_creates_performers(self, ipc_server, db_session):
        """Test seeding creates performers."""
        handler = ipc_server.handlers.get("performers.seed")
        assert handler is not None

        result = await handler()

        assert result["success"] is True
        assert result["count"] == 50
        assert "Seeded 50 performers" in result["message"]

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, ipc_server, db_session):
        """Test seeding multiple times doesn't create duplicates."""
        handler = ipc_server.handlers.get("performers.seed")

        # Seed twice
        result1 = await handler()
        result2 = await handler()

        # First call creates 50, second call returns 0 (already exist)
        assert result1["count"] == 50
        assert result2["count"] == 0  # No new performers created


class TestPerformerHandlerRegistration:
    """Tests for handler registration."""

    def test_all_performer_handlers_registered(self, ipc_server):
        """Test all performer handlers are registered."""
        expected_handlers = [
            "performers.search",
            "performers.featured",
            "performers.leaderboard",
            "performers.get",
            "performers.getACI",
            "performers.seed",
        ]

        for handler_name in expected_handlers:
            assert handler_name in ipc_server.handlers, f"Handler {handler_name} not registered"
