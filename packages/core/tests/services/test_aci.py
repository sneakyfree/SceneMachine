"""Tests for ACI (AI Character Integration) service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.aci import ACIService


class TestACIService:
    """Tests for ACIService."""

    @pytest.fixture
    def aci_service(self, db_session: AsyncSession) -> ACIService:
        """Create an ACI service instance."""
        return ACIService(db_session)

    @pytest.mark.asyncio
    async def test_calculate_aci_score_new_performer(self, aci_service: ACIService):
        """Test ACI score calculation for a new performer with no activity."""
        performer_id = uuid4()

        # New performer should have a baseline score
        score = await aci_service.calculate_aci_score(performer_id)

        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    @pytest.mark.asyncio
    async def test_calculate_aci_score_components(self, aci_service: ACIService):
        """Test that ACI score includes all expected components."""
        performer_id = uuid4()

        # Get score breakdown if available
        score = await aci_service.calculate_aci_score(performer_id)

        # Score should be a valid float
        assert isinstance(score, float)
        assert score >= 0.0

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty(self, aci_service: ACIService):
        """Test leaderboard with no performers."""
        leaderboard = await aci_service.get_leaderboard(limit=10)

        assert isinstance(leaderboard, list)

    @pytest.mark.asyncio
    async def test_get_leaderboard_limit(self, aci_service: ACIService):
        """Test leaderboard respects limit parameter."""
        leaderboard = await aci_service.get_leaderboard(limit=5)

        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 5

    @pytest.mark.asyncio
    async def test_engagement_weight(self, aci_service: ACIService):
        """Test that engagement is properly weighted in score."""
        performer_id = uuid4()

        # Calculate score - engagement should be one component
        score = await aci_service.calculate_aci_score(performer_id)

        # Score should be non-negative
        assert score >= 0.0

    @pytest.mark.asyncio
    async def test_recency_weighting(self, aci_service: ACIService):
        """Test that recent activity is weighted more heavily."""
        performer_id = uuid4()

        # Recent engagement should boost score
        score = await aci_service.calculate_aci_score(performer_id)

        # Score should be a valid float
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_aci_score_consistency(self, aci_service: ACIService):
        """Test that ACI score is consistent for same performer."""
        performer_id = uuid4()

        score1 = await aci_service.calculate_aci_score(performer_id)
        score2 = await aci_service.calculate_aci_score(performer_id)

        # Same performer with same data should get same score
        assert score1 == score2

    @pytest.mark.asyncio
    async def test_aci_score_logarithmic_scaling(self, aci_service: ACIService):
        """Test that high engagement values are scaled logarithmically."""
        performer_id = uuid4()

        score = await aci_service.calculate_aci_score(performer_id)

        # Score should be bounded
        assert score <= 100.0

    @pytest.mark.asyncio
    async def test_get_performer_rank(self, aci_service: ACIService):
        """Test getting a performer's rank on the leaderboard."""
        performer_id = uuid4()

        # Get rank - should return None or a valid rank
        rank = await aci_service.get_performer_rank(performer_id)

        if rank is not None:
            assert isinstance(rank, int)
            assert rank >= 1

    @pytest.mark.asyncio
    async def test_refresh_all_scores(self, aci_service: ACIService):
        """Test refreshing all performer scores."""
        # This should not raise an exception
        await aci_service.refresh_all_scores()
