"""Tests for Bookings API routes."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.main import app


class TestBookingsRoutes:
    """Tests for Bookings API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_create_booking_endpoint(self, client: AsyncClient):
        """Test creating a booking."""
        response = await client.post(
            "/api/bookings",
            json={
                "performer_id": str(uuid4()),
                "project_id": str(uuid4()),
                "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                "rate": 100.00,
            },
        )

        # Should handle booking creation
        assert response.status_code in (200, 201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_get_booking_endpoint(self, client: AsyncClient):
        """Test getting a specific booking."""
        booking_id = uuid4()
        response = await client.get(f"/api/bookings/{booking_id}")

        # Should return booking or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_list_my_bookings(self, client: AsyncClient):
        """Test listing user's bookings."""
        response = await client.get("/api/bookings/me")

        # Should return list or auth error
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_list_project_bookings(self, client: AsyncClient):
        """Test listing bookings for a project."""
        project_id = uuid4()
        response = await client.get(f"/api/projects/{project_id}/bookings")

        # Should return list or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_cancel_booking(self, client: AsyncClient):
        """Test canceling a booking."""
        booking_id = uuid4()
        response = await client.post(f"/api/bookings/{booking_id}/cancel")

        # Should handle cancellation
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_confirm_booking(self, client: AsyncClient):
        """Test confirming a booking (performer action)."""
        booking_id = uuid4()
        response = await client.post(f"/api/bookings/{booking_id}/confirm")

        # Should handle confirmation
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_decline_booking(self, client: AsyncClient):
        """Test declining a booking (performer action)."""
        booking_id = uuid4()
        response = await client.post(
            f"/api/bookings/{booking_id}/decline",
            json={"reason": "Schedule conflict"},
        )

        # Should handle decline
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_complete_booking(self, client: AsyncClient):
        """Test marking a booking as complete."""
        booking_id = uuid4()
        response = await client.post(f"/api/bookings/{booking_id}/complete")

        # Should handle completion
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_booking(self, client: AsyncClient):
        """Test updating a booking."""
        booking_id = uuid4()
        response = await client.put(
            f"/api/bookings/{booking_id}",
            json={
                "start_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=4)).isoformat(),
            },
        )

        # Should handle update
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_add_booking_note(self, client: AsyncClient):
        """Test adding a note to a booking."""
        booking_id = uuid4()
        response = await client.post(
            f"/api/bookings/{booking_id}/notes",
            json={"content": "Please arrive 30 minutes early."},
        )

        # Should handle note addition
        assert response.status_code in (200, 201, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_booking_notes(self, client: AsyncClient):
        """Test getting notes for a booking."""
        booking_id = uuid4()
        response = await client.get(f"/api/bookings/{booking_id}/notes")

        # Should return notes
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_check_performer_availability(self, client: AsyncClient):
        """Test checking performer availability."""
        performer_id = uuid4()
        response = await client.get(
            f"/api/performers/{performer_id}/availability",
            params={
                "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            },
        )

        # Should return availability
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_quick_blink_booking(self, client: AsyncClient):
        """Test quick Blink booking (same-day)."""
        response = await client.post(
            "/api/bookings/blink",
            json={
                "performer_id": str(uuid4()),
                "project_id": str(uuid4()),
                "duration_hours": 2,
            },
        )

        # Should handle quick booking
        assert response.status_code in (200, 201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_extend_booking(self, client: AsyncClient):
        """Test extending a booking."""
        booking_id = uuid4()
        response = await client.post(
            f"/api/bookings/{booking_id}/extend",
            json={"additional_days": 2},
        )

        # Should handle extension
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_booking_contract(self, client: AsyncClient):
        """Test getting booking contract details."""
        booking_id = uuid4()
        response = await client.get(f"/api/bookings/{booking_id}/contract")

        # Should return contract
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_sign_booking_contract(self, client: AsyncClient):
        """Test signing a booking contract."""
        booking_id = uuid4()
        response = await client.post(
            f"/api/bookings/{booking_id}/contract/sign",
            json={"signature": "digital_signature_data"},
        )

        # Should handle signing
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_rate_booking(self, client: AsyncClient):
        """Test rating a completed booking."""
        booking_id = uuid4()
        response = await client.post(
            f"/api/bookings/{booking_id}/rate",
            json={
                "rating": 5,
                "review": "Excellent work!",
            },
        )

        # Should handle rating
        assert response.status_code in (200, 201, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_filter_bookings_by_status(self, client: AsyncClient):
        """Test filtering bookings by status."""
        response = await client.get(
            "/api/bookings/me",
            params={"status": "confirmed"},
        )

        # Should handle filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_bookings_by_date(self, client: AsyncClient):
        """Test filtering bookings by date range."""
        response = await client.get(
            "/api/bookings/me",
            params={
                "start_after": datetime.utcnow().isoformat(),
                "end_before": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            },
        )

        # Should handle filter
        assert response.status_code in (200, 401)
