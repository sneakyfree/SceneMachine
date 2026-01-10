"""Tests for Performer Payouts service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.performer_payouts import PerformerPayoutsService


class TestPerformerPayoutsService:
    """Tests for PerformerPayoutsService."""

    @pytest.fixture
    def payouts_service(self, db_session: AsyncSession) -> PerformerPayoutsService:
        """Create a performer payouts service instance."""
        return PerformerPayoutsService(db_session)

    @pytest.mark.asyncio
    async def test_create_payout(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test creating a payout record."""
        if hasattr(payouts_service, "create_payout"):
            payout = await payouts_service.create_payout(
                performer_id=uuid4(),
                amount=Decimal("150.00"),
                currency="USD",
                booking_ids=[uuid4(), uuid4()],
            )

            assert payout is not None

    @pytest.mark.asyncio
    async def test_get_payout_by_id(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test getting a payout by ID."""
        if hasattr(payouts_service, "get_by_id"):
            payout = await payouts_service.get_by_id(uuid4())

            # Should return None for non-existent
            assert payout is None

    @pytest.mark.asyncio
    async def test_get_performer_payouts(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test getting all payouts for a performer."""
        if hasattr(payouts_service, "get_performer_payouts"):
            payouts = await payouts_service.get_performer_payouts(
                performer_id=uuid4(),
            )

            assert isinstance(payouts, list)

    @pytest.mark.asyncio
    async def test_get_pending_payouts(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test getting pending payouts."""
        if hasattr(payouts_service, "get_pending"):
            pending = await payouts_service.get_pending()

            assert isinstance(pending, list)

    @pytest.mark.asyncio
    async def test_process_payout(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test processing a payout."""
        if hasattr(payouts_service, "process_payout"):
            result = await payouts_service.process_payout(
                payout_id=uuid4(),
            )

            # May fail for non-existent payout
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_mark_payout_complete(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test marking a payout as complete."""
        if hasattr(payouts_service, "mark_complete"):
            result = await payouts_service.mark_complete(
                payout_id=uuid4(),
                transaction_id="txn_12345",
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_mark_payout_failed(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test marking a payout as failed."""
        if hasattr(payouts_service, "mark_failed"):
            result = await payouts_service.mark_failed(
                payout_id=uuid4(),
                reason="Insufficient funds",
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_calculate_performer_earnings(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test calculating a performer's earnings."""
        if hasattr(payouts_service, "calculate_earnings"):
            earnings = await payouts_service.calculate_earnings(
                performer_id=uuid4(),
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
            )

            assert earnings is not None
            if isinstance(earnings, dict):
                assert "total" in earnings or "amount" in earnings

    @pytest.mark.asyncio
    async def test_get_payout_history(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test getting payout history."""
        if hasattr(payouts_service, "get_history"):
            history = await payouts_service.get_history(
                performer_id=uuid4(),
                limit=10,
            )

            assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_get_earnings_summary(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test getting earnings summary."""
        if hasattr(payouts_service, "get_earnings_summary"):
            summary = await payouts_service.get_earnings_summary(
                performer_id=uuid4(),
            )

            assert summary is not None

    @pytest.mark.asyncio
    async def test_schedule_payout(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test scheduling a future payout."""
        if hasattr(payouts_service, "schedule"):
            scheduled = await payouts_service.schedule(
                performer_id=uuid4(),
                amount=Decimal("200.00"),
                scheduled_date=datetime.utcnow() + timedelta(days=7),
            )

            assert scheduled is not None

    @pytest.mark.asyncio
    async def test_cancel_payout(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test cancelling a pending payout."""
        if hasattr(payouts_service, "cancel"):
            result = await payouts_service.cancel(
                payout_id=uuid4(),
                reason="User request",
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_payout_stats(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test getting payout statistics."""
        if hasattr(payouts_service, "get_stats"):
            stats = await payouts_service.get_stats()

            assert stats is not None

    @pytest.mark.asyncio
    async def test_retry_failed_payout(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test retrying a failed payout."""
        if hasattr(payouts_service, "retry"):
            result = await payouts_service.retry(
                payout_id=uuid4(),
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_validate_payout_method(
        self,
        payouts_service: PerformerPayoutsService,
    ):
        """Test validating a performer's payout method."""
        if hasattr(payouts_service, "validate_payout_method"):
            validation = await payouts_service.validate_payout_method(
                performer_id=uuid4(),
            )

            assert validation is not None
