"""Tests for booking IPC handlers."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer
from scenemachine.models import (
    Booking,
    BookingMode,
    BookingStatus,
    Performer,
    PerformerAvailability,
    PerformerType,
    PerformerVerification,
    Project,
)
from scenemachine.models.project import ProjectState


@pytest.fixture
def ipc_server():
    """Create IPC server with registered handlers."""
    server = IPCServer("/tmp/test_scenemachine.sock")
    register_handlers(server)
    return server


@pytest.fixture
async def sample_project(db_session):
    """Create a sample project for testing."""
    project = Project(
        id=uuid4(),
        name="Test Film Project",
        description="A test project for booking tests",
        state=ProjectState.SCENES_PLANNING,
        owner_id=uuid4(),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def sample_performer(db_session):
    """Create a sample performer for testing."""
    performer = Performer(
        id=uuid4(),
        stage_name="Test Performer",
        bio="A test performer for booking tests",
        specialties=["action", "drama"],
        aci_score=85.0,
        performer_type=PerformerType.HUMAN,
        availability_status=PerformerAvailability.AVAILABLE,
        verification_status=PerformerVerification.VERIFIED,
        pricing={"blink": 10.0, "deep": 50.0, "epic_per_minute": 20.0},
        total_bookings=100,
        completed_bookings=95,
        lifetime_earnings_usd=25000.0,
        joined_at=datetime.now(UTC),
    )
    db_session.add(performer)
    await db_session.commit()
    await db_session.refresh(performer)
    return performer


@pytest.fixture
async def sample_booking(db_session, sample_project, sample_performer):
    """Create a sample booking for testing."""
    booking = Booking(
        id=uuid4(),
        project_id=sample_project.id,
        performer_id=sample_performer.id,
        requester_user_id=uuid4(),
        booking_mode=BookingMode.DEEP,
        status=BookingStatus.MATCHED,
        duration_requested_seconds=120,
        price_usd=50.0,
        requested_at=datetime.now(UTC),
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)
    return booking


class TestBlinkBookingHandler:
    """Tests for bookings.blink handler."""

    @pytest.mark.asyncio
    async def test_blink_creates_booking_without_performer(
        self, ipc_server, sample_project
    ):
        """Test creating a Blink booking without specifying a performer."""
        handler = ipc_server.handlers.get("bookings.blink")
        assert handler is not None

        result = await handler(
            project_id=str(sample_project.id),
            duration_seconds=10,
        )

        assert result["booking_mode"] == "BLINK"
        assert result["status"] == "MATCHING"  # No performer, so matching
        assert result["project_id"] == str(sample_project.id)
        assert "id" in result

    @pytest.mark.asyncio
    async def test_blink_creates_booking_with_performer(
        self, ipc_server, sample_project, sample_performer
    ):
        """Test creating a Blink booking with a specific performer."""
        handler = ipc_server.handlers.get("bookings.blink")

        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            duration_seconds=10,
        )

        assert result["booking_mode"] == "BLINK"
        assert result["status"] == "MATCHED"  # Performer specified
        assert result["performer_id"] == str(sample_performer.id)
        assert result["price_usd"] == 10.0  # From performer pricing

    @pytest.mark.asyncio
    async def test_blink_with_special_instructions(
        self, ipc_server, sample_project, sample_performer
    ):
        """Test creating a Blink booking with special instructions."""
        handler = ipc_server.handlers.get("bookings.blink")

        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            special_instructions="Quick smile and nod",
        )

        assert result["requirements"]["special_instructions"] == "Quick smile and nod"


class TestDeepBookingHandler:
    """Tests for bookings.deep handler."""

    @pytest.mark.asyncio
    async def test_deep_creates_booking(self, ipc_server, sample_project, sample_performer):
        """Test creating a Deep booking."""
        handler = ipc_server.handlers.get("bookings.deep")
        assert handler is not None

        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            duration_seconds=120,
        )

        assert result["booking_mode"] == "DEEP"
        assert result["status"] == "MATCHED"
        assert result["performer_id"] == str(sample_performer.id)
        assert result["requirements"]["duration_seconds"] == 120

    @pytest.mark.asyncio
    async def test_deep_with_emotion_markers(
        self, ipc_server, sample_project, sample_performer
    ):
        """Test creating a Deep booking with emotion markers."""
        handler = ipc_server.handlers.get("bookings.deep")

        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            duration_seconds=180,
            emotion_markers=["sad", "angry", "hopeful"],
        )

        assert result["requirements"]["emotion_markers"] == ["sad", "angry", "hopeful"]

    @pytest.mark.asyncio
    async def test_deep_calculates_price_by_duration(
        self, ipc_server, sample_project, sample_performer
    ):
        """Test Deep booking price scales with duration."""
        handler = ipc_server.handlers.get("bookings.deep")

        # 120 seconds = 12 * 10s units, base price $50
        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            duration_seconds=120,
        )

        # Price should be 50 * (120/10) = $600
        assert result["price_usd"] == 600.0


class TestEpicBookingHandler:
    """Tests for bookings.epic handler."""

    @pytest.mark.asyncio
    async def test_epic_creates_booking(self, ipc_server, sample_project, sample_performer):
        """Test creating an Epic booking."""
        handler = ipc_server.handlers.get("bookings.epic")
        assert handler is not None

        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            duration_seconds=300,
        )

        assert result["booking_mode"] == "EPIC"
        assert result["status"] == "MATCHED"
        assert result["requirements"]["duration_seconds"] == 300

    @pytest.mark.asyncio
    async def test_epic_price_by_minute(
        self, ipc_server, sample_project, sample_performer
    ):
        """Test Epic booking price uses per-minute rate."""
        handler = ipc_server.handlers.get("bookings.epic")

        # 300 seconds = 5 minutes, rate $20/min
        result = await handler(
            project_id=str(sample_project.id),
            performer_id=str(sample_performer.id),
            duration_seconds=300,
        )

        # Epic base price = 20 * (300/60) = $100, then scaled by duration
        # Actually: price_usd = (epic_per_minute * duration/60) * (duration/10)
        # = (20 * 5) * 30 = $3000
        expected_price = (20.0 * (300 / 60)) * (300 / 10)
        assert result["price_usd"] == expected_price


class TestGetBookingHandler:
    """Tests for bookings.get handler."""

    @pytest.mark.asyncio
    async def test_get_returns_booking(self, ipc_server, sample_booking):
        """Test getting a booking by ID."""
        handler = ipc_server.handlers.get("bookings.get")
        assert handler is not None

        result = await handler(id=str(sample_booking.id))

        assert result["id"] == str(sample_booking.id)
        assert result["booking_mode"] == "DEEP"
        assert result["status"] == "MATCHED"

    @pytest.mark.asyncio
    async def test_get_not_found_raises_error(self, ipc_server, db_session):
        """Test getting non-existent booking raises error."""
        handler = ipc_server.handlers.get("bookings.get")

        with pytest.raises(ValueError, match="not found"):
            await handler(id=str(uuid4()))

    @pytest.mark.asyncio
    async def test_get_includes_performer_info(self, ipc_server, sample_booking):
        """Test get includes performer stage name."""
        handler = ipc_server.handlers.get("bookings.get")

        result = await handler(id=str(sample_booking.id))

        assert result["performer_stage_name"] == "Test Performer"


class TestListProjectBookingsHandler:
    """Tests for bookings.listByProject handler."""

    @pytest.mark.asyncio
    async def test_list_returns_project_bookings(
        self, ipc_server, sample_project, sample_booking
    ):
        """Test listing bookings for a project."""
        handler = ipc_server.handlers.get("bookings.listByProject")
        assert handler is not None

        result = await handler(projectId=str(sample_project.id))

        assert isinstance(result, list)
        assert len(result) >= 1
        assert any(b["id"] == str(sample_booking.id) for b in result)

    @pytest.mark.asyncio
    async def test_list_empty_for_new_project(self, ipc_server, db_session):
        """Test listing bookings for project with no bookings."""
        # Create a new project with no bookings
        project = Project(
            id=uuid4(),
            name="Empty Project",
            description="No bookings",
            state=ProjectState.EMPTY,
            owner_id=uuid4(),
        )
        db_session.add(project)
        await db_session.commit()

        handler = ipc_server.handlers.get("bookings.listByProject")
        result = await handler(projectId=str(project.id))

        assert result == []

    @pytest.mark.asyncio
    async def test_list_filters_by_status(
        self, ipc_server, sample_project, sample_booking, db_session
    ):
        """Test filtering bookings by status."""
        # Create another booking with different status
        accepted_booking = Booking(
            id=uuid4(),
            project_id=sample_project.id,
            performer_id=sample_booking.performer_id,
            requester_user_id=uuid4(),
            booking_mode=BookingMode.BLINK,
            status=BookingStatus.ACCEPTED,
            duration_requested_seconds=10,
            price_usd=10.0,
            requested_at=datetime.now(UTC),
            accepted_at=datetime.now(UTC),
        )
        db_session.add(accepted_booking)
        await db_session.commit()

        handler = ipc_server.handlers.get("bookings.listByProject")
        result = await handler(projectId=str(sample_project.id), status="accepted")

        assert len(result) == 1
        assert result[0]["status"] == "ACCEPTED"


class TestAcceptBookingHandler:
    """Tests for bookings.accept handler."""

    @pytest.mark.asyncio
    async def test_accept_booking(self, ipc_server, sample_booking):
        """Test accepting a matched booking."""
        handler = ipc_server.handlers.get("bookings.accept")
        assert handler is not None

        result = await handler(bookingId=str(sample_booking.id))

        assert result["status"] == "ACCEPTED"
        assert result["accepted_at"] is not None

    @pytest.mark.asyncio
    async def test_accept_not_found_raises_error(self, ipc_server, db_session):
        """Test accepting non-existent booking raises error."""
        handler = ipc_server.handlers.get("bookings.accept")

        with pytest.raises(ValueError, match="not found"):
            await handler(bookingId=str(uuid4()))

    @pytest.mark.asyncio
    async def test_accept_invalid_status_raises_error(
        self, ipc_server, db_session, sample_project, sample_performer
    ):
        """Test accepting booking in wrong status raises error."""
        # Create a completed booking
        completed_booking = Booking(
            id=uuid4(),
            project_id=sample_project.id,
            performer_id=sample_performer.id,
            requester_user_id=uuid4(),
            booking_mode=BookingMode.BLINK,
            status=BookingStatus.COMPLETED,
            duration_requested_seconds=10,
            price_usd=10.0,
            requested_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db_session.add(completed_booking)
        await db_session.commit()

        handler = ipc_server.handlers.get("bookings.accept")

        with pytest.raises(ValueError, match="Cannot accept"):
            await handler(bookingId=str(completed_booking.id))


class TestDeliverBookingHandler:
    """Tests for bookings.deliver handler."""

    @pytest.mark.asyncio
    async def test_deliver_booking(self, ipc_server, db_session, sample_booking):
        """Test delivering a booking."""
        # First accept the booking
        sample_booking.status = BookingStatus.IN_PROGRESS
        await db_session.commit()
        await db_session.refresh(sample_booking)

        handler = ipc_server.handlers.get("bookings.deliver")
        assert handler is not None

        result = await handler(
            bookingId=str(sample_booking.id),
            deliveryUrl="https://storage.example.com/video.mp4",
            notes="Completed with 3 takes",
        )

        assert result["status"] == "DELIVERED"
        assert result["delivered_at"] is not None
        assert result["delivery_notes"] == "Completed with 3 takes"

    @pytest.mark.asyncio
    async def test_deliver_invalid_status_raises_error(self, ipc_server, sample_booking):
        """Test delivering booking in wrong status raises error."""
        handler = ipc_server.handlers.get("bookings.deliver")

        with pytest.raises(ValueError, match="Cannot deliver"):
            await handler(
                bookingId=str(sample_booking.id),
                deliveryUrl="https://storage.example.com/video.mp4",
            )


class TestApproveBookingHandler:
    """Tests for bookings.approve handler."""

    @pytest.mark.asyncio
    async def test_approve_booking(self, ipc_server, db_session, sample_booking):
        """Test approving a delivered booking."""
        # Set booking to delivered status
        sample_booking.status = BookingStatus.DELIVERED
        sample_booking.delivered_at = datetime.now(UTC)
        await db_session.commit()
        await db_session.refresh(sample_booking)

        handler = ipc_server.handlers.get("bookings.approve")
        assert handler is not None

        result = await handler(bookingId=str(sample_booking.id))

        # Should transition to COMPLETED (auto-completes after approval)
        assert result["status"] == "COMPLETED"
        assert result["payment_status"] == "RELEASED"

    @pytest.mark.asyncio
    async def test_approve_invalid_status_raises_error(self, ipc_server, sample_booking):
        """Test approving booking in wrong status raises error."""
        handler = ipc_server.handlers.get("bookings.approve")

        with pytest.raises(ValueError, match="Cannot approve"):
            await handler(bookingId=str(sample_booking.id))


class TestDisputeBookingHandler:
    """Tests for bookings.dispute handler."""

    @pytest.mark.asyncio
    async def test_dispute_booking(self, ipc_server, db_session, sample_booking):
        """Test disputing a delivered booking."""
        # Set booking to delivered status
        sample_booking.status = BookingStatus.DELIVERED
        sample_booking.delivered_at = datetime.now(UTC)
        await db_session.commit()
        await db_session.refresh(sample_booking)

        handler = ipc_server.handlers.get("bookings.dispute")
        assert handler is not None

        result = await handler(
            bookingId=str(sample_booking.id),
            reason="Video quality does not match requirements",
        )

        assert result["status"] == "DISPUTED"

    @pytest.mark.asyncio
    async def test_dispute_invalid_status_raises_error(self, ipc_server, sample_booking):
        """Test disputing booking in wrong status raises error."""
        handler = ipc_server.handlers.get("bookings.dispute")

        with pytest.raises(ValueError, match="Cannot dispute"):
            await handler(
                bookingId=str(sample_booking.id),
                reason="Some reason",
            )


class TestRateBookingHandler:
    """Tests for bookings.rate handler."""

    @pytest.mark.asyncio
    async def test_rate_booking(self, ipc_server, db_session, sample_booking):
        """Test rating a completed booking."""
        # Set booking to completed status
        sample_booking.status = BookingStatus.COMPLETED
        sample_booking.completed_at = datetime.now(UTC)
        await db_session.commit()
        await db_session.refresh(sample_booking)

        handler = ipc_server.handlers.get("bookings.rate")
        assert handler is not None

        result = await handler(
            bookingId=str(sample_booking.id),
            rating=5,
            review="Excellent performance!",
            wouldRehire=True,
        )

        assert result["rating"] == 5
        assert result["review"] == "Excellent performance!"

    @pytest.mark.asyncio
    async def test_rate_updates_existing_rating(
        self, ipc_server, db_session, sample_booking
    ):
        """Test rating can be updated."""
        from scenemachine.models import PerformerRating

        # Set booking to completed and add initial rating
        sample_booking.status = BookingStatus.COMPLETED
        sample_booking.completed_at = datetime.now(UTC)

        rating = PerformerRating(
            id=uuid4(),
            performer_id=sample_booking.performer_id,
            booking_id=sample_booking.id,
            rater_user_id=sample_booking.requester_user_id,
            overall_score=3,
            review_text="Initial review",
            would_rehire=False,
            rated_at=datetime.now(UTC),
        )
        db_session.add(rating)
        await db_session.commit()
        await db_session.refresh(sample_booking)

        handler = ipc_server.handlers.get("bookings.rate")

        result = await handler(
            bookingId=str(sample_booking.id),
            rating=5,
            review="Updated: Actually excellent!",
            wouldRehire=True,
        )

        assert result["rating"] == 5
        assert result["review"] == "Updated: Actually excellent!"


class TestBookingHandlerRegistration:
    """Tests for handler registration."""

    def test_all_booking_handlers_registered(self, ipc_server):
        """Test all booking handlers are registered."""
        expected_handlers = [
            "bookings.blink",
            "bookings.deep",
            "bookings.epic",
            "bookings.get",
            "bookings.listByProject",
            "bookings.accept",
            "bookings.deliver",
            "bookings.approve",
            "bookings.dispute",
            "bookings.rate",
        ]

        for handler_name in expected_handlers:
            assert handler_name in ipc_server.handlers, f"Handler {handler_name} not registered"


class TestBookingResponseFields:
    """Tests for booking response field completeness."""

    @pytest.mark.asyncio
    async def test_booking_response_includes_all_fields(self, ipc_server, sample_booking):
        """Test booking response includes all required fields."""
        handler = ipc_server.handlers.get("bookings.get")

        result = await handler(id=str(sample_booking.id))

        required_fields = [
            "id",
            "project_id",
            "performer_id",
            "performer_stage_name",
            "booking_mode",
            "status",
            "price_usd",
            "platform_fee_usd",
            "performer_payout_usd",
            "payment_status",
            "requirements",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in result, f"Field {field} missing from booking response"

    @pytest.mark.asyncio
    async def test_booking_requirements_structure(self, ipc_server, sample_booking):
        """Test booking requirements has expected structure."""
        handler = ipc_server.handlers.get("bookings.get")

        result = await handler(id=str(sample_booking.id))

        requirements = result["requirements"]
        assert "duration_seconds" in requirements
        assert "emotion_markers" in requirements
        assert "special_instructions" in requirements
        assert "reference_images" in requirements
